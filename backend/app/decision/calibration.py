"""Decision quality analytics, calibration, and override analysis for Task 57.

Compares confidence against actual outcomes, measures calibration error,
and detects systematic overconfidence or override patterns without confusing user acceptance with correctness.
"""

from __future__ import annotations

from typing import Any

from app.decision.schemas import DecisionOutcome, DecisionRecord


class DecisionCalibrationEngine:
    """Evaluates decision engine calibration and quality metrics across historical decisions."""

    def compute_analytics(
        self,
        records: list[DecisionRecord],
        outcomes: list[DecisionOutcome],
    ) -> dict[str, Any]:
        total_decisions = len(records)
        if total_decisions == 0:
            return {
                "total_decisions": 0,
                "acceptance_rate": 0.0,
                "override_rate": 0.0,
                "success_rate": 0.0,
                "average_confidence": 0.0,
                "calibration_error": 0.0,
                "calibration_assessment": "NO_DATA",
            }

        override_count = sum(1 for r in records if r.user_override)
        acceptance_count = total_decisions - override_count
        override_rate = round(override_count / total_decisions, 3)
        acceptance_rate = round(acceptance_count / total_decisions, 3)

        avg_confidence = round(sum(r.confidence for r in records) / total_decisions, 3)

        # Outcomes analysis
        outcome_by_dec = {o.decision_id: o for o in outcomes}
        matching_outcomes = [outcome_by_dec[r.decision_id] for r in records if r.decision_id in outcome_by_dec]

        if matching_outcomes:
            success_count = sum(1 for o in matching_outcomes if o.success)
            actual_success_rate = round(success_count / len(matching_outcomes), 3)
            avg_prediction_error = round(sum(o.prediction_error for o in matching_outcomes) / len(matching_outcomes), 3)
            # Expected Calibration Error (ECE approximation)
            calibration_error = round(abs(avg_confidence - actual_success_rate), 3)
        else:
            actual_success_rate = 0.0
            avg_prediction_error = 0.0
            calibration_error = 0.0

        if matching_outcomes and avg_confidence > (actual_success_rate + 0.15):
            cal_assessment = "OVERCONFIDENT"
        elif matching_outcomes and avg_confidence < (actual_success_rate - 0.15):
            cal_assessment = "UNDERCONFIDENT"
        elif matching_outcomes:
            cal_assessment = "WELL_CALIBRATED"
        else:
            cal_assessment = "AWAITING_OUTCOMES"

        return {
            "total_decisions": total_decisions,
            "recorded_outcomes": len(matching_outcomes),
            "acceptance_rate": acceptance_rate,
            "override_rate": override_rate,
            "actual_success_rate": actual_success_rate,
            "average_confidence": avg_confidence,
            "average_prediction_error": avg_prediction_error,
            "calibration_error": calibration_error,
            "calibration_assessment": cal_assessment,
        }

    def analyze_overrides(
        self,
        records: list[DecisionRecord],
    ) -> list[dict[str, Any]]:
        """Analyzes patterns behind user overrides to identify potential blind spots."""
        overrides: list[dict[str, Any]] = []
        for r in records:
            if not r.user_override or not r.recommendation:
                continue

            recommended_id = r.recommendation.recommended_option_id
            chosen_id = r.selected_option_id

            overrides.append({
                "decision_id": r.decision_id,
                "request_id": r.request_id,
                "recommended_option": recommended_id,
                "user_selected_option": chosen_id,
                "user": r.selected_by,
                "confidence_at_recommendation": r.confidence,
                "assumptions_count": len(r.recommendation.assumptions),
                "recorded_at": r.updated_at.isoformat(),
            })

        return overrides


decision_calibration_engine = DecisionCalibrationEngine()
