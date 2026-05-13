"""
Config loader for agent.guard.yml
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    raise ImportError("PyYAML is required: pip install pyyaml")


@dataclass
class NetworkConfig:
    mode: str = "open"           # open | restricted | disabled
    allow: list[str] = field(default_factory=list)
    deny: list[str] = field(default_factory=list)


@dataclass
class FilesystemConfig:
    read: list[str] = field(default_factory=lambda: ["./**"])
    write: list[str] = field(default_factory=list)


@dataclass
class ExecutionConfig:
    allow_shell: bool = False
    allow_subprocess: bool = False


@dataclass
class PermissionsConfig:
    network: NetworkConfig = field(default_factory=NetworkConfig)
    filesystem: FilesystemConfig = field(default_factory=FilesystemConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)


@dataclass
class InputGuardrails:
    block_prompt_injection: bool = True
    max_tokens: int = 4096
    pii_detection: str = "off"      # off | warn | block
    content_filter: str = "off"     # off | moderate | strict


@dataclass
class OutputGuardrails:
    block_harmful_content: bool = False
    max_output_tokens: int = 8192
    pii_redaction: bool = False


@dataclass
class BehaviorGuardrails:
    max_iterations: int = 20
    timeout: str = "5m"
    max_tool_calls: int = 50
    retry_limit: int = 3
    cost_limit: Optional[str] = None     # e.g. "$1.00"
    human_approval_after: Optional[int] = None


@dataclass
class GuardrailsConfig:
    input: InputGuardrails = field(default_factory=InputGuardrails)
    output: OutputGuardrails = field(default_factory=OutputGuardrails)
    behavior: BehaviorGuardrails = field(default_factory=BehaviorGuardrails)


@dataclass
class ModelConfig:
    provider: str = "openai"
    model: str = "gpt-4o"
    api_key_env: str = "OPENAI_API_KEY"


@dataclass
class AgentGuardConfig:
    model: ModelConfig = field(default_factory=ModelConfig)
    permissions: PermissionsConfig = field(default_factory=PermissionsConfig)
    guardrails: GuardrailsConfig = field(default_factory=GuardrailsConfig)
    identity_name: str = "agent"
    version: str = "1.0"


def parse_timeout(timeout_str: str) -> float:
    """Parse timeout string like '5m', '30s', '1h' into seconds."""
    timeout_str = timeout_str.strip()
    match = re.match(r"^(\d+(?:\.\d+)?)(s|m|h)$", timeout_str)
    if not match:
        raise ValueError(f"Invalid timeout format: {timeout_str!r}. Use e.g. '30s', '5m', '1h'")
    value, unit = float(match.group(1)), match.group(2)
    return value * {"s": 1, "m": 60, "h": 3600}[unit]


def parse_cost_limit(cost_str: str) -> float:
    """Parse cost limit string like '$1.00' into float dollars."""
    return float(cost_str.strip().lstrip("$"))


def load_config(path: Optional[str] = None) -> AgentGuardConfig:
    """Load agent.guard.yml from path or search up from cwd."""
    if path:
        config_path = Path(path)
    else:
        config_path = _find_config()

    if not config_path or not config_path.exists():
        return AgentGuardConfig()

    with open(config_path) as f:
        data = yaml.safe_load(f) or {}

    return _parse(data)


def _find_config() -> Optional[Path]:
    """Walk up directories looking for agent.guard.yml."""
    names = ["agent.guard.yml", "agentguard.yml"]
    current = Path.cwd()
    for _ in range(6):
        for name in names:
            candidate = current / name
            if candidate.exists():
                return candidate
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def _parse(data: dict) -> AgentGuardConfig:
    cfg = AgentGuardConfig()
    cfg.version = data.get("version", "1.0")

    identity = data.get("identity", {})
    cfg.identity_name = identity.get("name", "agent")

    # Model
    model_data = data.get("model", {})
    cfg.model = ModelConfig(
        provider=model_data.get("provider", "openai"),
        model=model_data.get("model", "gpt-4o"),
        api_key_env=model_data.get("api_key_env", "OPENAI_API_KEY"),
    )

    # Permissions
    perms = data.get("permissions", {})
    net = perms.get("network", {})
    exe = perms.get("execution", {})
    cfg.permissions = PermissionsConfig(
        network=NetworkConfig(
            mode=net.get("mode", "open"),
            allow=net.get("allow", []),
            deny=net.get("deny", []),
        ),
        execution=ExecutionConfig(
            allow_shell=exe.get("allow_shell", False),
            allow_subprocess=exe.get("allow_subprocess", False),
        ),
    )

    # Guardrails
    gr = data.get("guardrails", {})
    inp = gr.get("input", {})
    out = gr.get("output", {})
    beh = gr.get("behavior", {})
    cfg.guardrails = GuardrailsConfig(
        input=InputGuardrails(
            block_prompt_injection=inp.get("block_prompt_injection", True),
            max_tokens=inp.get("max_tokens", 4096),
            pii_detection=inp.get("pii_detection", "off"),
            content_filter=inp.get("content_filter", "off"),
        ),
        output=OutputGuardrails(
            block_harmful_content=out.get("block_harmful_content", False),
            max_output_tokens=out.get("max_output_tokens", 8192),
            pii_redaction=out.get("pii_redaction", False),
        ),
        behavior=BehaviorGuardrails(
            max_iterations=beh.get("max_iterations", 20),
            timeout=beh.get("timeout", "5m"),
            max_tool_calls=beh.get("max_tool_calls", 50),
            retry_limit=beh.get("retry_limit", 3),
            cost_limit=beh.get("cost_limit"),
            human_approval_after=beh.get("human_approval_after"),
        ),
    )

    return cfg
