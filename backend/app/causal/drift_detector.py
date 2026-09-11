"""Causal drift and world-model drift detection engine (Task 73, Spec 47, 48, 49).

Detects:
1. Causal drift: when an established causal relationship's empirical effect changes.
2. World-model drift: when predictions derived from the causal model degrade.
3. Prediction-error feedback: triggers model reassessment when prediction error exceeds threshold.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.causal.discovery_schemas import (
    CausalDriftReport,
    CausalRelationship,
)

logger = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class CausalDriftDetector:
    """Detects behavioral drift and prediction errors in causal relationships and the world model."""

    def __init__(self, prediction_error_threshold: float = 0.25) -> None:
        self.prediction_error_threshold = prediction_error_threshold
        self._drift_reports: list[CausalDriftReport] = []

    def evaluate_relationship_drift(
        self,
        relationship: CausalRelationship,
        new_observations: list[dict[str, Any]],
        observed_effect_magnitude: float,
        environment: str = "STAGING",
        software_version: str | None = None,
    ) -> CausalDriftReport | None:
        """Check if an established relationship behaves differently in a new environment/version."""
        expected_mag = 1.0
        if relationship.effect_size:
            expected_mag = relationship.effect_size.measurement
        elif relationship.strength.value == "STRONG":
            expected_mag = 1.0
        elif relationship.strength.value == "MODERATE":
            expected_mag = 0.5
        elif relationship.strength.value == "WEAK":
            expected_mag = 0.2
        else:
            expected_mag = 0.05

        # Compute divergence
        error = abs(expected_mag - observed_effect_magnitude) / max(0.1, abs(expected_mag))

        # Check if environment differs from original
        env_shift = environment != relationship.environment
        version_shift = software_version and software_version != relationship.software_version

        if error >= self.prediction_error_threshold or (env_shift and error >= 0.2):
            drift_type = "CAUSAL_DRIFT"
            rec_action = (
                f"Relationship {relationship.causal_relation_id} effect magnitude shifted from "
                f"{expected_mag:.2f} to {observed_effect_magnitude:.2f} (error: {error:.1%}). "
            )
            if env_shift:
                rec_action += f"Context shift: {relationship.environment} -> {environment}. Mark CONTEXTUAL or update scope."
            elif version_shift:
                rec_action += f"Version shift: {relationship.software_version} -> {software_version}. Create version-scoped model."
            else:
                rec_action += "Model reassessment or discriminating experiment recommended."

            report = CausalDriftReport(
                drift_type=drift_type,
                relation_id=relationship.causal_relation_id,
                environment=environment,
                software_version=software_version or relationship.software_version,
                expected_behavior={"expected_effect_magnitude": expected_mag},
                observed_behavior={"observed_effect_magnitude": observed_effect_magnitude},
                prediction_error=round(error, 3),
                status="DETECTED",
                recommended_action=rec_action,
                timestamp=_now_utc(),
            )
            self._drift_reports.append(report)
            return report

        return None

    def evaluate_prediction_feedback(
        self,
        relationship: CausalRelationship,
        predicted_effect: dict[str, Any],
        actual_effect: dict[str, Any],
        metric_key: str = "delta",
    ) -> tuple[float, bool, CausalDriftReport | None]:
        """Compare predicted outcome with actual observation. If error is large, flag drift."""
        pred_val = float(predicted_effect.get(metric_key, 0.0))
        act_val = float(actual_effect.get(metric_key, 0.0))

        denominator = max(0.1, abs(pred_val))
        error = abs(pred_val - act_val) / denominator
        exceeds_threshold = error >= self.prediction_error_threshold

        drift_report = None
        if exceeds_threshold:
            report = CausalDriftReport(
                drift_type="WORLD_MODEL_DRIFT",
                relation_id=relationship.causal_relation_id,
                environment=relationship.environment,
                software_version=relationship.software_version,
                expected_behavior=predicted_effect,
                observed_behavior=actual_effect,
                prediction_error=round(error, 3),
                status="DETECTED",
                recommended_action=(
                    f"Prediction error {error:.1%} exceeds threshold {self.prediction_error_threshold:.1%}. "
                    f"Triggering causal model review and active experiment generation."
                ),
                timestamp=_now_utc(),
            )
            self._drift_reports.append(report)
            drift_report = report

        return round(error, 3), exceeds_threshold, drift_report

    def get_drift_reports(self, relation_id: str | None = None) -> list[CausalDriftReport]:
        """Retrieve all recorded drift reports."""
        if relation_id:
            return [r for r in self._drift_reports if r.relation_id == relation_id]
        return list(self._drift_reports)
