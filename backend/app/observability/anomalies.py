"""Baseline-driven anomaly detector for latency spikes, error surges, and storms (Task 38)."""

import uuid
from datetime import UTC, datetime
from typing import Any

from app.observability.schemas import AnomalyReport, IncidentSeverity


class AnomalyDetector:
    """Detects operational deviations against historical baselines without executing remediation."""

    def __init__(
        self,
        latency_spike_multiplier: float = 2.5,
        min_latency_threshold_ms: float = 200.0,
        error_rate_threshold: float = 0.05,
    ) -> None:
        self.latency_spike_multiplier = latency_spike_multiplier
        self.min_latency_threshold_ms = min_latency_threshold_ms
        self.error_rate_threshold = error_rate_threshold
        # Baseline store: component -> {metric -> baseline_value}
        self._baselines: dict[str, dict[str, float]] = {
            "api": {"latency_ms": 45.0, "error_rate": 0.01},
            "task_engine": {"latency_ms": 120.0, "error_rate": 0.02},
            "model_router": {"latency_ms": 800.0, "error_rate": 0.03},
            "tool": {"latency_ms": 150.0, "error_rate": 0.02},
            "github": {"latency_ms": 250.0, "error_rate": 0.01},
            "database": {"latency_ms": 5.0, "error_rate": 0.001},
        }

    def evaluate_latency(self, component: str, current_latency_ms: float) -> AnomalyReport | None:
        """Evaluates whether current latency represents an anomalous spike."""
        baseline = self._baselines.get(component, {}).get("latency_ms", 100.0)
        if current_latency_ms > self.min_latency_threshold_ms and current_latency_ms >= baseline * self.latency_spike_multiplier:
            deviation = round(current_latency_ms / baseline, 2)
            severity = IncidentSeverity.CRITICAL if deviation >= 5.0 else IncidentSeverity.HIGH
            return AnomalyReport(
                anomaly_id=f"anom_{uuid.uuid4().hex[:12]}",
                metric_name="latency_ms",
                component=component,
                current_value=current_latency_ms,
                baseline_value=baseline,
                deviation_factor=deviation,
                severity=severity,
                evidence=f"{component} latency spiked to {current_latency_ms:.1f}ms (baseline: {baseline:.1f}ms, factor: {deviation}x)",
            )
        return None

    def evaluate_error_rate(self, component: str, current_error_rate: float) -> AnomalyReport | None:
        """Evaluates whether current error rate represents an anomalous surge."""
        baseline = self._baselines.get(component, {}).get("error_rate", 0.01)
        if current_error_rate >= self.error_rate_threshold and current_error_rate >= baseline * 3.0:
            deviation = round(current_error_rate / max(baseline, 0.001), 2)
            severity = IncidentSeverity.CRITICAL if current_error_rate >= 0.25 else IncidentSeverity.HIGH
            return AnomalyReport(
                anomaly_id=f"anom_{uuid.uuid4().hex[:12]}",
                metric_name="error_rate",
                component=component,
                current_value=current_error_rate,
                baseline_value=baseline,
                deviation_factor=deviation,
                severity=severity,
                evidence=f"{component} error rate surged to {current_error_rate*100:.1f}% (baseline: {baseline*100:.1f}%, factor: {deviation}x)",
            )
        return None
