"""Resource Budget Enforcement, Quota Tracking, and Starvation Prevention (Task 44)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("kairo.agents.budgets")


def utc_now() -> datetime:
    return datetime.now(UTC)


class BudgetExhaustedError(Exception):
    """Raised when an agent attempts an operation after consuming its allocated budget."""


@dataclass
class AgentBudget:
    """Resource quota assigned to an agent execution (Spec 87, 88)."""

    max_tokens: int = 50000
    max_tool_calls: int = 15
    max_duration_seconds: float = 180.0
    max_cost_usd: float = 0.25
    max_cost: float = 0.25

    used_tokens: int = 0
    used_tool_calls: int = 0
    elapsed_duration_seconds: float = 0.0
    used_cost_usd: float = 0.0

    def __post_init__(self):
        if self.max_cost != 0.25 and self.max_cost_usd == 0.25:
            self.max_cost_usd = self.max_cost
        elif self.max_cost_usd != 0.25 and self.max_cost == 0.25:
            self.max_cost = self.max_cost_usd

    @property
    def is_exhausted(self) -> bool:
        return (
            self.used_tokens >= self.max_tokens
            or self.used_tool_calls >= self.max_tool_calls
            or self.elapsed_duration_seconds >= self.max_duration_seconds
            or self.used_cost_usd >= self.max_cost_usd
        )

    def consume(
        self,
        tokens: int = 0,
        tool_calls: int = 0,
        duration_seconds: float = 0.0,
        cost: float = 0.0,
    ) -> None:
        """Deduct resource consumption and raise BudgetExhaustedError if limit exceeded."""
        if (
            (self.used_tokens + tokens > self.max_tokens)
            or (self.used_tool_calls + tool_calls > self.max_tool_calls)
            or (self.used_cost_usd + cost > self.max_cost_usd)
        ):
            raise BudgetExhaustedError("BLOCKED/BUDGET_EXHAUSTED: Agent resource quota exceeded.")

        self.used_tokens += tokens
        self.used_tool_calls += tool_calls
        self.elapsed_duration_seconds += duration_seconds
        self.used_cost_usd += cost

    def record_consumption(
        self,
        tokens: int = 0,
        tool_calls: int = 0,
        duration_seconds: float = 0.0,
        cost_usd: float = 0.0,
    ) -> None:
        self.consume(tokens=tokens, tool_calls=tool_calls, duration_seconds=duration_seconds, cost=cost_usd)


    def to_dict(self) -> dict[str, Any]:
        return {
            "max_tokens": self.max_tokens,
            "used_tokens": self.used_tokens,
            "max_tool_calls": self.max_tool_calls,
            "used_tool_calls": self.used_tool_calls,
            "max_duration_seconds": self.max_duration_seconds,
            "elapsed_duration_seconds": round(self.elapsed_duration_seconds, 2),
            "max_cost_usd": self.max_cost_usd,
            "used_cost_usd": round(self.used_cost_usd, 4),
            "is_exhausted": self.is_exhausted,
        }
