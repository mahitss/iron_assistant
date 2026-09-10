"""Metrics collection, percentiles aggregation, and freshness evaluation (Task 62)."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone

from app.optimization.schemas import (
    MetricAggregation,
    MetricDefinition,
    MetricMeasurement,
    ObjectiveDirection,
)

logger = logging.getLogger(__name__)


class MetricsEngine:
    """Collects measurements, computes statistical percentiles, and enforces data sufficiency thresholds."""

    def __init__(self, max_history_per_metric: int = 500) -> None:
        self._max_history = max_history_per_metric
        self._measurements: dict[str, list[MetricMeasurement]] = defaultdict(list)
        self._definitions: dict[str, MetricDefinition] = {}
        self._register_default_definitions()

    def _register_default_definitions(self) -> None:
        """Register canonical system metrics with target directions and sample requirements."""
        defaults = [
            MetricDefinition(
                metric_name="latency_ms",
                description="End-to-end request latency in milliseconds",
                unit="ms",
                direction=ObjectiveDirection.MINIMIZE,
                min_samples_required=5,
                target_value=300.0,
                sla_threshold=1000.0,
            ),
            MetricDefinition(
                metric_name="cost_usd",
                description="Hourly inference and resource consumption cost in USD",
                unit="USD",
                direction=ObjectiveDirection.MINIMIZE,
                min_samples_required=3,
                target_value=5.0,
                sla_threshold=20.0,
            ),
            MetricDefinition(
                metric_name="error_rate",
                description="Ratio of failed operations to total operations (0.0 - 1.0)",
                unit="ratio",
                direction=ObjectiveDirection.MINIMIZE,
                min_samples_required=5,
                target_value=0.01,
                sla_threshold=0.05,
            ),
            MetricDefinition(
                metric_name="throughput_rps",
                description="Requests handled per second",
                unit="rps",
                direction=ObjectiveDirection.MAXIMIZE,
                min_samples_required=5,
                target_value=100.0,
                sla_threshold=20.0,
            ),
            MetricDefinition(
                metric_name="verification_success_rate",
                description="Ratio of passed post-action verifications (0.0 - 1.0)",
                unit="ratio",
                direction=ObjectiveDirection.MAXIMIZE,
                min_samples_required=5,
                target_value=0.99,
                sla_threshold=0.90,
            ),
            MetricDefinition(
                metric_name="recovery_time_s",
                description="Time required to verify complete recovery after an incident in seconds",
                unit="s",
                direction=ObjectiveDirection.MINIMIZE,
                min_samples_required=3,
                target_value=60.0,
                sla_threshold=300.0,
            ),
        ]
        for d in defaults:
            self._definitions[d.metric_name] = d

    def record_measurement(self, measurement: MetricMeasurement) -> None:
        """Record an incoming raw measurement with provenance."""
        name = measurement.metric_name
        history = self._measurements[name]
        history.append(measurement)
        if len(history) > self._max_history:
            self._measurements[name] = history[-self._max_history :]

    def get_definition(self, metric_name: str) -> MetricDefinition | None:
        """Retrieve metric definition by name."""
        return self._definitions.get(metric_name)

    def aggregate_metric(self, metric_name: str) -> MetricAggregation:
        """Compute statistical aggregation (mean, min, max, p50, p95, p99) and evaluate sufficiency."""
        history = self._measurements.get(metric_name, [])
        sample_count = len(history)
        defn = self._definitions.get(metric_name)
        min_required = defn.min_samples_required if defn else 5

        if sample_count == 0:
            return MetricAggregation(
                metric_name=metric_name,
                sample_count=0,
                mean=0.0,
                min_value=0.0,
                max_value=0.0,
                p50=0.0,
                p95=0.0,
                p99=0.0,
                has_sufficient_data=False,
                freshness_seconds=999999.0,
            )

        values = sorted(m.value for m in history)
        mean_val = sum(values) / sample_count
        now = datetime.now(timezone.utc)
        latest_ts = max(m.timestamp for m in history)
        freshness = max(0.0, (now - latest_ts).total_seconds())

        p50 = self._percentile(values, 0.50)
        p95 = self._percentile(values, 0.95)
        p99 = self._percentile(values, 0.99)

        return MetricAggregation(
            metric_name=metric_name,
            sample_count=sample_count,
            mean=round(mean_val, 4),
            min_value=round(values[0], 4),
            max_value=round(values[-1], 4),
            p50=round(p50, 4),
            p95=round(p95, 4),
            p99=round(p99, 4),
            has_sufficient_data=sample_count >= min_required,
            freshness_seconds=round(freshness, 2),
        )

    def aggregate_all(self) -> list[MetricAggregation]:
        """Compute statistical summaries for all tracked metrics."""
        return [self.aggregate_metric(name) for name in self._definitions]

    def _percentile(self, sorted_vals: list[float], pct: float) -> float:
        """Compute nearest-rank percentile from sorted list."""
        if not sorted_vals:
            return 0.0
        k = (len(sorted_vals) - 1) * pct
        f = int(k)
        c = min(f + 1, len(sorted_vals) - 1)
        d = k - f
        return sorted_vals[f] + d * (sorted_vals[c] - sorted_vals[f])


metrics_engine = MetricsEngine()
