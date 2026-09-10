"""Decision outcome tracking and prediction-versus-reality comparison for Task 57.

Records verified post-execution outcomes, evaluates prediction errors, and tracks
unexpected side effects to feed calibration and adaptive learning.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.decision.schemas import DecisionOutcome, OptionEvaluation


class OutcomeTracker:
    """Tracks post-execution outcomes and quantifies divergence from predictions."""

    def record_outcome(
        self,
        decision_id: str,
        predicted_evaluation: OptionEvaluation | None,
        actual_benefit: float,
        actual_cost: float,
        actual_duration: float,
        success: bool = True,
        unexpected_side_effects: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> DecisionOutcome:
        side_effects = unexpected_side_effects or []

        # Compare predicted benefit vs actual
        pred_benefit = predicted_evaluation.benefit_score if predicted_evaluation else 0.0
        pred_cost = predicted_evaluation.cost_penalty if predicted_evaluation else 0.0

        benefit_err = abs(pred_benefit - actual_benefit)
        cost_err = abs(pred_cost - actual_cost)
        total_error = round(benefit_err + cost_err, 3)

        return DecisionOutcome(
            decision_id=decision_id,
            actual_benefit=actual_benefit,
            actual_cost=actual_cost,
            actual_duration=actual_duration,
            prediction_error=total_error,
            unexpected_side_effects=side_effects,
            success=success,
            recorded_at=datetime.now(timezone.utc),
            metadata=metadata or {},
        )


outcome_tracker = OutcomeTracker()
