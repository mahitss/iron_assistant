"""Calibration tracking comparing predicted vs actual optimization outcomes (Task 62)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.optimization.schemas import CalibrationRecord

logger = logging.getLogger(__name__)


class CalibrationTracker:
    """Tracks prediction accuracy and overconfidence across adaptive control recommendations.

    Invariant 25 & 26: Compares expected improvement vs actual verified improvement.
    Never rewrites history to make predictions appear accurate.
    """

    def __init__(self) -> None:
        self._records: list[CalibrationRecord] = []

    def record_calibration(
        self,
        recommendation_id: str,
        predicted_improvement_pct: float,
        actual_improvement_pct: float,
        confidence_score: float = 0.85,
    ) -> CalibrationRecord:
        """Record the delta between expected and real-world verified outcomes."""
        error = round(abs(predicted_improvement_pct - actual_improvement_pct), 4)
        is_overconfident = (predicted_improvement_pct - actual_improvement_pct) > 10.0

        rec = CalibrationRecord(
            recommendation_id=recommendation_id,
            predicted_improvement_pct=round(predicted_improvement_pct, 2),
            actual_improvement_pct=round(actual_improvement_pct, 2),
            prediction_error=error,
            confidence_score=confidence_score,
            is_overconfident=is_overconfident,
            recorded_at=datetime.now(timezone.utc),
        )
        self._records.append(rec)
        logger.info(
            "CALIBRATION_RECORDED: rec=%s predicted=%.1f%% actual=%.1f%% error=%.2f overconfident=%s",
            recommendation_id,
            predicted_improvement_pct,
            actual_improvement_pct,
            error,
            is_overconfident,
        )
        return rec

    def get_average_prediction_error(self) -> float:
        """Compute mean absolute prediction error across recorded calibration outcomes."""
        if not self._records:
            return 0.0
        total_err = sum(r.prediction_error for r in self._records)
        return round(total_err / len(self._records), 4)

    def list_calibration_records(self, limit: int = 50) -> list[CalibrationRecord]:
        """Retrieve historical calibration records."""
        return self._records[-limit:]


calibration_tracker = CalibrationTracker()
