"""
AgentVoy Guard exceptions — all guardrail violations raise these.
"""


class GuardError(Exception):
    """Base class for all guardrail violations."""
    pass


class IterationLimitError(GuardError):
    """Raised when max_iterations is exceeded."""
    def __init__(self, limit: int):
        super().__init__(f"Agent exceeded max_iterations limit of {limit}")
        self.limit = limit


class ToolCallLimitError(GuardError):
    """Raised when max_tool_calls is exceeded."""
    def __init__(self, limit: int):
        super().__init__(f"Agent exceeded max_tool_calls limit of {limit}")
        self.limit = limit


class CostLimitError(GuardError):
    """Raised when cost_limit is exceeded."""
    def __init__(self, limit: float, current: float):
        super().__init__(
            f"Agent exceeded cost limit of ${limit:.4f} (current: ${current:.4f})"
        )
        self.limit = limit
        self.current = current


class TimeoutError(GuardError):
    """Raised when agent execution exceeds the timeout."""
    def __init__(self, timeout_seconds: float):
        super().__init__(f"Agent execution timed out after {timeout_seconds:.0f}s")
        self.timeout_seconds = timeout_seconds


class PromptInjectionError(GuardError):
    """Raised when a prompt injection attempt is detected."""
    def __init__(self, pattern: str):
        super().__init__(f"Prompt injection detected: {pattern!r}")
        self.pattern = pattern


class PIIDetectedError(GuardError):
    """Raised when PII is detected and mode is 'block'."""
    def __init__(self, pii_types: list[str]):
        super().__init__(f"PII detected in input: {', '.join(pii_types)}")
        self.pii_types = pii_types


class NetworkBlockedError(GuardError):
    """Raised when a network request is blocked by permissions."""
    def __init__(self, url: str, reason: str):
        super().__init__(f"Network request blocked: {url!r} — {reason}")
        self.url = url
        self.reason = reason


class ShellBlockedError(GuardError):
    """Raised when shell/subprocess execution is blocked."""
    def __init__(self, command: str = ""):
        super().__init__(
            f"Shell execution blocked by agent.guard.yml (allow_shell: false)"
            + (f": {command!r}" if command else "")
        )
        self.command = command
