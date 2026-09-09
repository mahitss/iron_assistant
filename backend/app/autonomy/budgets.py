"""Resource Quota Tracking, Multi-Factor Budgets, and Propagation (Task 45)."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any, Dict

logger = logging.getLogger("kairo.autonomy.budgets")


class BudgetExhaustedError(Exception):
    """Raised when an autonomous run or child step exceeds its allocated budget."""


@dataclass
class AutonomousBudget:
    """Comprehensive resource budget bounding autonomous execution (Spec 54, 55)."""

    max_model_calls: int = 100
    max_tool_calls: int = 50
    max_agent_calls: int = 20
    max_external_calls: int = 30
    max_compute_seconds: float = 600.0
    max_cost_usd: float = 5.0

    used_model_calls: int = 0
    used_tool_calls: int = 0
    used_agent_calls: int = 0
    used_external_calls: int = 0
    used_compute_seconds: float = 0.0
    used_cost_usd: float = 0.0

    @property
    def is_exhausted(self) -> bool:
        return (
            self.used_model_calls >= self.max_model_calls
            or self.used_tool_calls >= self.max_tool_calls
            or self.used_agent_calls >= self.max_agent_calls
            or self.used_external_calls >= self.max_external_calls
            or self.used_compute_seconds >= self.max_compute_seconds
            or self.used_cost_usd >= self.max_cost_usd
        )

    def check_and_consume(
        self,
        model_calls: int = 0,
        tool_calls: int = 0,
        agent_calls: int = 0,
        external_calls: int = 0,
        compute_seconds: float = 0.0,
        cost_usd: float = 0.0,
    ) -> None:
        """Pre-check and record resource consumption (Spec 56)."""
        if (
            (self.used_model_calls + model_calls > self.max_model_calls)
            or (self.used_tool_calls + tool_calls > self.max_tool_calls)
            or (self.used_agent_calls + agent_calls > self.max_agent_calls)
            or (self.used_external_calls + external_calls > self.max_external_calls)
            or (self.used_compute_seconds + compute_seconds > self.max_compute_seconds)
            or (self.used_cost_usd + cost_usd > self.max_cost_usd)
        ):
            logger.warning("Autonomous budget exhausted: %s", self.to_dict())
            raise BudgetExhaustedError("BLOCKED/BUDGET_EXHAUSTED: Autonomous execution quota exceeded.")

        self.used_model_calls += model_calls
        self.used_tool_calls += tool_calls
        self.used_agent_calls += agent_calls
        self.used_external_calls += external_calls
        self.used_compute_seconds += compute_seconds
        self.used_cost_usd += cost_usd

    def derive_child_budget(self, fraction: float = 0.5) -> AutonomousBudget:
        """Propagate bounded sub-budget to child task or delegated agent (Spec 55)."""
        fraction = max(0.1, min(fraction, 0.9))
        remaining_models = max(1, int((self.max_model_calls - self.used_model_calls) * fraction))
        remaining_tools = max(1, int((self.max_tool_calls - self.used_tool_calls) * fraction))
        remaining_cost = max(0.01, (self.max_cost_usd - self.used_cost_usd) * fraction)

        return AutonomousBudget(
            max_model_calls=remaining_models,
            max_tool_calls=remaining_tools,
            max_cost_usd=round(remaining_cost, 4),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_model_calls": self.max_model_calls,
            "used_model_calls": self.used_model_calls,
            "max_tool_calls": self.max_tool_calls,
            "used_tool_calls": self.used_tool_calls,
            "max_agent_calls": self.max_agent_calls,
            "used_agent_calls": self.used_agent_calls,
            "max_compute_seconds": self.max_compute_seconds,
            "used_compute_seconds": round(self.used_compute_seconds, 2),
            "max_cost_usd": self.max_cost_usd,
            "used_cost_usd": round(self.used_cost_usd, 4),
            "is_exhausted": self.is_exhausted,
        }
