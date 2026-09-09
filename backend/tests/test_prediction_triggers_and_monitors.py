import pytest
from datetime import datetime, timezone, timedelta
from app.prediction.triggers import (
    PredictionTrigger,
    TriggerType,
    ActionClass,
    TriggerStatus,
    evaluate_trigger,
)
from app.prediction.monitors import (
    PredictionMonitor,
    MonitorRegistry,
    MonitorBudgetExceededError,
)
from app.prediction.forecasts import Prediction, PredictionWindow


def test_prediction_trigger_evaluation_and_safety():
    # Safe preemptive trigger
    safe_trigger = PredictionTrigger(
        condition="cpu_utilization > 85",
        trigger_type=TriggerType.THRESHOLD,
        scope="service:checkout",
        required_evidence=["cpu_utilization"],
        action_class=ActionClass.SAFE_PREEMPTIVE,
        action_name="warm_cache",
        authorized=True,
    )
    assert safe_trigger.status == TriggerStatus.PENDING

    fired, reason = evaluate_trigger(safe_trigger, observed_state={"cpu_utilization": 90})
    assert fired is True
    assert safe_trigger.status == TriggerStatus.FIRED

    # Destructive trigger cannot fire without explicit authorization even if condition met
    destructive_trigger = PredictionTrigger(
        condition="error_rate > 50",
        trigger_type=TriggerType.THRESHOLD,
        scope="service:checkout",
        required_evidence=["error_rate"],
        action_class=ActionClass.DESTRUCTIVE,
        action_name="terminate_database_instance",
        authorized=False,
    )
    fired_destr, reason_destr = evaluate_trigger(destructive_trigger, observed_state={"error_rate": 75})
    assert fired_destr is False
    assert "destructive" in reason_destr.lower() or "unauthorized" in reason_destr.lower()
    assert destructive_trigger.status == TriggerStatus.BLOCKED


def test_monitor_registry_budget_and_lifecycle():
    registry = MonitorRegistry(max_active_monitors=3)

    pred1 = Prediction(subject="s1", event="e1", predicted_state={}, prediction_window=PredictionWindow.NEAR_TERM, confidence=0.7)
    pred2 = Prediction(subject="s2", event="e2", predicted_state={}, prediction_window=PredictionWindow.NEAR_TERM, confidence=0.7)
    pred3 = Prediction(subject="s3", event="e3", predicted_state={}, prediction_window=PredictionWindow.NEAR_TERM, confidence=0.7)
    pred4 = Prediction(subject="s4", event="e4", predicted_state={}, prediction_window=PredictionWindow.NEAR_TERM, confidence=0.7)

    m1 = registry.register_monitor(pred1.prediction_id, pred1.subject, max_polls=5)
    m2 = registry.register_monitor(pred2.prediction_id, pred2.subject, max_polls=5)
    m3 = registry.register_monitor(pred3.prediction_id, pred3.subject, max_polls=5)
    assert len(registry.list_active_monitors()) == 3

    # Exceeding budget should raise or reject
    with pytest.raises(MonitorBudgetExceededError):
        registry.register_monitor(pred4.prediction_id, pred4.subject, max_polls=5)

    # Monitor poll and update
    m1.record_poll(observed_evidence="metric:s1:ok")
    assert m1.poll_count == 1

    # Cleanup expired predictions removes monitors
    pred1.expires_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    cleaned = registry.cleanup_expired([pred1.prediction_id])
    assert cleaned >= 1
    assert len(registry.list_active_monitors()) == 2
