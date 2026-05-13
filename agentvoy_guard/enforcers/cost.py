"""
Cost tracking enforcer.
Tracks token usage and enforces cost_limit from agent.guard.yml.
"""

from __future__ import annotations
from ..exceptions import CostLimitError

# Pricing per 1M tokens (input, output) in USD — updated May 2026
PRICING: dict[str, tuple[float, float]] = {
    # OpenAI
    "gpt-4o":                  (2.50,  10.00),
    "gpt-4o-mini":             (0.15,   0.60),
    "gpt-4-turbo":             (10.00, 30.00),
    "o1":                      (15.00, 60.00),
    "o1-mini":                 (3.00,  12.00),
    # Anthropic
    "claude-opus-4-20250514":         (15.00, 75.00),
    "claude-sonnet-4-20250514":       (3.00,  15.00),
    "claude-haiku-4-5-20251001":      (0.80,   4.00),
    # Google
    "gemini-2.0-flash":        (0.075,  0.30),
    "gemini-2.5-pro":          (1.25,  10.00),
    # Groq (approximation)
    "llama-3.3-70b-versatile": (0.59,   0.79),
    # Mistral
    "mistral-large-latest":    (2.00,   6.00),
}

DEFAULT_PRICING = (1.00, 3.00)   # fallback per 1M tokens


class CostEnforcer:
    def __init__(self, model: str, cost_limit: float | None):
        self.model = model
        self.cost_limit = cost_limit
        self._input_tokens = 0
        self._output_tokens = 0

        pricing = PRICING.get(model, DEFAULT_PRICING)
        self._input_price = pricing[0] / 1_000_000
        self._output_price = pricing[1] / 1_000_000

    def track(self, input_tokens: int = 0, output_tokens: int = 0):
        """Record token usage and check against cost limit."""
        self._input_tokens += input_tokens
        self._output_tokens += output_tokens

        if self.cost_limit is not None:
            current = self.current_cost
            if current >= self.cost_limit:
                raise CostLimitError(self.cost_limit, current)

    def track_usage_object(self, usage: object):
        """
        Accept a usage object from any SDK.
        Handles: anthropic, openai, google style usage objects.
        """
        input_tokens = (
            getattr(usage, "input_tokens", None)
            or getattr(usage, "prompt_tokens", None)
            or 0
        )
        output_tokens = (
            getattr(usage, "output_tokens", None)
            or getattr(usage, "completion_tokens", None)
            or 0
        )
        self.track(input_tokens=input_tokens, output_tokens=output_tokens)

    @property
    def current_cost(self) -> float:
        return (
            self._input_tokens * self._input_price
            + self._output_tokens * self._output_price
        )

    @property
    def summary(self) -> dict:
        return {
            "input_tokens": self._input_tokens,
            "output_tokens": self._output_tokens,
            "total_tokens": self._input_tokens + self._output_tokens,
            "estimated_cost_usd": round(self.current_cost, 6),
        }
