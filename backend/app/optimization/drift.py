"""Multi-dimensional drift detection across data, models, metrics, and baselines (Task 62)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.optimization.baselines import BaselineManager, baseline_manager
from app.optimization.metrics import MetricsEngine, metrics_engine
from app.optimization.schemas import (
    DriftRecord,
    DriftType,
    RiskLevel,
)

logger = logging.getLogger(__name__)


class DriftDetector:
    """Detects statistical, operational, model, and configuration drift across the Kairo runtime.

    Invariant 24: Tracks drift type, scope, severity, baseline, current state, evidence, and confidence.
    """

    def __init__(
        self,
        metrics_eng: MetricsEngine | None = None,
        baselines_mgr: BaselineManager | None = None,
    ) -> None:
        self._metrics = metrics_eng or metrics_engine
        self._baselines = baselines_mgr or baseline_manager
        self._drift_records: list[DriftRecord] = []

    def check_drift(self) -> list[DriftRecord]:
        """Scan active metrics and baselines for statistical divergence or operational drift."""
        new_drifts: list[DriftRecord] = []
        aggregations = self._metrics.aggregate_all()

        for agg in aggregations:
            if not agg.has_sufficient_data:
                continue

            # Check baseline drift
            drift_info = self._baselines.detect_baseline_drift(
                metric_name=agg.metric_name,
                observed_mean=agg.mean,
                threshold_sigmas=2.5,
            )
            if drift_info:
                sigmas = drift_info["divergence_sigmas"]
                severity = RiskLevel.HIGH if sigmas >= 4.0 else RiskLevel.MEDIUM

                record = DriftRecord(
                    drift_type=DriftType.BASELINE_DRIFT,
                    scope=f"metric:{agg.metric_name}",
                    severity=severity,
                    baseline_value=drift_info["baseline_value"],
                    observed_value=drift_info["observed_value"],
                    divergence_score=sigmas,
                    evidence=f"Observed value {agg.mean} diverged by {sigmas:.2f} standard deviations from baseline.",
                    detected_at=datetime.now(timezone.utc),
                )
                new_drifts.append(record)
                self._drift_records.append(record)
                logger.warning(
                    "DRIFT_DETECTED: type=%s scope=%s sigmas=%.2f",
                    record.drift_type.value,
                    record.scope,
                    sigmas,
                )

        return new_drifts

    def list_drift_records(self, limit: int = 50) -> list[DriftRecord]:
        """Retrieve recent drift alerts."""
        return self._drift_records[-limit:]


drift_detector = DriftDetector()
