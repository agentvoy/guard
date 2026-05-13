"""
agentvoy-guard — Runtime guardrails enforcement for AI agents.

Reads agent.guard.yml and enforces:
- Iteration limits
- Cost limits (with token tracking)
- Timeouts
- Prompt injection detection
- PII detection and blocking
- Network access restrictions
- Shell execution blocking

Quick start:
    from agentvoy_guard import Guard

    guard = Guard.from_config()   # loads agent.guard.yml automatically

    with guard.session() as session:
        session.check_input(user_prompt)
        for i in range(100):
            session.tick()
            response = llm_call(...)
            session.track_usage(response.usage)
        session.check_output(result)

    print(guard.last_summary)
"""

from .guard import Guard, GuardSession
from .config import load_config, AgentGuardConfig
from .exceptions import (
    GuardError,
    IterationLimitError,
    ToolCallLimitError,
    CostLimitError,
    TimeoutError,
    PromptInjectionError,
    PIIDetectedError,
    NetworkBlockedError,
    ShellBlockedError,
)

__version__ = "0.1.0"

__all__ = [
    "Guard",
    "GuardSession",
    "load_config",
    "AgentGuardConfig",
    "GuardError",
    "IterationLimitError",
    "ToolCallLimitError",
    "CostLimitError",
    "TimeoutError",
    "PromptInjectionError",
    "PIIDetectedError",
    "NetworkBlockedError",
    "ShellBlockedError",
]
