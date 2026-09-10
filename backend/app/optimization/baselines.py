"""Baseline management, versioning, and incident anti-poisoning quarantine (Task 62)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.optimization.schemas import OptimizationBaseline

logger = logging.getLogger(__name__)


class BaselineManager:
    """Maintains versioned reference baselines with incident anti-poisoning quarantine safeguards.

    Invariant 10: A baseline must never silently change simply because a metric temporarily spiked
    or degraded during an incident or anomaly.
    """

    def __init__(self) -> None:
        self._baselines: dict[str, OptimizationBaseline] = {}
        self._initialize_default_baselines()

    def _initialize_default_baselines(self) -> None:
        """Seed initial healthy operational baselines for core metrics."""
        defaults = [
            OptimizationBaseline(
                baseline_id="bsl_latency_prod",
                metric_name="latency_ms",
                baseline_value=450.0,
                std_dev=35.0,
                sample_size=100,
                version=1,
                environment="production",
            ),
            OptimizationBaseline(
                baseline_id="bsl_cost_prod",
                metric_name="cost_usd",
                baseline_value=8.5,
                std_dev=1.2,
                sample_size=100,
                version=1,
                environment="production",
            ),
            OptimizationBaseline(
                baseline_id="bsl_error_prod",
                metric_name="error_rate",
                baseline_value=0.008,
                std_dev=0.002,
                sample_size=100,
                version=1,
                environment="production",
            ),
            OptimizationBaseline(
                baseline_id="bsl_throughput_prod",
                metric_name="throughput_rps",
                baseline_value=85.0,
                std_dev=12.0,
                sample_size=100,
                version=1,
                environment="production",
            ),
            OptimizationBaseline(
                baseline_id="bsl_verif_prod",
                metric_name="verification_success_rate",
                baseline_value=0.995,
                std_dev=0.003,
                sample_size=100,
                version=1,
                environment="production",
            ),
        ]
        for b in defaults:
            self._baselines[b.metric_name] = b

    def get_baseline(self, metric_name: str) -> OptimizationBaseline | None:
        """Retrieve current baseline for a metric."""
        return self._baselines.get(metric_name)

    def list_baselines(self) -> list[OptimizationBaseline]:
        """List all active baselines."""
        return list(self._baselines.values())

    def update_baseline(
        self,
        metric_name: str,
        new_mean: float,
        std_dev: float,
        sample_count: int,
        is_incident_active: bool = False,
    ) -> OptimizationBaseline:
        """Update baseline using verified non-incident data, enforcing anti-poisoning quarantine."""
        current = self._baselines.get(metric_name)
        now = datetime.now(timezone.utc)

        # Anti-poisoning defense: if an incident is active, quarantine incoming values
        if is_incident_active:
            logger.warning(
                "BASELINE_ANTI_POISONING: Metric '%s' update quarantined due to active incident.",
                metric_name,
            )
            if current:
                current.is_quarantined = True
                current.updated_at = now
                return current
            quarantined = OptimizationBaseline(
                baseline_id=f"bsl_{metric_name}_quarantine",
                metric_name=metric_name,
                baseline_value=new_mean,
                std_dev=std_dev,
                sample_size=sample_count,
                version=1,
                is_quarantined=True,
                created_at=now,
                updated_at=now,
            )
            self._baselines[metric_name] = quarantined
            return quarantined

        # Normal versioned update
        new_version = (current.version + 1) if current else 1
        updated = OptimizationBaseline(
            baseline_id=f"bsl_{metric_name}_v{new_version}",
            metric_name=metric_name,
            baseline_value=round(new_mean, 4),
            std_dev=round(std_dev, 4),
            sample_size=sample_count,
            version=new_version,
            is_quarantined=False,
            created_at=current.created_at if current else now,
            updated_at=now,
        )
        self._baselines[metric_name] = updated
        logger.info(
            "BASELINE_UPDATED: metric=%s v%d value=%.4f (samples=%d)",
            metric_name,
            new_version,
            new_mean,
            sample_count,
        )
        return updated

    def detect_baseline_drift(
        self,
        metric_name: str,
        observed_mean: float,
        threshold_sigmas: float = 2.5,
    ) -> dict[str, Any] | None:
        """Check if observed value has statistically drifted from the established baseline."""
        baseline = self._baselines.get(metric_name)
        if not baseline or baseline.is_quarantined or baseline.std_dev <= 0:
            return None

        diff = abs(observed_mean - baseline.baseline_value)
        sigmas = diff / baseline.std_dev

        if sigmas >= threshold_sigmas:
            return {
                "metric_name": metric_name,
                "baseline_value": baseline.baseline_value,
                "observed_value": observed_mean,
                "divergence_sigmas": round(sigmas, 2),
                "is_drift_detected": True,
            }
        return None


baseline_manager = BaselineManager()
