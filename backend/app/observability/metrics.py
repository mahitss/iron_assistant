"""Prometheus-compatible metrics engine with bounded cardinality defense (Task 38)."""

import threading
from collections import defaultdict
from typing import Any

# Default latency buckets in seconds (0.005s to 60s)
DEFAULT_HISTOGRAM_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0)

# Maximum allowed distinct label combinations per metric family to defend against cardinality explosion
MAX_CARDINALITY_PER_METRIC = 500


class MetricsCollector:
    """Thread-safe collector for counters, gauges, histograms, and Prometheus text generation."""

    def __init__(self, max_cardinality: int = MAX_CARDINALITY_PER_METRIC) -> None:
        self._lock = threading.Lock()
        self.max_cardinality = max_cardinality
        self._counters: dict[str, float] = defaultdict(float)
        self._gauges: dict[str, float] = {}
        self._latencies: dict[str, list[float]] = defaultdict(list)
        self._histograms: dict[str, dict[str, Any]] = {}
        self._metric_cardinality: dict[str, set[str]] = defaultdict(set)

    def _sanitize_labels(self, metric_base: str, labels: dict[str, str] | None) -> str:
        """Sanitizes labels and bounds cardinality to prevent memory bloat."""
        if not labels:
            return ""

        # Scrub potentially unbounded or sensitive labels
        clean_labels: dict[str, str] = {}
        for k, v in sorted(labels.items()):
            k_clean = str(k).strip()[:32]
            # Truncate label values and strip injection chars
            v_clean = str(v).replace('"', '\\"').replace("\n", "").strip()[:64]
            clean_labels[k_clean] = v_clean

        label_str = ",".join(f'{k}="{v}"' for k, v in clean_labels.items())

        # Check cardinality limit
        cardinality_set = self._metric_cardinality[metric_base]
        if label_str not in cardinality_set:
            if len(cardinality_set) >= self.max_cardinality:
                # Fallback to generic overflow bucket to prevent memory leak
                return 'overflow="true"'
            cardinality_set.add(label_str)

        return label_str

    def inc_counter(self, name: str, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        """Increment a metric counter."""
        base_name = name.split("{")[0]
        label_str = self._sanitize_labels(base_name, labels)
        metric_key = f"{base_name}{{{label_str}}}" if label_str else base_name
        with self._lock:
            self._counters[metric_key] += value

    def set_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Set an instantaneous gauge metric value."""
        base_name = name.split("{")[0]
        label_str = self._sanitize_labels(base_name, labels)
        metric_key = f"{base_name}{{{label_str}}}" if label_str else base_name
        with self._lock:
            self._gauges[metric_key] = value

    def record_latency(
        self, name: str, duration_seconds: float, labels: dict[str, str] | None = None
    ) -> None:
        """Record an operation latency measurement."""
        base_name = name.split("{")[0]
        label_str = self._sanitize_labels(base_name, labels)
        metric_key = f"{base_name}{{{label_str}}}" if label_str else base_name
        with self._lock:
            self._latencies[metric_key].append(duration_seconds)
            # Bound in-memory sample size (keep last 1000 measurements)
            if len(self._latencies[metric_key]) > 1000:
                self._latencies[metric_key] = self._latencies[metric_key][-500:]

    def generate_prometheus_text(self) -> str:
        """Generate standard Prometheus exposition text format."""
        lines: list[str] = []
        with self._lock:
            # 1. Counters
            for key, val in sorted(self._counters.items()):
                lines.append(f"{key} {val}")

            # 2. Gauges
            for key, val in sorted(self._gauges.items()):
                lines.append(f"{key} {val}")

            # 3. Latencies / Summaries
            for key, samples in sorted(self._latencies.items()):
                if samples:
                    count = len(samples)
                    total = sum(samples)
                    avg = total / count
                    base_name = key.split("{")[0]
                    labels = "{" + key.split("{")[1] if "{" in key else ""
                    lines.append(f"{base_name}_count{labels} {count}")
                    lines.append(f"{base_name}_sum{labels} {total:.4f}")
                    lines.append(f"{base_name}_avg{labels} {avg:.4f}")

        return "\n".join(lines) + "\n"

    def clear(self) -> None:
        """Reset all metrics (used in test suites)."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._latencies.clear()
            self._histograms.clear()
            self._metric_cardinality.clear()


_METRICS_COLLECTOR: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    """Return global singleton MetricsCollector."""
    global _METRICS_COLLECTOR
    if _METRICS_COLLECTOR is None:
        _METRICS_COLLECTOR = MetricsCollector()
    return _METRICS_COLLECTOR
