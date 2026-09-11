"""Temporal Feature Engineering and Zero Future-Data Leakage Prevention (Task 74, Spec 10, 11).

Provides:
- Strict temporal provenance on all features
- Leakage detection and quarantine for future-dated telemetry
- Lag features, rolling statistics, velocity, acceleration, trend slope, volatility
- Seasonality indicators and event counts
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import math
from typing import Any, Dict, List, Optional, Tuple


class DataLeakageError(Exception):
    """Raised when an observation timestamp exceeds the forecast origin time."""


class TemporalFeatureError(Exception):
    """Raised when temporal feature computation fails due to missing or invalid data."""


def parse_timestamp(ts: Any) -> datetime:
    """Safely parse timestamps into UTC datetime."""
    if isinstance(ts, datetime):
        return ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    if isinstance(ts, str):
        # Handle ISO strings with Z or timezone offset
        clean_str = ts.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(clean_str)
        except ValueError:
            pass
    raise TemporalFeatureError(f"Ambiguous or unparseable timestamp: {ts}")


@dataclass
class TemporalObservation:
    """Atomic numerical or categorical observation with temporal provenance."""

    timestamp: datetime
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Any) -> TemporalObservation:
        if isinstance(data, (int, float)):
            return cls(timestamp=datetime.now(timezone.utc), value=float(data))
        if isinstance(data, dict):
            ts_val = data.get("timestamp") or data.get("time") or data.get("t")
            if ts_val is None:
                ts_val = datetime.now(timezone.utc)
            val = data.get("value") if data.get("value") is not None else (data.get("val") if data.get("val") is not None else data.get("metric_value", 0.0))
            return cls(timestamp=parse_timestamp(ts_val), value=float(val), metadata=data.get("metadata", {}))
        raise TemporalFeatureError(f"Cannot convert {type(data)} to TemporalObservation")


@dataclass
class TemporalFeatureVector:
    """Engineered temporal feature vector with audit proof of temporal isolation."""

    target_metric: str
    forecast_origin: datetime
    sample_count: int
    latest_value: float
    lags: List[float]  # [y_{t-1}, y_{t-2}, y_{t-3}]
    rolling_mean_short: float
    rolling_mean_long: float
    rolling_std: float  # Volatility
    velocity: float  # Rate of change
    acceleration: float  # Second derivative
    trend_slope: float  # OLS slope
    seasonality_index: float  # Ratio or difference from historical phase
    is_leakage_free: bool
    feature_provenance: Dict[str, Any] = field(default_factory=dict)

    @property
    def target(self) -> str:
        return self.target_metric

    @property
    def current_value(self) -> float:
        return self.latest_value

    @property
    def lag_1(self) -> float:
        return self.lags[0] if len(self.lags) > 0 else 0.0

    @property
    def lag_2(self) -> float:
        return self.lags[1] if len(self.lags) > 1 else 0.0

    @property
    def rolling_mean(self) -> float:
        return self.rolling_mean_long

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_metric": self.target_metric,
            "forecast_origin": self.forecast_origin.isoformat(),
            "sample_count": self.sample_count,
            "latest_value": round(self.latest_value, 4),
            "lags": [round(x, 4) for x in self.lags],
            "rolling_mean_short": round(self.rolling_mean_short, 4),
            "rolling_mean_long": round(self.rolling_mean_long, 4),
            "rolling_std": round(self.rolling_std, 4),
            "velocity": round(self.velocity, 4),
            "acceleration": round(self.acceleration, 4),
            "trend_slope": round(self.trend_slope, 4),
            "seasonality_index": round(self.seasonality_index, 4),
            "is_leakage_free": self.is_leakage_free,
            "feature_provenance": self.feature_provenance,
        }


class TemporalFeaturePipeline:
    """Extracts temporal features with strict zero future-data leakage enforcement (Spec 10, 11)."""

    @classmethod
    def sanitize_and_isolate_series(
        cls,
        observations: List[Any],
        forecast_origin: datetime,
        strict_quarantine: bool = True,
    ) -> List[TemporalObservation]:
        """Filters observations to strictly ensure: observation.timestamp <= forecast_origin.

        Raises DataLeakageError if future data is present and strict_quarantine is True.
        """
        valid_series: List[TemporalObservation] = []
        future_leaks: List[TemporalObservation] = []

        n_items = len(observations)
        for idx, item in enumerate(observations):
            if isinstance(item, (int, float)):
                sec_offset = (n_items - 1 - idx) * 60
                obs = TemporalObservation(
                    timestamp=forecast_origin - timedelta(seconds=sec_offset),
                    value=float(item),
                )
            elif isinstance(item, dict) and not (item.get("timestamp") or item.get("time") or item.get("t")):
                sec_offset = (n_items - 1 - idx) * 60
                val = item.get("value") if item.get("value") is not None else (item.get("val") if item.get("val") is not None else item.get("metric_value", 0.0))
                obs = TemporalObservation(
                    timestamp=forecast_origin - timedelta(seconds=sec_offset),
                    value=float(val),
                    metadata=item.get("metadata", {}),
                )
            else:
                obs = item if isinstance(item, TemporalObservation) else TemporalObservation.from_dict(item)

            if obs.timestamp > forecast_origin:
                future_leaks.append(obs)
            else:
                valid_series.append(obs)

        if future_leaks:
            msg = (
                f"Data leakage detected: {len(future_leaks)} observation(s) have timestamp > forecast_origin "
                f"({forecast_origin.isoformat()}). First leaking sample at {future_leaks[0].timestamp.isoformat()}."
            )
            if strict_quarantine:
                raise DataLeakageError(msg)

        # Sort strictly by timestamp ascending
        valid_series.sort(key=lambda x: x.timestamp)
        return valid_series

    @classmethod
    def extract_features(
        cls,
        target_metric: str,
        observations: List[Any],
        forecast_origin: Optional[datetime] = None,
        short_window: int = 3,
        long_window: int = 7,
        num_lags: int = 3,
    ) -> TemporalFeatureVector:
        """Extract multi-scale temporal features with leakage proof (Spec 10)."""
        origin = forecast_origin or datetime.now(timezone.utc)
        clean_obs = cls.sanitize_and_isolate_series(observations, origin, strict_quarantine=True)

        if not clean_obs:
            # Degenerate zero state
            return TemporalFeatureVector(
                target_metric=target_metric,
                forecast_origin=origin,
                sample_count=0,
                latest_value=0.0,
                lags=[0.0] * num_lags,
                rolling_mean_short=0.0,
                rolling_mean_long=0.0,
                rolling_std=0.0,
                velocity=0.0,
                acceleration=0.0,
                trend_slope=0.0,
                seasonality_index=1.0,
                is_leakage_free=True,
                feature_provenance={"isolation": "NO_OBSERVATIONS"},
            )

        values = [o.value for o in clean_obs]
        n = len(values)
        latest = values[-1]

        # 1. Lag features
        lags: List[float] = []
        for i in range(1, num_lags + 1):
            if n > i:
                lags.append(values[-1 - i])
            else:
                lags.append(values[0])

        # 2. Rolling stats
        sw = min(n, short_window)
        lw = min(n, long_window)
        short_slice = values[-sw:]
        long_slice = values[-lw:]

        rolling_mean_short = sum(short_slice) / sw
        rolling_mean_long = sum(long_slice) / lw

        # Volatility / standard deviation
        if lw > 1:
            variance = sum((x - rolling_mean_long) ** 2 for x in long_slice) / (lw - 1)
            rolling_std = math.sqrt(variance)
        else:
            rolling_std = 0.0

        # 3. Velocity (first difference)
        velocity = (values[-1] - values[-2]) if n >= 2 else 0.0

        # 4. Acceleration (second difference)
        if n >= 3:
            v_prev = values[-2] - values[-3]
            acceleration = velocity - v_prev
        else:
            acceleration = 0.0

        # 5. Trend slope (OLS regression on last long_window items)
        if lw >= 2:
            x_vals = list(range(lw))
            y_vals = long_slice
            x_mean = sum(x_vals) / lw
            y_mean = rolling_mean_long
            num = sum((x_vals[i] - x_mean) * (y_vals[i] - y_mean) for i in range(lw))
            den = sum((x_vals[i] - x_mean) ** 2 for i in range(lw))
            trend_slope = (num / den) if den != 0 else 0.0
        else:
            trend_slope = 0.0

        # 6. Seasonality index (e.g. ratio to long mean or lagged period)
        seasonality_index = (latest / rolling_mean_long) if rolling_mean_long != 0 else 1.0

        return TemporalFeatureVector(
            target_metric=target_metric,
            forecast_origin=origin,
            sample_count=n,
            latest_value=latest,
            lags=lags,
            rolling_mean_short=rolling_mean_short,
            rolling_mean_long=rolling_mean_long,
            rolling_std=rolling_std,
            velocity=velocity,
            acceleration=acceleration,
            trend_slope=trend_slope,
            seasonality_index=seasonality_index,
            is_leakage_free=True,
            feature_provenance={
                "first_sample": clean_obs[0].timestamp.isoformat(),
                "latest_sample": clean_obs[-1].timestamp.isoformat(),
                "origin_cutoff": origin.isoformat(),
                "leakage_audited": True,
            },
        )


TemporalDataPoint = TemporalObservation


class TemporalFeatureExtractor:
    def __init__(self, origin_time: Optional[datetime] = None) -> None:
        self.origin_time = origin_time

    def extract_features(self, target: str, observations: List[Any]) -> TemporalFeatureVector:
        return TemporalFeaturePipeline.extract_features(
            target_metric=target,
            observations=observations,
            forecast_origin=self.origin_time,
        )


def extract_lag_features(points: List[Any], num_lags: int = 3) -> List[float]:
    values = [p.value if hasattr(p, "value") else float(p) for p in points]
    return [values[-(i + 2)] if len(values) >= i + 2 else 0.0 for i in range(num_lags)]


def extract_rolling_statistics(points: List[Any], window: int = 5) -> Dict[str, float]:
    values = [p.value if hasattr(p, "value") else float(p) for p in points]
    sub = values[-window:] if len(values) >= window else values
    if not sub:
        return {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}
    m = sum(sub) / len(sub)
    variance = sum((x - m) ** 2 for x in sub) / len(sub) if len(sub) > 0 else 0.0
    return {"mean": round(m, 4), "std": round(math.sqrt(variance), 4), "min": min(sub), "max": max(sub)}

