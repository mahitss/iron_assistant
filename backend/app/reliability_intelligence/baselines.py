"""Component-aware baselines, trend detection, and rate-of-change engine for Task 90."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import math
from typing import Dict, List, Optional, Tuple

from app.reliability_intelligence.models import (
    MetricBaseline,
    MetricRateOfChange,
    TrendDirection,
    _now_utc,
)


class TelemetrySample:
    """Individual timestamped measurement."""

    __slots__ = ("timestamp", "value")

    def __init__(self, timestamp: datetime, value: float) -> None:
        self.timestamp = timestamp
        self.value = float(value)


class BaselineTracker:
    """Manages component-aware, bounded rolling telemetry buffers and computes baselines."""

    def __init__(self, max_samples_per_series: int = 120, default_window_seconds: float = 300.0) -> None:
        self.max_samples = max_samples_per_series
        self.default_window = default_window_seconds
        # Key: (component, metric_name) -> deque of TelemetrySample
        self._buffers: Dict[Tuple[str, str], deque[TelemetrySample]] = {}

    def record_sample(
        self,
        component: str,
        metric_name: str,
        value: float,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Appends a new observation into the bounded rolling buffer."""
        ts = timestamp or _now_utc()
        key = (component.lower(), metric_name.lower())
        if key not in self._buffers:
            self._buffers[key] = deque(maxlen=self.max_samples)
        self._buffers[key].append(TelemetrySample(ts, value))

    def get_baseline(
        self,
        component: str,
        metric_name: str,
        unit: str = "",
        window_seconds: Optional[float] = None,
    ) -> MetricBaseline:
        """Computes statistical baseline across active time window."""
        key = (component.lower(), metric_name.lower())
        buf = self._buffers.get(key)
        now = _now_utc()
        win = window_seconds or self.default_window

        if not buf:
            return MetricBaseline(
                component=component,
                metric_name=metric_name,
                baseline_value=0.0,
                unit=unit,
                sample_count=0,
                window_duration_seconds=win,
                freshness_seconds=0.0,
                confidence=0.1,
                stdev=0.0,
                min_value=0.0,
                max_value=0.0,
            )

        # Filter within window
        cutoff = now.timestamp() - win
        active_samples = [s.value for s in buf if s.timestamp.timestamp() >= cutoff]
        if not active_samples:
            active_samples = [s.value for s in buf]  # Fallback to whatever exists

        n = len(active_samples)
        mean_val = sum(active_samples) / n
        stdev_val = 0.0
        if n > 1:
            variance = sum((x - mean_val) ** 2 for x in active_samples) / (n - 1)
            stdev_val = math.sqrt(variance)

        latest_sample = buf[-1]
        freshness = max(0.0, now.timestamp() - latest_sample.timestamp.timestamp())
        # Confidence decays if few samples or stale
        sample_conf = min(1.0, n / 10.0)
        freshness_penalty = min(0.5, freshness / 60.0)
        confidence = max(0.2, sample_conf - freshness_penalty)

        return MetricBaseline(
            component=component,
            metric_name=metric_name,
            baseline_value=round(mean_val, 4),
            unit=unit,
            sample_count=n,
            window_duration_seconds=win,
            freshness_seconds=round(freshness, 2),
            confidence=round(confidence, 2),
            stdev=round(stdev_val, 4),
            min_value=round(min(active_samples), 4),
            max_value=round(max(active_samples), 4),
        )

    def detect_trend(
        self,
        component: str,
        metric_name: str,
        min_samples: int = 3,
    ) -> TrendDirection:
        """Empirically evaluates trend direction without claiming fake signals."""
        key = (component.lower(), metric_name.lower())
        buf = self._buffers.get(key)
        if not buf or len(buf) < min_samples:
            return TrendDirection.UNKNOWN

        sample_window = max(min_samples, min(len(buf), 10))
        vals = [s.value for s in list(buf)[-sample_window:]]
        deltas = [vals[i] - vals[i - 1] for i in range(1, len(vals))]

        pos_count = sum(1 for d in deltas if d > 0.001)
        neg_count = sum(1 for d in deltas if d < -0.001)
        zero_count = sum(1 for d in deltas if abs(d) <= 0.001)

        # Check for oscillating pattern
        signs = [1 if d > 0.001 else (-1 if d < -0.001 else 0) for d in deltas]
        alternations = sum(1 for i in range(1, len(signs)) if signs[i] != 0 and signs[i] == -signs[i - 1])
        if alternations >= 2:
            return TrendDirection.OSCILLATING

        if pos_count == len(deltas):
            return TrendDirection.INCREASING
        elif neg_count == len(deltas):
            return TrendDirection.DECREASING
        elif zero_count >= len(deltas) - 1:
            return TrendDirection.STABLE

        # High variance ratio
        mean_v = sum(vals) / len(vals)
        if mean_v > 0:
            var_v = sum((v - mean_v) ** 2 for v in vals) / len(vals)
            if math.sqrt(var_v) / mean_v > 0.35:
                return TrendDirection.VOLATILE

        return TrendDirection.STABLE if abs(vals[-1] - vals[0]) < 0.05 * (mean_v or 1.0) else TrendDirection.UNKNOWN

    def compute_rate_of_change(
        self,
        component: str,
        metric_name: str,
        threshold_value: Optional[float] = None,
    ) -> MetricRateOfChange:
        """Calculates current delta slope and estimates time-to-threshold with uncertainty intervals."""
        key = (component.lower(), metric_name.lower())
        buf = self._buffers.get(key)

        if not buf or len(buf) < 2:
            current_val = buf[-1].value if buf else 0.0
            return MetricRateOfChange(
                metric_name=metric_name,
                current_value=current_val,
                rate_per_minute=0.0,
                acceleration=0.0,
                threshold_value=threshold_value,
                estimated_time_to_threshold_minutes=None,
                uncertainty_interval_minutes=None,
                confidence=0.2,
                trend=TrendDirection.UNKNOWN,
            )

        recent = list(buf)[-6:]  # Up to 6 most recent samples
        t_first = recent[0].timestamp.timestamp()
        t_last = recent[-1].timestamp.timestamp()
        time_delta_min = max(0.01, (t_last - t_first) / 60.0)

        val_delta = recent[-1].value - recent[0].value
        rate_per_min = val_delta / time_delta_min
        current_val = recent[-1].value
        trend = self.detect_trend(component, metric_name)

        time_to_thresh: Optional[float] = None
        uncertainty_str: Optional[str] = None

        if threshold_value is not None:
            remaining = threshold_value - current_val
            # If rate is positive and we need to reach a higher threshold
            if rate_per_min > 0 and remaining > 0:
                est_min = remaining / rate_per_min
                time_to_thresh = round(est_min, 2)
                # Formulate calibrated interval (e.g. 5-15 min) rather than false decimal precision
                lower_bound = max(0.5, round(est_min * 0.75, 1))
                upper_bound = round(est_min * 1.35, 1)
                uncertainty_str = f"{lower_bound}–{upper_bound} min"
            elif rate_per_min < 0 and remaining < 0:  # Descending to a lower critical threshold
                est_min = remaining / rate_per_min
                time_to_thresh = round(est_min, 2)
                lower_bound = max(0.5, round(est_min * 0.75, 1))
                upper_bound = round(est_min * 1.35, 1)
                uncertainty_str = f"{lower_bound}–{upper_bound} min"

        conf = min(0.9, 0.4 + (len(recent) * 0.08))

        return MetricRateOfChange(
            metric_name=metric_name,
            current_value=round(current_val, 4),
            rate_per_minute=round(rate_per_min, 4),
            acceleration=0.0,
            threshold_value=threshold_value,
            estimated_time_to_threshold_minutes=time_to_thresh,
            uncertainty_interval_minutes=uncertainty_str,
            confidence=round(conf, 2),
            trend=trend,
        )


_global_baseline_tracker: Optional[BaselineTracker] = None


def get_baseline_tracker() -> BaselineTracker:
    global _global_baseline_tracker
    if _global_baseline_tracker is None:
        _global_baseline_tracker = BaselineTracker()
    return _global_baseline_tracker
