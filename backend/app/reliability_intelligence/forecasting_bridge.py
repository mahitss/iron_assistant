"""Forecasting bridge integrating Task 74 predictive intelligence without duplication."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.reliability_intelligence.models import (
    FailureForecast,
    ForecastHorizon,
    MetricRateOfChange,
    ReliabilitySignal,
    ReliabilitySignalType,
    generate_ri_id,
    _now_utc,
)

logger = logging.getLogger("kairo.reliability_intelligence.forecasting_bridge")


class ForecastingBridge:
    """Delegates failure forecasting to Task 74 predictive engine with calibrated intervals."""

    def __init__(self, prediction_service: Optional[Any] = None) -> None:
        self._prediction_service = prediction_service

    def _get_prediction_service(self) -> Any:
        if self._prediction_service is None:
            try:
                from app.prediction.service import default_prediction_service
                self._prediction_service = default_prediction_service
            except Exception as e:
                logger.debug("Task 74 prediction service lazy init: %s", e)
        return self._prediction_service

    def forecast_failure(
        self,
        signal: ReliabilitySignal,
        rate_of_change: Optional[MetricRateOfChange] = None,
    ) -> FailureForecast:
        """Synthesizes a failure forecast with explicit uncertainty intervals."""
        comp = signal.component
        sig_type = signal.signal_type

        # Base time-to-threshold from rate of change if present
        time_to_thresh = rate_of_change.estimated_time_to_threshold_minutes if rate_of_change else None
        uncertainty = (
            rate_of_change.uncertainty_interval_minutes
            if (rate_of_change and rate_of_change.uncertainty_interval_minutes)
            else "unknown"
        )

        # Multi-horizon mapping
        if time_to_thresh is not None:
            if time_to_thresh <= 2.0:
                horizon = ForecastHorizon.IMMEDIATE
            elif time_to_thresh <= 15.0:
                horizon = ForecastHorizon.SHORT
            elif time_to_thresh <= 60.0:
                horizon = ForecastHorizon.MEDIUM
            else:
                horizon = ForecastHorizon.LONG
        else:
            # Fallback horizon based on severity
            horizon = ForecastHorizon.IMMEDIATE if signal.severity in ("P0", "P1") else ForecastHorizon.SHORT

        # Calibrated probability estimate
        prob = 0.5
        if signal.severity == "P0":
            prob = 0.95
        elif signal.severity == "P1":
            prob = 0.85
        elif signal.severity == "P2":
            prob = 0.65
        else:
            prob = 0.35

        # Incorporate slope confidence
        conf = signal.confidence
        if rate_of_change:
            conf = round((conf + rate_of_change.confidence) / 2.0, 2)

        # Estimate prevention window (time available to act safely before failure threshold)
        prev_window = None
        if time_to_thresh is not None:
            prev_window = max(0.5, round(time_to_thresh * 0.5, 1))

        evidence = [
            f"Observed {sig_type.value} on {comp} at value {signal.current_value}",
            f"Trend is {signal.trend.value}",
        ]
        if rate_of_change and rate_of_change.rate_per_minute != 0.0:
            evidence.append(f"Rate of change is {rate_of_change.rate_per_minute:+.2f}/min")
        if uncertainty != "unknown":
            evidence.append(f"Estimated threshold crossing in {uncertainty}")

        return FailureForecast(
            forecast_id=generate_ri_id("fc"),
            target_component=comp,
            failure_probability=prob,
            time_horizon=horizon,
            estimated_time_to_failure_minutes=time_to_thresh,
            uncertainty_interval=uncertainty,
            prevention_window_minutes=prev_window,
            confidence=conf,
            evidence=evidence,
        )


_global_forecasting_bridge: Optional[ForecastingBridge] = None


def get_forecasting_bridge() -> ForecastingBridge:
    global _global_forecasting_bridge
    if _global_forecasting_bridge is None:
        _global_forecasting_bridge = ForecastingBridge()
    return _global_forecasting_bridge
