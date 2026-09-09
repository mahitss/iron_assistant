"""Telemetry Signals, Trend Detection, and Anomaly-to-Prediction Ingestion (Task 47)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger("kairo.prediction.signals")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class DetectedTrend:
    """Statistical trend derived from sequential observations (Spec 26, 27, 76, 77)."""

    subject: str
    metric: str
    slope: float  # Positive = growing, negative = shrinking
    datapoints_count: int
    is_statistically_significant: bool
    projected_exhaustion_seconds: Optional[float] = None
    detected_at: datetime = field(default_factory=utc_now)


class SignalDetector:
    """Extracts trends and anomalies into predictive signals (Spec 26-29, 76, 77)."""

    @classmethod
    def detect_linear_trend(
        cls,
        subject: str,
        metric_name: str,
        series: List[tuple[float, float]],  # list of (timestamp_offset_seconds, value)
        critical_threshold: Optional[float] = None,
    ) -> Optional[DetectedTrend]:
        """Enforce Spec 26, 27: Detect trends (e.g. latency increasing, capacity depleting)."""
        if len(series) < 3:
            return None

        n = len(series)
        x_vals = [pt[0] for pt in series]
        y_vals = [pt[1] for pt in series]

        x_mean = sum(x_vals) / n
        y_mean = sum(y_vals) / n

        num = sum((x_vals[i] - x_mean) * (y_vals[i] - y_mean) for i in range(n))
        den = sum((x_vals[i] - x_mean) ** 2 for i in range(n))

        slope = (num / den) if den != 0 else 0.0
        # Positive slope means metric is growing
        is_significant = abs(slope) > 0.01

        # Project time to reach threshold if growing toward it
        time_to_exhaust = None
        if critical_threshold is not None and slope > 0:
            current_val = y_vals[-1]
            if current_val < critical_threshold:
                time_to_exhaust = (critical_threshold - current_val) / slope

        logger.info("Detected trend on %s (%s): slope=%.4f (pts=%d)", subject, metric_name, slope, n)
        return DetectedTrend(
            subject=subject,
            metric=metric_name,
            slope=slope,
            datapoints_count=n,
            is_statistically_significant=is_significant,
            projected_exhaustion_seconds=time_to_exhaust,
        )

    @classmethod
    def evaluate_anomaly_signal(cls, anomaly_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Enforce Spec 28, 29: Anomaly signals may become predictive inputs. Anomaly != failure."""
        subj = anomaly_data.get("subject", "unknown")
        confidence = anomaly_data.get("confidence", 0.5)

        # Do not predict failure solely on uncalibrated minor anomaly (Spec 29)
        if confidence < 0.6:
            return None

        return {
            "signal_type": "ANOMALY_INPUT",
            "subject": subj,
            "observed_deviation": anomaly_data.get("deviation", 1.0),
            "evidence": anomaly_data.get("evidence", {}),
            "timestamp": utc_now().isoformat(),
        }
