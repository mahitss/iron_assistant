"""Unit tests for Temporal Backtesting and Zero Future Data Leakage (Task 74, Spec 11, 12)."""

from datetime import datetime, timedelta, timezone
import pytest

from app.prediction.backtesting import TemporalBacktester
from app.prediction.schemas import BacktestConfig, ForecastStrategyType
from app.prediction.temporal_features import DataLeakageError, TemporalDataPoint


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def test_rolling_origin_backtesting_execution():
    """Verify rolling-origin backtester evaluates successive folds without temporal leakage (Spec 12)."""
    # 20 observations with linear growth + small oscillation
    series = [float(10 + i * 2 + (1 if i % 2 == 0 else -1)) for i in range(25)]

    config = BacktestConfig(
        target="network_packets",
        strategy=ForecastStrategyType.TREND_EXTRAPOLATION,
        horizon_steps=1,
        window_type="rolling",
        min_train_size=10,
        step_size=2,
        leakage_check_strict=True,
    )

    tester = TemporalBacktester()
    result = tester.run_backtest(target="network_packets", series=series, config=config)

    assert result.target == "network_packets"
    assert result.strategy == "TREND_EXTRAPOLATION"
    assert result.folds_evaluated > 0
    assert result.mae >= 0.0
    assert result.rmse >= 0.0
    assert result.temporal_isolation_verified is True
    assert len(result.evaluation_records) == result.folds_evaluated


def test_expanding_window_backtesting_execution():
    """Verify expanding-window backtesting increases training size fold by fold (Spec 12)."""
    series = [float(50 + i * 1.5) for i in range(20)]

    config = BacktestConfig(
        target="db_connections",
        strategy=ForecastStrategyType.MOVING_AVERAGE,
        horizon_steps=1,
        window_type="expanding",
        min_train_size=8,
        step_size=1,
    )

    tester = TemporalBacktester()
    result = tester.run_backtest(target="db_connections", series=series, config=config)

    assert result.folds_evaluated == (20 - 8 - 1 + 1)
    assert result.temporal_isolation_verified is True


def test_msss_skill_score_against_baseline():
    """Verify Mean Squared Skill Score is calculated relative to naive baseline (Spec 9, 12, 13)."""
    # Strongly linear trend where TrendExtrapolation should drastically beat NaiveBaseline
    series = [float(i * 10) for i in range(20)]

    config = BacktestConfig(
        target="linear_growth",
        strategy=ForecastStrategyType.TREND_EXTRAPOLATION,
        horizon_steps=1,
        window_type="rolling",
        min_train_size=5,
        step_size=1,
    )

    tester = TemporalBacktester()
    result = tester.run_backtest(target="linear_growth", series=series, config=config)

    # TrendExtrapolation should have RMSE lower than baseline RMSE, so MSSS > 0
    assert result.baseline_rmse > 0.0
    assert result.rmse < result.baseline_rmse
    assert result.skill_score_msss > 0.0  # Demonstrating genuine skill superiority over baseline


def test_backtester_catches_and_rejects_insufficient_data():
    """Verify backtester raises ValueError when series length < min_train_size + horizon (Spec 12, 39)."""
    series = [1.0, 2.0, 3.0]
    config = BacktestConfig(
        target="tiny_series",
        min_train_size=10,
        horizon_steps=2,
    )

    tester = TemporalBacktester()
    with pytest.raises(ValueError) as exc_info:
        tester.run_backtest(target="tiny_series", series=series, config=config)

    assert "Insufficient time-series" in str(exc_info.value)
