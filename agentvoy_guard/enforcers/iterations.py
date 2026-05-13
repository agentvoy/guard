from ..exceptions import IterationLimitError, ToolCallLimitError


class IterationEnforcer:
    def __init__(self, max_iterations: int, max_tool_calls: int):
        self.max_iterations = max_iterations
        self.max_tool_calls = max_tool_calls
        self._iterations = 0
        self._tool_calls = 0

    def tick(self):
        """Call once per agent loop iteration."""
        self._iterations += 1
        if self._iterations > self.max_iterations:
            raise IterationLimitError(self.max_iterations)

    def tick_tool(self):
        """Call once per tool invocation."""
        self._tool_calls += 1
        if self._tool_calls > self.max_tool_calls:
            raise ToolCallLimitError(self.max_tool_calls)

    @property
    def iterations(self) -> int:
        return self._iterations

    @property
    def tool_calls(self) -> int:
        return self._tool_calls
