"""Downstream Decision Sensitivity Analysis Engine for Task 114.
Determines whether resolving an uncertainty has material leverage to change downstream actions or decisions.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.observation.domain import (
    DecisionSensitivity,
    InformationGap,
    UncertaintyDimensionType,
)


class DecisionSensitivityEngine:
    """Evaluates whether resolving an unknown can materially alter a decision branch (Section 8, 46)."""

    @classmethod
    def evaluate_sensitivity(
        cls,
        gap: InformationGap,
        dependent_decision: Optional[Dict[str, Any]] = None,
        candidate_actions: Optional[List[Dict[str, Any]]] = None,
    ) -> DecisionSensitivity:
        candidate_actions = candidate_actions or []
        decisions_affected: List[str] = []
        actions_affected: List[str] = []
        possible_branch_changes: List[str] = []

        if dependent_decision:
            dec_id = dependent_decision.get("decision_id", "dec_active")
            decisions_affected.append(dec_id)
            for opt in dependent_decision.get("options", []):
                opt_name = opt.get("name") or opt.get("option_id")
                if opt_name:
                    actions_affected.append(str(opt_name))

        # Check if gap is tied to critical operational or safety dimensions
        is_critical_dim = any(
            d in {
                UncertaintyDimensionType.STATE,
                UncertaintyDimensionType.CAPABILITY,
                UncertaintyDimensionType.CAUSAL,
                UncertaintyDimensionType.INTENT,
                UncertaintyDimensionType.DECISION,
            }
            for d in gap.uncertainty_dimensions
        )

        # Evaluate scenario: Decision Insensitivity (Section 8, Scenario C)
        # If candidate actions already have uniform risk or the decision would proceed identically regardless of the value
        if dependent_decision and dependent_decision.get("is_insensitive", False):
            return DecisionSensitivity(
                gap_id=gap.gap_id,
                decisions_affected=decisions_affected,
                actions_affected=actions_affected,
                is_decision_sensitive=False,
                sensitivity_score=0.1,
                possible_branch_changes=[],
                rationale="Downstream decision options remain invariant to the outcome of this unknown.",
            )

        # If options diverge (e.g. Action A vs Action B, or ACT vs WAIT)
        if len(actions_affected) >= 2 or is_critical_dim or gap.severity in {"HIGH", "CRITICAL"}:
            score = 0.85 if gap.severity == "CRITICAL" else 0.70
            possible_branch_changes.append("ACT_NOW vs WAIT_FOR_CONFIRMATION")
            if len(actions_affected) >= 2:
                possible_branch_changes.append(f"Switch between '{actions_affected[0]}' and '{actions_affected[1]}'")

            return DecisionSensitivity(
                gap_id=gap.gap_id,
                decisions_affected=decisions_affected,
                actions_affected=actions_affected,
                is_decision_sensitive=True,
                sensitivity_score=score,
                possible_branch_changes=possible_branch_changes,
                rationale=f"Resolving '{gap.affected_state}' directly discriminates between actionable alternatives.",
            )

        # Default moderate / low sensitivity
        return DecisionSensitivity(
            gap_id=gap.gap_id,
            decisions_affected=decisions_affected,
            actions_affected=actions_affected,
            is_decision_sensitive=False,
            sensitivity_score=0.25,
            possible_branch_changes=[],
            rationale="Information provides general context but is unlikely to trigger decision branch shifts.",
        )
