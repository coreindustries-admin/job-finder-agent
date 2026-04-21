"""
Cost tracking for Claude API usage.

Tracks input/output tokens per call, calculates dollar cost based on model pricing.
Provides per-job and per-run cost summaries.
"""

import logging

logger = logging.getLogger(__name__)

# Pricing per million tokens (as of April 2026)
# https://docs.anthropic.com/en/docs/about-claude/models
MODEL_PRICING = {
    # Sonnet 4.6
    "claude-sonnet-4-6-20250620": {"input": 3.00, "output": 15.00},
    # Sonnet 4 (deprecated but still used)
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    # Haiku 4.5
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
    # Opus 4.6
    "claude-opus-4-6-20250620": {"input": 15.00, "output": 75.00},
}


class CostTracker:
    """Tracks token usage and calculates costs across a pipeline run."""

    def __init__(self):
        self.calls = []
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def record(self, model: str, input_tokens: int, output_tokens: int):
        """Record a single API call's usage."""
        pricing = MODEL_PRICING.get(model, {"input": 3.00, "output": 15.00})

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        total_cost = input_cost + output_cost

        self.calls.append({
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": total_cost,
        })

        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

    @property
    def total_cost(self) -> float:
        """Total cost in dollars for all recorded calls."""
        return sum(call["cost"] for call in self.calls)

    @property
    def num_calls(self) -> int:
        return len(self.calls)

    @property
    def avg_cost_per_call(self) -> float:
        if not self.calls:
            return 0.0
        return self.total_cost / len(self.calls)

    def summary(self) -> str:
        """Return a human-readable cost summary."""
        if not self.calls:
            return "No API calls recorded."

        return (
            f"API Usage Summary:\n"
            f"  Calls: {self.num_calls}\n"
            f"  Input tokens: {self.total_input_tokens:,}\n"
            f"  Output tokens: {self.total_output_tokens:,}\n"
            f"  Total cost: ${self.total_cost:.4f}\n"
            f"  Avg cost/job: ${self.avg_cost_per_call:.4f}\n"
            f"  Projected daily (100 jobs): ${self.avg_cost_per_call * 100:.2f}\n"
            f"  Projected monthly (3000 jobs): ${self.avg_cost_per_call * 3000:.2f}"
        )


# Global tracker instance (reset per pipeline run)
tracker = CostTracker()


def reset():
    """Reset the global tracker for a new run."""
    global tracker
    tracker = CostTracker()
