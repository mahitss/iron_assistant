"""Tests for Prediction Models, Lifecycles, Time Windows, and Schemas (Task 47)."""

from datetime import datetime, timedelta, timezone
import pytest

from app.prediction.forecasts import (
    Forecast,
    Prediction,
    PredictionStatus,
    PredictionWindow,
)
from app.prediction.schemas import (
    ForecastCreateRequest,
    PredictionCreateRequest,
    PredictionResponse,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def test_6_prediction_statuses():
    """Enforce Spec 3: Support ACTIVE, CONFIRMED, DISCONFIRMED, EXPIRED, CANCELLED, UNKNOWN."""
    expected = ["ACTIVE", "CONFIRMED", "DISCONFIRMED", "EXPIRED", "CANCELLED", "UNKNOWN"]
    for s in expected:
        assert PredictionStatus(s) is not None


def test_prediction_creation_and_expiration():
    """Enforce Spec 2, 4, 5: Explicit time interval, time-bounded windows, avoid vague 'soon'."""
    now = utc_now()
    pred = Prediction(
        prediction_id="pred_01",
        subject="service:payment:latency",
        event="LATENCY_SPIKE",
        predicted_state={"latency_ms": 500, "status": "DEGRADED"},
        prediction_window=PredictionWindow.SHORT_TERM,
        confidence=0.85,
        model_reference="trend_linear_v1",
        created_at=now,
        expires_at=now + timedelta(hours=2),
        assumptions=["Traffic volume doubles based on marketing campaign"],
        evidence_refs=["obs_pay_01", "obs_pay_02"],
        scope={"user_id": "u1", "project_id": "p1"},
    )

    assert pred.prediction_id == "pred_01"
    assert pred.confidence == 0.85
    assert pred.status == PredictionStatus.ACTIVE
    assert pred.is_expired is False

    # Simulate expired prediction (Spec 38, 144)
    pred.expires_at = now - timedelta(seconds=1)
    assert pred.is_expired is True


def test_prediction_outcome_evaluation_confirmed_and_disconfirmed():
    """Enforce Spec 138-143: A prediction becomes CONFIRMED or DISCONFIRMED based on observed evidence."""
    pred = Prediction(
        prediction_id="pred_02",
        subject="service:redis:memory",
        event="CAPACITY_EXHAUSTED",
        predicted_state={"status": "OOM"},
        prediction_window=PredictionWindow.NEAR_TERM,
        confidence=0.9,
        model_reference="trend_linear_v1",
    )

    # Disconfirming outcome
    status1 = pred.evaluate_outcome({"status": "HEALTHY", "memory_pct": 55})
    assert status1 == PredictionStatus.DISCONFIRMED
    assert pred.status == PredictionStatus.DISCONFIRMED

    # Confirming outcome
    pred.status = PredictionStatus.ACTIVE
    status2 = pred.evaluate_outcome({"status": "OOM", "memory_pct": 100})
    assert status2 == PredictionStatus.CONFIRMED
    assert pred.status == PredictionStatus.CONFIRMED


def test_no_self_fulfilling_label():
    """Enforce Spec 24: If Kairo takes an action, record that prediction influenced the outcome."""
    pred = Prediction(
        prediction_id="pred_03",
        subject="service:api:cache",
        event="CACHE_THRASHING",
        predicted_state={"hit_rate": 0.2},
        prediction_window=PredictionWindow.SHORT_TERM,
        confidence=0.8,
        model_reference="trend_linear_v1",
    )

    pred.evaluate_outcome({"hit_rate": 0.85}, was_action_influenced=True)
    assert pred.action_influenced is True


def test_pydantic_schema_validation():
    req = PredictionCreateRequest(
        subject="database:iops",
        event="IOPS_SATURATION",
        predicted_state={"iops": 5000},
        prediction_window="short-term",
        confidence=0.78,
    )
    assert req.subject == "database:iops"
    assert req.confidence == 0.78
