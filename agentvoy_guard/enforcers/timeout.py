"""
Timeout enforcer using threading.
Works cross-platform (unlike signal-based approach which is Unix-only).
"""

from __future__ import annotations
import threading
import time
from ..exceptions import TimeoutError


class TimeoutEnforcer:
    def __init__(self, timeout_seconds: float):
        self.timeout_seconds = timeout_seconds
        self._start_time: float | None = None
        self._timer: threading.Timer | None = None
        self._timed_out = False

    def start(self):
        """Start the timeout clock."""
        self._start_time = time.monotonic()
        self._timed_out = False
        self._timer = threading.Timer(self.timeout_seconds, self._on_timeout)
        self._timer.daemon = True
        self._timer.start()

    def stop(self):
        """Cancel the timeout timer."""
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def check(self):
        """Manually check if timeout has been exceeded."""
        if self._timed_out:
            raise TimeoutError(self.timeout_seconds)
        if self._start_time is not None:
            elapsed = time.monotonic() - self._start_time
            if elapsed >= self.timeout_seconds:
                raise TimeoutError(self.timeout_seconds)

    def _on_timeout(self):
        self._timed_out = True

    @property
    def elapsed(self) -> float:
        if self._start_time is None:
            return 0.0
        return time.monotonic() - self._start_time
