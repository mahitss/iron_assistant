"""Cognitive Resource Allocation, EVOA & VOI Engine (Task 70).

Manages cognitive resource budgets:
- reasoning capacity
- tool quota
- agent slots
- compute budget
- context tokens
- human attention slots
- execution slots

Computes:
- Expected Value of Attention (EVOA = expected_benefit - cost)
- Value of Information (VOI = uncertainty_reduction * decision_impact - cost)
"""

from typing import Any

from app.attention.schemas import CognitiveResourceBudget


class CognitiveResourceManager:
    """Tracks and allocates bounded cognitive resources and computes EVOA/VOI."""

    def __init__(self, initial_budget: CognitiveResourceBudget | None = None):
        self.budget = initial_budget or CognitiveResourceBudget()

    def can_allocate(
        self,
        *,
        estimated_effort: float = 1.0,
        estimated_tool_calls: int = 1,
        requires_agent: bool = False,
        estimated_tokens: int = 2000,
    ) -> tuple[bool, str]:
        """Check if cognitive resources exist for a candidate."""
        # 1. Check reasoning capacity
        required_reasoning = min(50.0, estimated_effort * 15.0)
        if self.budget.reasoning_capacity_pct < required_reasoning:
            return (
                False,
                f"Insufficient reasoning capacity ({self.budget.reasoning_capacity_pct:.1f}% available)",
            )

        # 2. Check tool budget
        if self.budget.active_tool_calls + estimated_tool_calls > self.budget.max_tool_calls:
            return (
                False,
                f"Tool call quota exceeded ({self.budget.active_tool_calls}/{self.budget.max_tool_calls})",
            )

        # 3. Check agent slots
        if requires_agent and self.budget.active_agent_slots >= self.budget.max_agent_slots:
            return (
                False,
                f"All agent slots in use ({self.budget.active_agent_slots}/{self.budget.max_agent_slots})",
            )

        # 4. Check context token budget
        if self.budget.context_tokens_used + estimated_tokens > self.budget.context_token_budget:
            return False, (
                f"Context budget exceeded ({self.budget.context_tokens_used + estimated_tokens} > "
                f"{self.budget.context_token_budget})"
            )

        # 5. Check execution slots
        if self.budget.execution_slots_used >= self.budget.max_execution_slots:
            return (
                False,
                f"Execution slots full ({self.budget.execution_slots_used}/{self.budget.max_execution_slots})",
            )

        return True, "Resources available"

    def allocate(
        self,
        *,
        estimated_effort: float = 1.0,
        estimated_tool_calls: int = 1,
        requires_agent: bool = False,
        estimated_tokens: int = 2000,
    ) -> bool:
        """Allocate resources for active attention."""
        can, _ = self.can_allocate(
            estimated_effort=estimated_effort,
            estimated_tool_calls=estimated_tool_calls,
            requires_agent=requires_agent,
            estimated_tokens=estimated_tokens,
        )
        if not can:
            return False

        required_reasoning = min(50.0, estimated_effort * 15.0)
        self.budget.reasoning_capacity_pct = max(0.0, self.budget.reasoning_capacity_pct - required_reasoning)
        self.budget.active_tool_calls += estimated_tool_calls
        if requires_agent:
            self.budget.active_agent_slots += 1
        self.budget.context_tokens_used += estimated_tokens
        self.budget.execution_slots_used += 1
        return True

    def release(
        self,
        *,
        estimated_effort: float = 1.0,
        estimated_tool_calls: int = 1,
        requires_agent: bool = False,
        estimated_tokens: int = 2000,
    ) -> None:
        """Release allocated resources upon completion, pause, or delegation."""
        restored_reasoning = min(50.0, estimated_effort * 15.0)
        self.budget.reasoning_capacity_pct = min(
            100.0, self.budget.reasoning_capacity_pct + restored_reasoning
        )
        self.budget.active_tool_calls = max(0, self.budget.active_tool_calls - estimated_tool_calls)
        if requires_agent:
            self.budget.active_agent_slots = max(0, self.budget.active_agent_slots - 1)
        self.budget.context_tokens_used = max(0, self.budget.context_tokens_used - estimated_tokens)
        self.budget.execution_slots_used = max(0, self.budget.execution_slots_used - 1)

    @staticmethod
    def compute_evoa(
        *,
        importance: float,
        risk_reduction: float,
        goal_progress: float,
        user_value: float,
        estimated_effort: float,
        cost_weight: float = 0.2,
    ) -> tuple[float, str, dict[str, float]]:
        """Compute Expected Value of Attention (EVOA = benefit - cost)."""
        benefit = (importance * 0.35) + (risk_reduction * 0.35) + (goal_progress * 0.15) + (user_value * 0.15)
        cost = min(1.0, (estimated_effort / 5.0) * cost_weight)
        net_evoa = round(benefit - cost, 3)

        if net_evoa >= 0.6:
            tier = "HIGH_VALUE"
        elif net_evoa >= 0.3:
            tier = "EFFICIENT"
        elif net_evoa >= 0.0:
            tier = "NEUTRAL"
        else:
            tier = "INEFFICIENT"

        breakdown = {
            "benefit": round(benefit, 3),
            "cost": round(cost, 3),
            "net_evoa": net_evoa,
        }
        return net_evoa, tier, breakdown

    @staticmethod
    def compute_voi(
        *,
        uncertainty: float,
        decision_consequence: float,
        investigation_cost: float = 0.1,
    ) -> tuple[float, bool, dict[str, Any]]:
        """Compute Value of Information (VOI).

        High uncertainty on a high-consequence decision yields high VOI.
        If investigation will not alter the decision path or costs too much, VOI is low.
        """
        raw_gain = max(0.0, min(1.0, uncertainty)) * max(0.0, min(1.0, decision_consequence))
        cost = max(0.0, min(1.0, investigation_cost))
        net_voi = round(raw_gain - cost, 3)
        worth_investigating = net_voi > 0.15

        explanation = (
            f"Value of Information is {net_voi:.3f} (uncertainty={uncertainty:.2f}, "
            f"consequence={decision_consequence:.2f}, cost={cost:.2f}). "
            f"{'Investigation justified.' if worth_investigating else 'Investigation not justified.'}"
        )

        breakdown = {
            "uncertainty": round(uncertainty, 3),
            "decision_consequence": round(decision_consequence, 3),
            "investigation_cost": round(cost, 3),
            "net_voi": net_voi,
            "worth_investigating": worth_investigating,
            "explanation": explanation,
        }
        return net_voi, worth_investigating, breakdown
