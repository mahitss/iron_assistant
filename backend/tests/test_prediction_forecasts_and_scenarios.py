import pytest
from datetime import datetime, timezone, timedelta
from app.prediction.forecasts import (
    Prediction,
    Forecast,
    PredictionStatus,
    PredictionWindow,
    diff_forecasts,
)
from app.prediction.scenarios import (
    Scenario,
    ScenarioGenerator,
)


def test_prediction_creation_and_time_windows():
    now = datetime.now(timezone.utc)
    pred_near = Prediction(
        subject="service:payment",
        event="latency_spike",
        predicted_state={"p99_ms": 850},
        prediction_window=PredictionWindow.NEAR_TERM,
        confidence=0.82,
        evidence_refs=["metric:latency_trend_20m"],
        assumptions=["traffic remains stable"],
    )
    assert pred_near.prediction_id.startswith("pred_")
    assert pred_near.status == PredictionStatus.ACTIVE
    assert pred_near.expires_at > pred_near.created_at
    # Near term is ~1 hour
    delta = pred_near.expires_at - pred_near.created_at
    assert 3500 <= delta.total_seconds() <= 3700

    pred_long = Prediction(
        subject="infra:storage",
        event="disk_exhaustion",
        predicted_state={"utilization_pct": 95},
        prediction_window=PredictionWindow.LONG_TERM,
        confidence=0.65,
    )
    delta_long = pred_long.expires_at - pred_long.created_at
    assert delta_long.total_seconds() >= 2500000  # ~30 days


def test_prediction_status_transitions():
    pred = Prediction(
        subject="worker:queue",
        event="backlog_saturation",
        predicted_state={"queue_depth": 5000},
        prediction_window=PredictionWindow.SHORT_TERM,
        confidence=0.78,
    )
    assert pred.status == PredictionStatus.ACTIVE
    assert not pred.is_expired

    # Confirm prediction
    pred.confirm(["metric:queue_depth:5200"])
    assert pred.status == PredictionStatus.CONFIRMED
    assert pred.resolved_at is not None
    assert "metric:queue_depth:5200" in pred.evidence_refs

    # Test disconfirm
    pred2 = Prediction(
        subject="worker:queue",
        event="backlog_saturation",
        predicted_state={"queue_depth": 5000},
        prediction_window=PredictionWindow.SHORT_TERM,
        confidence=0.78,
    )
    pred2.disconfirm("Traffic drained cleanly before threshold")
    assert pred2.status == PredictionStatus.DISCONFIRMED
    assert "Traffic drained cleanly before threshold" in pred2.assumptions


def test_forecast_scenarios_and_alternatives():
    generator = ScenarioGenerator()
    baseline = generator.create_baseline(
        description="No action taken, current trend continues",
        expected_state={"memory_utilization_pct": 98},
        likelihood=0.75,
        impact=0.8,
        evidence=["trend:memory_growth_5mb_min"],
    )
    assert baseline.is_baseline is True
    assert baseline.intervention is None

    intervention = generator.create_intervention(
        description="Horizontal pod autoscaler scales 3 additional pods",
        intervention_action="scale_replicas(count=3)",
        expected_state={"memory_utilization_pct": 52},
        likelihood=0.90,
        impact=-0.5,
        prerequisites=["cluster_capacity_available"],
    )
    assert intervention.is_baseline is False
    assert intervention.intervention == "scale_replicas(count=3)"

    forecast = Forecast(
        target="service:auth",
        scenarios=[baseline, intervention],
        likelihood=0.75,
        timeframe=PredictionWindow.SHORT_TERM,
        evidence=["trend:memory_growth_5mb_min"],
        uncertainty=0.25,
    )
    assert len(forecast.scenarios) == 2
    assert forecast.baseline_scenario.scenario_id == baseline.scenario_id
    assert len(forecast.intervention_scenarios) == 1


def test_forecast_versioning_and_diff():
    s1 = Scenario(
        description="Initial baseline",
        expected_state={"cpu": 90},
        likelihood=0.70,
        impact=0.7,
        is_baseline=True,
    )
    f1 = Forecast(
        target="service:api",
        scenarios=[s1],
        likelihood=0.70,
        timeframe=PredictionWindow.NEAR_TERM,
        evidence=["obs:1"],
        version=1,
    )

    s2 = Scenario(
        description="Revised baseline after traffic spike",
        expected_state={"cpu": 98},
        likelihood=0.88,
        impact=0.9,
        is_baseline=True,
    )
    f2 = Forecast(
        forecast_id=f1.forecast_id,
        target="service:api",
        scenarios=[s2],
        likelihood=0.88,
        timeframe=PredictionWindow.NEAR_TERM,
        evidence=["obs:1", "obs:traffic_surge"],
        version=2,
    )

    diff = diff_forecasts(f1, f2)
    assert diff["target"] == "service:api"
    assert diff["old_version"] == 1
    assert diff["new_version"] == 2
    assert diff["likelihood_diff"] == pytest.approx(0.18, 0.01)
    assert diff["new_evidence"] == ["obs:traffic_surge"]
    assert diff["scenario_count_diff"] == 0
