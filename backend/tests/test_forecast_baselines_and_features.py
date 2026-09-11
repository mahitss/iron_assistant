"""Unit tests for Forecasting Strategies, Baselines, and Temporal Features (Task 74, Spec 8, 9, 10, 16)."""

from datetime import datetime, timedelta, timezone
import pytest

from app.prediction.strategies import (
    CausalInterventionStrategy,
    EnsembleStrategy,
    ExponentialSmoothingStrategy,
    ForecastStrategyRegistry,
    HistoricalSeasonalStrategy,
    MovingAverageStrategy,
    NaiveBaselineStrategy,
    TrendExtrapolationStrategy,
)
from app.prediction.temporal_features import (
    DataLeakageError,
    TemporalDataPoint,
    TemporalFeatureExtractor,
    extract_lag_features,
    extract_rolling_statistics,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def test_naive_baseline_strategy():
    """Verify NaiveBaseline returns the last observed point with empirical interval (Spec 8, 9)."""
    strat = NaiveBaselineStrategy()
    series = [10.0, 12.0, 11.5, 13.0, 14.2]
    res = strat.generate_forecast(target="load", history=series, horizon_steps=1)

    assert res["predicted_value"] == 14.2
    assert res["baseline_value"] == 14.2
    assert res["prediction_interval"]["lower"] < 14.2
    assert res["prediction_interval"]["upper"] > 14.2
    assert res["strategy"] == "NAIVE_BASELINE"


def test_moving_average_strategy():
    """Verify MovingAverageStrategy computes rolling mean and standard deviation (Spec 8)."""
    strat = MovingAverageStrategy(window_size=3)
    series = [10.0, 20.0, 30.0, 40.0, 50.0]
    # last 3 are 30, 40, 50 -> mean = 40.0
    res = strat.generate_forecast(target="temp", history=series, horizon_steps=2)

    assert res["predicted_value"] == 40.0
    assert res["prediction_interval"]["lower"] < 40.0
    assert res["prediction_interval"]["upper"] > 40.0
    assert res["metadata"]["window_size"] == 3


def test_exponential_smoothing_holt_linear():
    """Verify Holt's linear exponential smoothing captures level and positive trend (Spec 8)."""
    strat = ExponentialSmoothingStrategy(alpha=0.5, beta=0.3)
    # Strictly increasing linear sequence: 10, 20, 30, 40, 50
    series = [10.0, 20.0, 30.0, 40.0, 50.0]
    res = strat.generate_forecast(target="growth", history=series, horizon_steps=1)

    # Next step should be > 50.0 due to positive slope
    assert res["predicted_value"] > 50.0
    assert res["metadata"]["slope"] > 0.0


def test_trend_extrapolation_strategy():
    """Verify least-squares linear trend extrapolation on known slope (Spec 8)."""
    strat = TrendExtrapolationStrategy()
    # y = 2x + 1: x in [0, 1, 2, 3, 4] -> y = [1, 3, 5, 7, 9]
    series = [1.0, 3.0, 5.0, 7.0, 9.0]
    res = strat.generate_forecast(target="linear_metric", history=series, horizon_steps=1)

    # For x = 5 (1 step ahead), y = 2(5) + 1 = 11.0
    assert res["predicted_value"] == pytest.approx(11.0, 0.05)
    assert res["metadata"]["slope"] == pytest.approx(2.0, 0.05)


def test_historical_seasonal_strategy():
    """Verify seasonal baseline matches the identical phase of the cycle (Spec 8, 9)."""
    strat = HistoricalSeasonalStrategy(seasonality_period=4)
    # 2 cycles of period 4: [10, 20, 30, 40, 10, 20, 30, 40]
    series = [10.0, 20.0, 30.0, 40.0, 10.0, 20.0, 30.0, 40.0]
    # 1 step ahead from index 7 (val 40) is index 8 -> phase 0 -> value 10.0
    res = strat.generate_forecast(target="seasonal_traffic", history=series, horizon_steps=1)

    assert res["predicted_value"] == pytest.approx(10.0, 0.1)


def test_ensemble_strategy_disagreement_detection():
    """Verify Ensemble preserves sub-model predictions and flags high disagreement (Spec 16)."""
    ensemble = EnsembleStrategy()
    # History where trend extrapolates to ~11, naive predicts 9, moving avg predicts 7
    series = [1.0, 3.0, 5.0, 7.0, 9.0]
    res = ensemble.generate_forecast(target="ensemble_test", history=series, horizon_steps=1)

    assert "sub_predictions" in res["metadata"]
    assert len(res["metadata"]["sub_predictions"]) >= 3
    assert "disagreement_spread" in res["metadata"]
    assert "high_disagreement" in res["metadata"]
    assert isinstance(res["metadata"]["high_disagreement"], bool)


def test_temporal_features_and_rolling_metrics():
    """Verify lag features, rolling metrics, velocity, acceleration, and slope (Spec 10)."""
    now = utc_now()
    points = [
        TemporalDataPoint(timestamp=now - timedelta(minutes=50 - i * 10), value=float(10 + i * 5))
        for i in range(6)
    ]
    # values: 10, 15, 20, 25, 30, 35

    extractor = TemporalFeatureExtractor(origin_time=now)
    features = extractor.extract_features("server_rps", points)

    assert features.target == "server_rps"
    assert features.current_value == 35.0
    assert features.lag_1 == 30.0
    assert features.lag_2 == 25.0
    assert features.rolling_mean == pytest.approx(22.5, 0.1)
    assert features.velocity > 0.0
    assert features.trend_slope > 0.0


def test_temporal_feature_future_data_leakage_prevented():
    """Verify strict rejection of any datapoints with timestamp > origin_time (Spec 10, 11)."""
    origin = utc_now()
    future_time = origin + timedelta(minutes=15)

    points = [
        TemporalDataPoint(timestamp=origin - timedelta(minutes=10), value=100.0),
        TemporalDataPoint(timestamp=future_time, value=150.0),  # FUTURE LEAKAGE!
    ]

    extractor = TemporalFeatureExtractor(origin_time=origin)
    with pytest.raises(DataLeakageError) as exc_info:
        extractor.extract_features("leakage_test", points)

    assert "Data leakage detected" in str(exc_info.value)
