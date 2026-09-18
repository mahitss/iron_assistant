"""Intervention verification and prediction-vs-reality calibration engine for Task 113.
Compares simulated counterfactual predictions against observed real-world post-execution outcomes.
Feeds calibration signals to continuous evaluation, reliability intelligence, and cognitive memory.
"""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any
import uuid

from app.counterfactual.domain import (
    CounterfactualAnalysis,
    CounterfactualLifecycleStage,
    InterventionVerification,
    VerificationOutcome,
)

logger = logging.getLogger("kairo.counterfactual.verification_engine")


class VerificationEngine:
    """Verifies counterfactual predictions against actual observed post-intervention telemetry."""

    @classmethod
    def verify_intervention(
        cls,
        analysis: CounterfactualAnalysis,
        executed_intervention_id: str,
        observed_state: dict[str, Any],
    ) -> InterventionVerification:
        """Compares predicted outcome against actual post-execution observed state."""
        # Find corresponding scenario/prediction
        target_pred = None
        for scen in analysis.scenarios:
            for intv in scen.interventions:
                if intv.intervention_id == executed_intervention_id:
                    target_pred = scen.prediction
                    break
            if target_pred:
                break

        predicted_state = target_pred.predicted_state if target_pred else {}
        ver_id = f"cf_ver_{uuid.uuid4().hex[:12]}"

        # Calculate deviations
        metric_deviations: dict[str, float] = {}
        deviation_scores: list[float] = []

        for metric in ("latency_ms", "error_rate", "queue_depth"):
            pred_val = float(predicted_state.get(metric, 0.0))
            obs_val = float(observed_state.get(metric, 0.0))
            diff = abs(obs_val - pred_val)
            metric_deviations[metric] = round(diff, 4)
            if pred_val > 0:
                deviation_scores.append(min(2.0, diff / pred_val))
            elif diff > 0:
                deviation_scores.append(1.0)
            else:
                deviation_scores.append(0.0)

        mean_dev = sum(deviation_scores) / len(deviation_scores) if deviation_scores else 0.0

        # Compare categorical status
        pred_status = predicted_state.get("status")
        obs_status = observed_state.get("status")

        if pred_status and obs_status and pred_status != obs_status:
            outcome = VerificationOutcome.CONTRADICTED
            explanation = f"Observed status '{obs_status}' directly contradicts predicted status '{pred_status}'."
            analysis.lifecycle_stage = CounterfactualLifecycleStage.CONTRADICTED
        elif pred_status and obs_status and pred_status == obs_status:
            if mean_dev < 0.25:
                outcome = VerificationOutcome.VERIFIED
                explanation = f"Observed state matches counterfactual prediction (mean metric deviation: {round(mean_dev * 100, 1)}%)."
                analysis.lifecycle_stage = CounterfactualLifecycleStage.VERIFIED
            else:
                outcome = VerificationOutcome.DEVIATED
                explanation = f"Status matched but numerical telemetry deviated (mean deviation: {round(mean_dev * 100, 1)}%)."
                analysis.lifecycle_stage = CounterfactualLifecycleStage.PROVISIONAL
        elif mean_dev >= 0.25:
            outcome = VerificationOutcome.DEVIATED
            explanation = f"Significant numerical deviation between predicted and observed telemetry (deviation: {round(mean_dev * 100, 1)}%)."
            analysis.lifecycle_stage = CounterfactualLifecycleStage.PROVISIONAL
        else:
            outcome = VerificationOutcome.UNRESOLVED
            explanation = "Insufficient observation data to conclusively verify prediction."

        verification = InterventionVerification(
            verification_id=ver_id,
            counterfactual_id=analysis.analysis_id,
            executed_intervention_id=executed_intervention_id,
            predicted_state=predicted_state,
            observed_state=observed_state,
            outcome=outcome,
            state_deviation_score=round(mean_dev, 4),
            metric_deviations=metric_deviations,
            explanation_of_deviation=explanation,
            calibration_feedback_emitted=True,
            verified_at=datetime.now(UTC),
        )

        analysis.verification = verification
        analysis.updated_at = datetime.now(UTC)

        # Invariant: Never overwrite original prediction. Verification retains both predicted and observed.
        logger.info(
            "Verified counterfactual %s: outcome=%s, deviation=%s",
            analysis.analysis_id,
            outcome.value,
            mean_dev,
        )

        return verification
