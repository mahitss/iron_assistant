"""Resource awareness, pressure tracking, cost accounting, and budget gating (INVARIANTS 91-93)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from app.metacognition.schemas import ResourceStateSchema


class ResourceBudgetExceededError(Exception):
    """Raised when an operation is requested with insufficient computational or API budget."""
    pass


class ResourceAwarenessTracker:
    """Tracks system latency, memory/compute pressure, token counts, and API budget limits."""

    def __init__(self, api_budget_limit_usd: float = 100.0) -> None:
        self.state = ResourceStateSchema()
        self.api_budget_limit_usd = api_budget_limit_usd

    def record_usage(self, tokens_used: int, estimated_cost_usd: float, latency_ms: float) -> None:
        self.state.active_tokens += tokens_used
        self.state.cost_usd += estimated_cost_usd
        self.state.latency_ms = round((self.state.latency_ms * 0.8) + (latency_ms * 0.2), 2)

        # Update remaining budget percentage
        if self.api_budget_limit_usd > 0:
            pct = max(0.0, 100.0 * (1.0 - (self.state.cost_usd / self.api_budget_limit_usd)))
            self.state.api_budget_remaining_percent = round(pct, 2)

    def set_rate_limited_tool(self, tool_name: str, is_limited: bool = True) -> None:
        if is_limited and tool_name not in self.state.rate_limited_tools:
            self.state.rate_limited_tools.append(tool_name)
        elif not is_limited and tool_name in self.state.rate_limited_tools:
            self.state.rate_limited_tools.remove(tool_name)

    def assert_resource_available(self, requested_tokens: int = 0) -> None:
        """INVARIANT 92: If resources are insufficient, stops execution safely."""
        if self.state.api_budget_remaining_percent <= 1.0:
            raise ResourceBudgetExceededError(
                "Operational API budget exhausted. Execution halted safely to prevent overages."
            )
        if self.state.compute_pressure == "EXHAUSTED":
            raise ResourceBudgetExceededError(
                "System compute resources exhausted. Operation paused."
            )

    def get_state(self) -> ResourceStateSchema:
        return self.state
