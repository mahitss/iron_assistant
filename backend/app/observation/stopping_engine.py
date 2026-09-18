"""Stopping Intelligence and Marginal Threshold Governance for Task 114.
Prevents infinite observation loops and terminates gathering when uncertainty is sufficiently reduced or insensitive.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.observation.domain import (
    InformationGap,
    ObservationBudget,
    ObservationCandidate,
    ObservationMethodType,
    ObservationPlan,
    StopConditionReason,
    UncertaintyState,
)

logger = logging.getLogger("kairo.observation.stopping_engine")


class StoppingIntelligenceEngine:
    """Evaluates stopping conditions and recommended operational stance (Section 16, 63, 64)."""

    @classmethod
    def evaluate_stopping(
        cls,
        plan: ObservationPlan,
        elapsed_seconds: float = 0.0,
        deadline_seconds: Optional[float] = None,
    ) -> Tuple[bool, Optional[StopConditionReason], str]:
        """Returns (should_stop, stop_reason, recommended_stance)."""

        # 1. Check if all gaps are already resolved by existing data
        if plan.gaps and all(g.is_resolved_by_existing_data for g in plan.gaps):
            return True, StopConditionReason.NO_OBSERVATION_NEEDED, "NO FURTHER INFORMATION NEEDED"

        # 2. Check Resource Economy Budget Exhaustion (Section 42)
        if plan.budget.remaining_units <= 0.0 or plan.budget.spent_units >= plan.budget.allocated_units:
            return True, StopConditionReason.BUDGET_EXHAUSTED, "ACT NOW"

        # 3. Check Deadline Exceeded (Section 45)
        if deadline_seconds and elapsed_seconds >= deadline_seconds:
            return True, StopConditionReason.DEADLINE_REACHED, "ACT NOW"

        # 4. Check Decision Insensitivity across all gaps (Section 8)
        if plan.sensitivities and all(not s.is_decision_sensitive for s in plan.sensitivities.values()):
            return True, StopConditionReason.DECISION_INSENSITIVE, "NO FURTHER INFORMATION NEEDED"

        # 5. Check Sufficient Information (Section 16)
        if plan.uncertainty_after and plan.uncertainty_after.overall_confidence >= 0.85:
            has_critical_unknown = any(
                d.is_critical and d.level.value in {"UNKNOWN", "CONTESTED", "STALE"}
                for d in plan.uncertainty_after.dimensions.values()
            )
            if not has_critical_unknown:
                return True, StopConditionReason.SUFFICIENT_INFORMATION, "ACT NOW"

        # 6. Check User Clarification Required (Section 19)
        has_intent_gap = any(
            "intent" in g.affected_state.lower() and not g.is_resolved_by_existing_data
            for g in plan.gaps
        )
        if has_intent_gap:
            return False, None, "ASK USER"

        # 7. Check if best remaining candidate is WAIT (Section 17)
        selectable_candidates = [
            c for c in plan.candidates
            if not c.is_blocked and c.value_estimate and not c.value_estimate.is_redundant
        ]
        if not selectable_candidates:
            return True, StopConditionReason.NO_USEFUL_SOURCE, "NO FURTHER INFORMATION NEEDED"

        best_cand = max(selectable_candidates, key=lambda c: c.value_estimate.net_value_score if c.value_estimate else -1.0)
        if best_cand.method == ObservationMethodType.WAIT:
            return False, None, "WAIT"

        # 8. Check Marginal Value Decay below Threshold (Section 64)
        if best_cand.value_estimate and best_cand.value_estimate.marginal_value < 0.10:
            return True, StopConditionReason.SUFFICIENT_INFORMATION, "NO FURTHER INFORMATION NEEDED"

        # Default stance: Proceed to observe
        return False, None, "OBSERVE"
