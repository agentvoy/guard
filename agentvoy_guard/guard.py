"""
Guard — the main runtime enforcement class.

Usage:
    from agentvoy_guard import Guard

    guard = Guard.from_config()          # loads agent.guard.yml automatically
    guard = Guard.from_config("path/to/agent.guard.yml")

    # As a context manager (recommended):
    with guard.session() as session:
        session.check_input(user_prompt)

        for i in range(100):
            session.tick()                        # enforces max_iterations + timeout
            response = client.messages.create(...)
            session.track_usage(response.usage)   # enforces cost_limit
            session.tick_tool()                   # enforces max_tool_calls

        session.check_output(final_text)

    print(guard.last_summary)

    # As a decorator:
    @guard.protect
    def run_agent(prompt: str) -> str:
        ...
"""

from __future__ import annotations

import functools
import time
from contextlib import contextmanager
from typing import Any, Callable, Generator, Optional

from .config import AgentGuardConfig, load_config, parse_timeout, parse_cost_limit
from .exceptions import GuardError
from .enforcers import (
    IterationEnforcer,
    CostEnforcer,
    TimeoutEnforcer,
    enforce_no_injection,
    enforce_pii,
    NetworkEnforcer,
    ShellEnforcer,
)


class GuardSession:
    """
    A single agent execution session with all enforcers active.
    Use as a context manager via guard.session().
    """

    def __init__(self, config: AgentGuardConfig):
        self._config = config
        beh = config.guardrails.behavior

        # Enforcers
        self._iterations = IterationEnforcer(
            max_iterations=beh.max_iterations,
            max_tool_calls=beh.max_tool_calls,
        )
        self._cost = CostEnforcer(
            model=config.model.model,
            cost_limit=parse_cost_limit(beh.cost_limit) if beh.cost_limit else None,
        )
        timeout_secs = parse_timeout(beh.timeout)
        self._timeout = TimeoutEnforcer(timeout_seconds=timeout_secs)
        self._network = NetworkEnforcer(
            mode=config.permissions.network.mode,
            allow=config.permissions.network.allow,
            deny=config.permissions.network.deny,
        )
        self._shell = ShellEnforcer(
            allow_shell=config.permissions.execution.allow_shell,
            allow_subprocess=config.permissions.execution.allow_subprocess,
        )
        self._start_wall: float = 0.0

    def start(self):
        """Activate all enforcers."""
        self._start_wall = time.monotonic()
        self._timeout.start()
        self._network.install()
        self._shell.install()

    def stop(self):
        """Deactivate all enforcers."""
        self._timeout.stop()
        self._network.uninstall()
        self._shell.uninstall()

    # ── Input / output checks ─────────────────────────────────────────────

    def check_input(self, text: str):
        """
        Run all input guardrails on user-provided text.
        Call this before passing text to the agent.
        """
        inp = self._config.guardrails.input

        if inp.block_prompt_injection:
            enforce_no_injection(text)

        if inp.pii_detection != "off":
            enforce_pii(text, mode=inp.pii_detection)

        if len(text.split()) * 1.3 > inp.max_tokens:  # rough token estimate
            import warnings
            warnings.warn(
                f"[agentvoy-guard] Input may exceed max_tokens ({inp.max_tokens})",
                stacklevel=2,
            )

    def check_output(self, text: str):
        """Run output guardrails. Call this on the agent's final response."""
        out = self._config.guardrails.output
        if out.pii_redaction:
            from .enforcers.pii import detect_pii
            pii = detect_pii(text)
            if pii:
                import warnings
                warnings.warn(
                    f"[agentvoy-guard] PII detected in output: {', '.join(pii)}",
                    stacklevel=2,
                )

    # ── Per-iteration hooks ───────────────────────────────────────────────

    def tick(self):
        """Call once per agent loop iteration. Enforces max_iterations + timeout."""
        self._timeout.check()
        self._iterations.tick()

    def tick_tool(self):
        """Call once per tool invocation. Enforces max_tool_calls."""
        self._iterations.tick_tool()

    def track_usage(self, usage: Any):
        """
        Track token usage from any SDK response.
        Accepts usage objects from Anthropic, OpenAI, Google, etc.
        """
        self._cost.track_usage_object(usage)

    def track_tokens(self, input_tokens: int = 0, output_tokens: int = 0):
        """Manually track token counts."""
        self._cost.track(input_tokens=input_tokens, output_tokens=output_tokens)

    # ── Summary ───────────────────────────────────────────────────────────

    @property
    def summary(self) -> dict:
        elapsed = time.monotonic() - self._start_wall
        return {
            "iterations": self._iterations.iterations,
            "tool_calls": self._iterations.tool_calls,
            "elapsed_seconds": round(elapsed, 2),
            **self._cost.summary,
        }


class Guard:
    """
    Main entry point for agentvoy-guard.

    Guard loads agent.guard.yml and provides:
    - guard.session() context manager for wrapping agent execution
    - guard.protect decorator for simple agent functions
    """

    def __init__(self, config: AgentGuardConfig):
        self._config = config
        self._last_summary: Optional[dict] = None

    @classmethod
    def from_config(cls, path: Optional[str] = None) -> "Guard":
        """Load config from agent.guard.yml (auto-discovered or explicit path)."""
        config = load_config(path)
        return cls(config)

    @classmethod
    def from_defaults(cls) -> "Guard":
        """Create a Guard with safe default settings (no config file needed)."""
        return cls(AgentGuardConfig())

    @property
    def config(self) -> AgentGuardConfig:
        return self._config

    @property
    def last_summary(self) -> Optional[dict]:
        return self._last_summary

    @contextmanager
    def session(self) -> Generator[GuardSession, None, None]:
        """
        Context manager that activates all guardrails for one agent run.

        with guard.session() as session:
            session.check_input(prompt)
            for i in range(100):
                session.tick()
                response = llm.call(...)
                session.track_usage(response.usage)
                session.tick_tool()
            session.check_output(result)
        """
        s = GuardSession(self._config)
        s.start()
        try:
            yield s
        finally:
            s.stop()
            self._last_summary = s.summary

    def protect(self, fn: Callable) -> Callable:
        """
        Decorator for simple agent functions.
        Automatically starts a session and runs input/output checks.

        @guard.protect
        def run_agent(prompt: str) -> str:
            ...
        """
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            # Extract first string arg as prompt for input check
            prompt = next(
                (a for a in args if isinstance(a, str)),
                kwargs.get("prompt", ""),
            )
            with self.session() as session:
                if prompt:
                    session.check_input(prompt)
                result = fn(*args, **kwargs)
                if isinstance(result, str):
                    session.check_output(result)
                return result
        return wrapper

    def __repr__(self) -> str:
        return (
            f"Guard(model={self._config.model.model!r}, "
            f"max_iterations={self._config.guardrails.behavior.max_iterations}, "
            f"cost_limit={self._config.guardrails.behavior.cost_limit})"
        )
