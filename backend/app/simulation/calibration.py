"""Simulation calibration engine, error tracking, bias detection, and drift monitoring."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel

from app.simulation.schemas import CalibrationMetric


class CalibrationReport(BaseModel):
    """Aggregated model accuracy and drift diagnostics."""

    metric_name: str
    sample_count: int
    mean_absolute_error: float
    mean_bias: float  # Positive = systematically over-predicts, Negative = under-predicts
    is_biased: bool
    drift_detected: bool
    diagnostics: str


class SimulationCalibrator:
    """Tracks simulation vs reality accuracy and calculates systematic error and drift."""

    def __init__(self, drift_mae_threshold: float = 20.0, bias_threshold: float = 5.0) -> None:
        self.drift_mae_threshold = drift_mae_threshold
        self.bias_threshold = bias_threshold
        self._history: list[CalibrationMetric] = []

    def record_outcome_pair(
        self,
        simulation_id: str,
        metric_name: str,
        predicted: float,
        actual_observed: float,
    ) -> CalibrationMetric:
        """Records a post-execution reality verification comparison.

        Enforces: Only real observed data can validate predictions (Prompt #145).
        """
        err = round(abs(predicted - actual_observed), 3)
        bias = round(predicted - actual_observed, 3)

        metric = CalibrationMetric(
            calibration_id=f"cal_{uuid.uuid4().hex[:12]}",
            simulation_id=simulation_id,
            metric_name=metric_name,
            predicted_value=predicted,
            actual_value=actual_observed,
            error=err,
            bias=bias,
            calibrated_at=datetime.now(timezone.utc),
        )
        self._history.append(metric)
        return metric

    def evaluate_model_calibration(self, metric_name: str) -> CalibrationReport:
        """Evaluates MAE, bias, and drift for a specific metric across tracked history."""
        samples = [m for m in self._history if m.metric_name == metric_name]
        if not samples:
            return CalibrationReport(
                metric_name=metric_name,
                sample_count=0,
                mean_absolute_error=0.0,
                mean_bias=0.0,
                is_biased=False,
                drift_detected=False,
                diagnostics="No calibration samples available yet.",
            )

        n = len(samples)
        mae = round(sum(m.error for m in samples) / n, 3)
        mean_bias = round(sum(m.bias for m in samples) / n, 3)

        is_biased = abs(mean_bias) > self.bias_threshold
        drift_detected = mae > self.drift_mae_threshold

        diag_parts = []
        if is_biased:
            direction = "over-predicts" if mean_bias > 0 else "under-predicts"
            diag_parts.append(f"Systematic bias detected: model {direction} by {abs(mean_bias):.2f}.")
        if drift_detected:
            diag_parts.append(f"Model accuracy drift detected: MAE ({mae:.2f}) exceeds threshold ({self.drift_mae_threshold}).")

        if not diag_parts:
            diag_parts.append("Model is well-calibrated within tolerance limits.")

        return CalibrationReport(
            metric_name=metric_name,
            sample_count=n,
            mean_absolute_error=mae,
            mean_bias=mean_bias,
            is_biased=is_biased,
            drift_detected=drift_detected,
            diagnostics=" ".join(diag_parts),
        )

    def get_history(self) -> list[CalibrationMetric]:
        return list(self._history)


calibrator = SimulationCalibrator()
