"""Tests for Multi-Horizon Range Forecasting and Calibration Tracking (Task 65)."""

from app.foresight.forecasting import LongHorizonForecaster
from app.foresight.schemas import (
    ForecastStatus,
    ForesightHorizon,
)


def test_forecast_not_fact_and_no_false_precision():
    """Verify FORECAST != FACT and NO FALSE PRECISION invariants (Spec 28, 29).

    Forecasts must always specify lower and upper probability bounds.
    """
    forecaster = LongHorizonForecaster()
    fct = forecaster.generate_forecast(
        topic="Peak Transactions per Second",
        horizon=ForesightHorizon.MID_FUTURE_1M,
        metric_name="tps",
        base_estimate=500.0,
        assumptions=["Traffic grows at standard 5% month-over-month rate"],
    )

    assert fct.status == ForecastStatus.ACTIVE
    assert len(fct.intervals) > 0
    interval = fct.intervals[0]
    # No false precision: must have distinct bounds
    assert interval.lower_bound < interval.upper_bound
    assert interval.lower_bound <= interval.point_estimate <= interval.upper_bound


def test_expanding_uncertainty_cone():
    """Verify expanding uncertainty cone across temporal horizons (Spec 30).

    Farther horizons (1y) must have wider interval spreads than near horizons (1h).
    """
    forecaster = LongHorizonForecaster()

    near_fct = forecaster.generate_forecast(
        topic="CPU Utilization",
        horizon=ForesightHorizon.NEAR_FUTURE_1H,
        metric_name="cpu_pct",
        base_estimate=50.0,
    )

    far_fct = forecaster.generate_forecast(
        topic="CPU Utilization",
        horizon=ForesightHorizon.LONG_FUTURE_1Y,
        metric_name="cpu_pct",
        base_estimate=50.0,
    )

    near_spread = near_fct.intervals[0].upper_bound - near_fct.intervals[0].lower_bound
    far_spread = far_fct.intervals[0].upper_bound - far_fct.intervals[0].lower_bound

    assert far_spread > near_spread
    # Confidence in 1-year forecast must be lower than 1-hour forecast
    assert far_fct.confidence < near_fct.confidence


def test_assumption_invalidation_lifecycle():
    """Verify automatic invalidation of forecasts when core assumptions fail (Spec 33)."""
    forecaster = LongHorizonForecaster()
    fct = forecaster.generate_forecast(
        topic="Cloud Storage Expenditure",
        horizon=ForesightHorizon.MID_FUTURE_1M,
        metric_name="cost_usd",
        base_estimate=12000.0,
        assumptions=["Spot pricing discount tier remains active", "Retention policy unchanged"],
    )

    # Invalidate assumption
    invalidated_ids = forecaster.invalidate_on_assumption_failure("Spot pricing discount tier")
    assert fct.forecast_id in invalidated_ids

    retrieved = forecaster.get_forecast(fct.forecast_id)
    assert retrieved.status == ForecastStatus.INVALIDATED


def test_forecast_calibration_scoring():
    """Verify Brier/calibration score calculation upon outcome realization (Spec 34)."""
    forecaster = LongHorizonForecaster()
    fct = forecaster.generate_forecast(
        topic="Memory Consumption",
        horizon=ForesightHorizon.NEAR_FUTURE_1H,
        metric_name="gb",
        base_estimate=16.0,
    )

    # Real outcome is within interval
    actual_gb = 16.5
    score = forecaster.record_actual_outcome(fct.forecast_id, actual_gb)
    assert 0.0 <= score <= 1.0

    retrieved = forecaster.get_forecast(fct.forecast_id)
    assert retrieved.status == ForecastStatus.FULFILLED
    assert retrieved.calibration_score == score
