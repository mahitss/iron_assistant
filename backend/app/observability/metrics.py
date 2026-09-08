"""Prometheus-compatible application metrics collector."""

import threading
from collections import defaultdict


class MetricsCollector:
    """Thread-safe collector for application metrics and Prometheus text generation."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, float] = defaultdict(float)
        self._latencies: dict[str, list[float]] = defaultdict(list)

    def inc_counter(self, name: str, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        """Increment a metric counter with labels."""
        label_str = self._format_labels(labels)
        metric_key = f"{name}{{{label_str}}}" if label_str else name
        with self._lock:
            self._counters[metric_key] += value

    def record_latency(
        self, name: str, duration_seconds: float, labels: dict[str, str] | None = None
    ) -> None:
        """Record an operation latency measurement."""
        label_str = self._format_labels(labels)
        metric_key = f"{name}{{{label_str}}}" if label_str else name
        with self._lock:
            self._latencies[metric_key].append(duration_seconds)
            # Bound memory: keep last 1000 measurements per metric
            if len(self._latencies[metric_key]) > 1000:
                self._latencies[metric_key] = self._latencies[metric_key][-500:]

    def _format_labels(self, labels: dict[str, str] | None) -> str:
        if not labels:
            return ""
        return ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))

    def generate_prometheus_text(self) -> str:
        """Generate Prometheus exposition text format."""
        lines: list[str] = []
        with self._lock:
            for key, val in sorted(self._counters.items()):
                lines.append(f"{key} {val}")

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
        """Reset metrics (used in tests)."""
        with self._lock:
            self._counters.clear()
            self._latencies.clear()


_METRICS_COLLECTOR: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    """Return singleton MetricsCollector."""
    global _METRICS_COLLECTOR
    if _METRICS_COLLECTOR is None:
        _METRICS_COLLECTOR = MetricsCollector()
    return _METRICS_COLLECTOR
