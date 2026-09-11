"""Confidence Calibration, Prediction Audit, and Brier Score Computation (Task 67)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.self_audit.schemas import (
    ConfidenceCalibrationState,
    PredictionCalibrationRecord,
)

logger = logging.getLogger("kairo.self_audit.calibration")


class CalibrationEngine:
    """Evaluates whether reported confidence matches empirical reality (Spec 15, 24, 25, 26)."""

    def __init__(self) -> None:
        self._predictions: dict[str, PredictionCalibrationRecord] = {}

    def record_prediction(
        self,
        subject: str,
        prediction: str,
        confidence: float,
        expected_outcome: str,
    ) -> PredictionCalibrationRecord:
        """Register a tracked prediction with reported confidence (Spec 15)."""
        pred_id = f"prd_{uuid.uuid4().hex[:8]}"
        record = PredictionCalibrationRecord(
            prediction_id=pred_id,
            subject=subject,
            prediction=prediction,
            confidence=max(0.0, min(1.0, confidence)),
            expected_outcome=expected_outcome,
            actual_outcome=None,
            outcome_verified=False,
            brier_score=None,
            calibration_state=ConfidenceCalibrationState.UNKNOWN,
        )
        self._predictions[pred_id] = record
        return record

    def record_actual_outcome(
        self,
        prediction_id: str,
        actual_outcome: str,
        success: bool,
    ) -> PredictionCalibrationRecord:
        """Record empirical outcome and compute individual Brier score."""
        record = self._predictions.get(prediction_id)
        if not record:
            raise KeyError(f"Prediction '{prediction_id}' not found.")

        record.actual_outcome = actual_outcome
        record.outcome_verified = True

        outcome_val = 1.0 if success else 0.0
        # Brier Score = (confidence - outcome)^2
        record.brier_score = round((record.confidence - outcome_val) ** 2, 4)

        if record.confidence >= 0.75 and not success:
            record.calibration_state = ConfidenceCalibrationState.OVERCONFIDENT
        elif record.confidence <= 0.35 and success:
            record.calibration_state = ConfidenceCalibrationState.UNDERCONFIDENT
        else:
            record.calibration_state = ConfidenceCalibrationState.WELL_CALIBRATED

        logger.info(
            "PREDICTION_RESOLVED: id=%s confidence=%.2f success=%s brier=%.4f state=%s",
            prediction_id,
            record.confidence,
            success,
            record.brier_score,
            record.calibration_state.value,
        )
        return record

    def compute_aggregate_calibration(self) -> dict[str, Any]:
        """Compute aggregate Brier score, calibration state, and systematic bias alerts (Spec 24, 25, 26)."""
        verified = [p for p in self._predictions.values() if p.outcome_verified and p.brier_score is not None]
        if len(verified) < 3:
            return {
                "sample_size": len(verified),
                "calibration_state": ConfidenceCalibrationState.UNKNOWN.value,
                "mean_brier_score": 0.0,
                "alerts": [],
                "buckets": {},
            }

        mean_brier = round(sum(p.brier_score for p in verified) / len(verified), 4)

        overconfident_count = sum(
            1 for p in verified if p.calibration_state == ConfidenceCalibrationState.OVERCONFIDENT
        )
        underconfident_count = sum(
            1 for p in verified if p.calibration_state == ConfidenceCalibrationState.UNDERCONFIDENT
        )

        alerts: list[str] = []
        overall_state = ConfidenceCalibrationState.WELL_CALIBRATED

        # Systematic Overconfidence Guard (Spec 25)
        if (overconfident_count / len(verified)) > 0.35:
            overall_state = ConfidenceCalibrationState.OVERCONFIDENT
            alerts.append(
                "SYSTEMATIC_OVERCONFIDENCE: Kairo repeatedly reports high confidence on failing outcomes."
            )
        # Systematic Underconfidence Guard (Spec 26)
        elif (underconfident_count / len(verified)) > 0.40:
            overall_state = ConfidenceCalibrationState.UNDERCONFIDENT
            alerts.append(
                "SYSTEMATIC_UNDERCONFIDENCE: Kairo repeatedly reports low confidence on successful outcomes."
            )

        # 3 calibration buckets: Low (0.0-0.33), Med (0.34-0.66), High (0.67-1.0)
        buckets = {
            "low_confidence": {
                "count": sum(1 for p in verified if p.confidence <= 0.33),
                "avg_brier": round(
                    sum(p.brier_score for p in verified if p.confidence <= 0.33)
                    / max(1, sum(1 for p in verified if p.confidence <= 0.33)),
                    3,
                ),
            },
            "medium_confidence": {
                "count": sum(1 for p in verified if 0.33 < p.confidence <= 0.66),
                "avg_brier": round(
                    sum(p.brier_score for p in verified if 0.33 < p.confidence <= 0.66)
                    / max(1, sum(1 for p in verified if 0.33 < p.confidence <= 0.66)),
                    3,
                ),
            },
            "high_confidence": {
                "count": sum(1 for p in verified if p.confidence > 0.66),
                "avg_brier": round(
                    sum(p.brier_score for p in verified if p.confidence > 0.66)
                    / max(1, sum(1 for p in verified if p.confidence > 0.66)),
                    3,
                ),
            },
        }

        return {
            "sample_size": len(verified),
            "calibration_state": overall_state.value,
            "mean_brier_score": mean_brier,
            "overconfident_ratio": round(overconfident_count / len(verified), 2),
            "underconfident_ratio": round(underconfident_count / len(verified), 2),
            "alerts": alerts,
            "buckets": buckets,
        }

    def list_predictions(self) -> list[PredictionCalibrationRecord]:
        return list(self._predictions.values())
