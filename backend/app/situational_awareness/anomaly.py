"""Anomaly detection, sigma deviation scoring, and independent signal corroboration (Task 60)."""

from __future__ import annotations

import logging
from typing import Any

from app.situational_awareness.baselines import BaselineEngine, baseline_engine
from app.situational_awareness.schemas import AnomalySignal, SituationSeverity

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Detects statistical metric anomalies, threshold breaches, and corroborates multi-source signals."""

    def __init__(self, baselines: BaselineEngine | None = None) -> None:
        self._baselines = baselines or baseline_engine

    def check_observation(
        self,
        signal_name: str,
        resource: str,
        observed_value: float,
        environment: str = "development",
        sigma_threshold: float = 3.0,
    ) -> AnomalySignal | None:
        """Check if an observed metric deviates significantly from calibrated baseline."""
        baseline = self._baselines.get_baseline(signal_name, resource, environment)
        if not baseline or baseline.sample_count < 10:
            # Insufficient baseline data -> Conservative check using hard thresholds
            if observed_value > 90.0 and "percent" in signal_name:
                return AnomalySignal(
                    signal_name=signal_name,
                    resource=resource,
                    observed_value=observed_value,
                    baseline_mean=50.0,
                    deviation_sigmas=3.5,
                    confidence=0.75,
                )
            return None

        diff = observed_value - baseline.mean_val
        sigmas = diff / max(0.01, baseline.std_dev)

        if abs(sigmas) >= sigma_threshold:
            confidence = min(0.99, 0.70 + (abs(sigmas) - sigma_threshold) * 0.10)
            anomaly = AnomalySignal(
                signal_name=signal_name,
                resource=resource,
                observed_value=round(observed_value, 2),
                baseline_mean=baseline.mean_val,
                deviation_sigmas=round(sigmas, 2),
                confidence=round(confidence, 3),
            )
            logger.warning(
                "ANOMALY_DETECTED: %s on %s = %.2f (mean=%.2f, sigmas=%.2f, conf=%.2f)",
                signal_name,
                resource,
                observed_value,
                baseline.mean_val,
                sigmas,
                confidence,
            )
            return anomaly

        return None

    def corroborate_anomalies(
        self,
        anomalies: list[AnomalySignal],
    ) -> dict[str, Any]:
        """Corroborate multiple independent anomaly signals.

        Invariant 38: Combining independent signals increases confidence, but does not double-count identical sources.
        """
        if not anomalies:
            return {"is_corroborated": False, "confidence": 0.0, "severity": SituationSeverity.INFO}

        # Distinct resources and signal types
        distinct_signals = {a.signal_name for a in anomalies}
        distinct_resources = {a.resource for a in anomalies}

        base_conf = max(a.confidence for a in anomalies)
        # Independent signal boost
        boost = (len(distinct_signals) - 1) * 0.10
        total_conf = min(0.99, base_conf + boost)

        # Determine suggested severity
        max_sigmas = max(abs(a.deviation_sigmas) for a in anomalies)
        if len(distinct_signals) >= 2 and max_sigmas >= 4.0:
            severity = SituationSeverity.CRITICAL
        elif max_sigmas >= 3.5 or len(distinct_signals) >= 2:
            severity = SituationSeverity.HIGH
        elif max_sigmas >= 3.0:
            severity = SituationSeverity.MEDIUM
        else:
            severity = SituationSeverity.LOW

        return {
            "is_corroborated": len(distinct_signals) > 1,
            "distinct_signals_count": len(distinct_signals),
            "distinct_resources_count": len(distinct_resources),
            "confidence": round(total_conf, 3),
            "suggested_severity": severity,
        }


anomaly_detector = AnomalyDetector()
