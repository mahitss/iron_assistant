"""Unit tests for Forecast Domain Model, 10-state Lifecycle, and Versioning (Task 74, Spec 4, 5, 6, 34, 35, 63)."""

from datetime import datetime, timedelta, timezone
import pytest

from app.prediction.forecasts import Forecast, InvalidStateTransitionError
from app.prediction.schemas import (
    BaselineSpec,
    ForecastHorizon,
    ForecastQualityScore,
    ForecastState,
    ForecastStrategyType,
    ForecastType,
    PredictionInterval,
    UncertaintyBreakdown,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def test_forecast_initialization_defaults():
    """Verify default initialization, state=DRAFT, and ontological labeling (Spec 1, 4, 5)."""
    origin = utc_now()
    fc = Forecast(
        target="cpu_utilization",
        predicted_value=78.5,
        horizon=ForecastHorizon.SHORT,
        forecast_type=ForecastType.POINT,
        strategy=ForecastStrategyType.TREND_EXTRAPOLATION,
        origin_time=origin,
    )
    assert fc.target == "cpu_utilization"
    assert fc.predicted_value == 78.5
    assert fc.label == "FORECAST"
    assert fc.is_observed_fact is False
    assert fc.state == ForecastState.DRAFT
    assert fc.version == 1
    assert fc.forecast_id.startswith("fc_")
    assert fc.forecast_start >= origin
    assert fc.forecast_end > fc.forecast_start


def test_forecast_lifecycle_valid_transitions():
    """Verify strictly validated state transitions along canonical lifecycle (Spec 5)."""
    origin = utc_now()
    fc = Forecast(
        target="memory_usage",
        predicted_value=64.0,
        horizon=ForecastHorizon.MEDIUM,
        forecast_type=ForecastType.INTERVAL,
        strategy=ForecastStrategyType.MOVING_AVERAGE,
        origin_time=origin,
    )
    assert fc.state == ForecastState.DRAFT

    # DRAFT -> GENERATED
    fc.transition_to(ForecastState.GENERATED, reason="Model computation finished")
    assert fc.state == ForecastState.GENERATED

    # GENERATED -> PUBLISHED
    fc.transition_to(ForecastState.PUBLISHED, reason="Passed sanity checks and published")
    assert fc.state == ForecastState.PUBLISHED

    # PUBLISHED -> MONITORING
    fc.transition_to(ForecastState.MONITORING, reason="Attached telemetry observer")
    assert fc.state == ForecastState.MONITORING

    # MONITORING -> VERIFIED_BY_OUTCOME
    fc.record_outcome(actual_value=66.2, action_influenced=False)
    assert fc.state == ForecastState.VERIFIED_BY_OUTCOME
    assert fc.actual_outcome == 66.2
    assert fc.evaluation_results["error"] == pytest.approx(2.2, 0.01)
    assert fc.evaluation_results["directional_correct"] is True


def test_forecast_lifecycle_invalid_transition_rejected():
    """Verify InvalidStateTransitionError is raised on prohibited jumps (Spec 5)."""
    fc = Forecast(
        target="api_latency",
        predicted_value=120.0,
        horizon=ForecastHorizon.SHORT,
        forecast_type=ForecastType.POINT,
        strategy=ForecastStrategyType.NAIVE_BASELINE,
    )
    assert fc.state == ForecastState.DRAFT

    # Cannot jump directly from DRAFT to VERIFIED_BY_OUTCOME
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        fc.transition_to(ForecastState.VERIFIED_BY_OUTCOME, reason="Bypassing evaluation")
    assert "Invalid state transition from DRAFT to VERIFIED_BY_OUTCOME" in str(exc_info.value)

    # Move to PUBLISHED
    fc.transition_to(ForecastState.GENERATED)
    fc.transition_to(ForecastState.PUBLISHED)

    # Cannot transition from PUBLISHED back to DRAFT
    with pytest.raises(InvalidStateTransitionError):
        fc.transition_to(ForecastState.DRAFT)


def test_forecast_immutable_versioning_and_diff():
    """Verify version bumping, immutable previous record, and diff computation (Spec 34, 35)."""
    fc = Forecast(
        target="disk_io",
        predicted_value=500.0,
        horizon=ForecastHorizon.SHORT,
        strategy=ForecastStrategyType.TREND_EXTRAPOLATION,
    )
    fc.transition_to(ForecastState.GENERATED)
    fc.transition_to(ForecastState.PUBLISHED)
    assert fc.version == 1

    # Refresh forecast with updated inputs
    new_interval = PredictionInterval(lower=510.0, upper=620.0, coverage_target=0.90)
    ver_record = fc.update_forecast(
        new_predicted_value=560.0,
        new_prediction_interval=new_interval,
        change_reason="Sudden telemetry spike in last 5 minutes",
        changed_inputs={"io_burst_rate": 1400},
        changed_assumptions=["write_queue_depth > 100"],
    )

    assert fc.version == 2
    assert fc.state == ForecastState.UPDATED
    assert fc.predicted_value == 560.0
    assert len(fc.versions) == 1

    assert ver_record.version == 2
    assert ver_record.previous_version == 1
    assert ver_record.diff["predicted_value"]["previous"] == 500.0
    assert ver_record.diff["predicted_value"]["current"] == 560.0
    assert "Sudden telemetry spike" in ver_record.change_reason


def test_forecast_horizon_validity_and_stale_detection():
    """Verify horizon time window calculation and stale detection (Spec 6, 38)."""
    now = utc_now()
    past_origin = now - timedelta(hours=3)

    # Short horizon (1 hour validity by default)
    fc = Forecast(
        target="throughput",
        predicted_value=1000.0,
        horizon=ForecastHorizon.SHORT,
        origin_time=past_origin,
    )
    fc.transition_to(ForecastState.GENERATED)
    fc.transition_to(ForecastState.PUBLISHED)

    # Since past_origin was 3 hours ago and SHORT horizon expiration is ~1h, it must be stale
    assert fc.is_stale() is True


def test_forecast_quality_score_calculation():
    """Verify composite interpretability of ForecastQualityScore (Spec 63)."""
    score = ForecastQualityScore(
        data_quality=0.95,
        historical_strategy_performance=0.88,
        calibration_score=0.90,
        recency_score=1.0,
        model_agreement_score=0.85,
        causal_validity_score=0.80,
        horizon_difficulty=0.20,  # 0.20 penalty
        feature_completeness=1.0,
    )
    composite = score.composite_score
    assert 0.0 <= composite <= 1.0
    assert composite > 0.80  # high quality
    assert score.to_dict()["composite_score"] == composite
