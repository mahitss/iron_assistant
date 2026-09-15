"""Metacognitive calibration, false positives, false negatives, and scorecards for Task 90."""

from __future__ import annotations

from collections import defaultdict
import logging
from typing import Any, Dict, List, Optional

from app.reliability_intelligence.models import (
    FalseNegativeRecord,
    FalsePositiveRecord,
    ForecastCalibrationRecord,
    PreventionActionType,
    PreventionStrategyScorecard,
    generate_ri_id,
    _now_utc,
)

logger = logging.getLogger("kairo.reliability_intelligence.calibration")


class CalibrationManager:
    """Tracks prediction accuracy, false alarms, missed failures, and prevention strategy scorecards."""

    def __init__(self) -> None:
        self._calibrations: List[ForecastCalibrationRecord] = []
        self._false_positives: List[FalsePositiveRecord] = []
        self._false_negatives: List[FalseNegativeRecord] = []
        self._scorecards: Dict[PreventionActionType, PreventionStrategyScorecard] = {
            strat: PreventionStrategyScorecard(strategy=strat) for strat in PreventionActionType
        }

    def record_calibration(
        self,
        incident_id: str,
        predicted_failure: str,
        actual_failure_occurred: bool,
        predicted_horizon: str,
        predicted_confidence: float,
        actual_horizon_seconds: Optional[float] = None,
        predicted_impact_score: float = 0.5,
        actual_impact_score: Optional[float] = None,
        intervention_executed: bool = False,
    ) -> ForecastCalibrationRecord:
        """Records pairing between predicted outcome and verified reality (Section 48)."""
        # Correctness score: 1.0 if prediction matched outcome, 0.0 if false alarm/miss
        correctness = 1.0 if actual_failure_occurred else 0.0

        rec = ForecastCalibrationRecord(
            calibration_id=generate_ri_id("calib"),
            incident_id=incident_id,
            predicted_failure=predicted_failure,
            actual_failure_occurred=actual_failure_occurred,
            predicted_horizon=predicted_horizon,
            actual_horizon_seconds=actual_horizon_seconds,
            predicted_confidence=predicted_confidence,
            actual_correctness=correctness,
            predicted_impact_score=predicted_impact_score,
            actual_impact_score=actual_impact_score,
            intervention_executed=intervention_executed,
        )
        self._calibrations.append(rec)
        return rec

    def record_false_positive(
        self,
        incident_id: str,
        signal_type: Any,
        confidence: float,
        evidence: Dict[str, Any],
        intervention_occurred: bool = False,
    ) -> FalsePositiveRecord:
        """Records a prediction where failure did NOT manifest (Section 49)."""
        rec = FalsePositiveRecord(
            fp_id=generate_ri_id("fp"),
            incident_id=incident_id,
            signal_type=signal_type,
            confidence=confidence,
            evidence=evidence,
            outcome="NO_FAILURE_OBSERVED",
            intervention_occurred=intervention_occurred,
        )
        self._false_positives.append(rec)
        logger.info("Recorded False Positive warning for incident %s (confidence=%.2f)", incident_id, confidence)
        return rec

    def record_false_negative(
        self,
        failure_id: str,
        component: str,
        failure_description: str,
        observable_precursor_present: bool = False,
        precursor_detected: bool = False,
        forecast_attempted: bool = False,
        root_cause_of_miss: str = "MODEL_BLIND_SPOT",
        remediation_note: str = "",
    ) -> FalseNegativeRecord:
        """Records an unpredicted failure to detect blind spots in telemetry or models (Section 50)."""
        rec = FalseNegativeRecord(
            fn_id=generate_ri_id("fn"),
            failure_id=failure_id,
            component=component,
            failure_description=failure_description,
            observable_precursor_present=observable_precursor_present,
            precursor_detected=precursor_detected,
            forecast_attempted=forecast_attempted,
            root_cause_of_miss=root_cause_of_miss,
            remediation_note=remediation_note,
        )
        self._false_negatives.append(rec)
        logger.warning("CRITICAL: Recorded False Negative missed failure on %s (%s)", component, root_cause_of_miss)
        return rec

    def record_strategy_execution(
        self,
        strategy: PreventionActionType,
        success: bool,
        duration_seconds: float = 1.0,
        resource_cost: Optional[Dict[str, float]] = None,
        side_effects: bool = False,
    ) -> PreventionStrategyScorecard:
        """Updates per-strategy effectiveness metrics and monitors degradation (Section 52)."""
        card = self._scorecards[strategy]
        card.total_attempts += 1
        if success:
            card.successes += 1
        else:
            card.failures += 1

        if side_effects:
            card.side_effects_detected += 1

        card.verification_rate = round(card.successes / card.total_attempts, 4)
        card.average_duration_seconds = round(
            (card.average_duration_seconds * (card.total_attempts - 1) + duration_seconds) / card.total_attempts, 2
        )
        if resource_cost:
            card.average_resource_cost.update(resource_cost)

        # Check for degradation (< 80% SLA threshold)
        if card.total_attempts >= 3 and card.verification_rate < 0.80:
            card.health_status = "DEGRADED"
        else:
            card.health_status = "HEALTHY"

        return card

    def get_scorecards(self) -> List[PreventionStrategyScorecard]:
        return list(self._scorecards.values())

    def get_calibration_metrics(self) -> Dict[str, Any]:
        """Calculates macro metrics: Brier score, FP rate, FN count, and strategy health."""
        n_calib = len(self._calibrations)
        if n_calib == 0:
            return {
                "total_evaluations": 0,
                "brier_score": 0.0,
                "false_positives_count": len(self._false_positives),
                "false_negatives_count": len(self._false_negatives),
                "degraded_strategies": [],
            }

        brier = sum((c.predicted_confidence - c.actual_correctness) ** 2 for c in self._calibrations) / n_calib
        degraded = [c.strategy.value for c in self._scorecards.values() if c.health_status == "DEGRADED"]

        return {
            "total_evaluations": n_calib,
            "brier_score": round(brier, 4),
            "false_positives_count": len(self._false_positives),
            "false_negatives_count": len(self._false_negatives),
            "degraded_strategies": degraded,
        }


_global_calibration_manager: Optional[CalibrationManager] = None


def get_calibration_manager() -> CalibrationManager:
    global _global_calibration_manager
    if _global_calibration_manager is None:
        _global_calibration_manager = CalibrationManager()
    return _global_calibration_manager
