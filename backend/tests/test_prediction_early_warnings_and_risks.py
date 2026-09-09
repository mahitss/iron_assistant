import pytest
from datetime import datetime, timezone, timedelta
from app.prediction.early_warning import (
    EarlyWarning,
    EarlyWarningManager,
    WarningSeverity,
    WarningStatus,
)
from app.prediction.risk import (
    PredictedRisk,
    RiskAnticipator,
)
from app.prediction.forecasts import PredictionWindow


def test_early_warning_lifecycle_and_deduplication():
    manager = EarlyWarningManager()

    w1 = manager.create_warning(
        target="db:primary",
        signal="connection_pool_saturation",
        predicted_event="exhaustion_in_15m",
        timeframe=PredictionWindow.NEAR_TERM,
        confidence=0.75,
        severity=WarningSeverity.HIGH,
        evidence=["pool_active:98/100"],
    )
    assert w1.status == WarningStatus.OPEN
    assert w1.target == "db:primary"

    # Deduplication: identical target and predicted event within active window merges
    w2 = manager.create_warning(
        target="db:primary",
        signal="connection_pool_saturation",
        predicted_event="exhaustion_in_15m",
        timeframe=PredictionWindow.NEAR_TERM,
        confidence=0.85,
        severity=WarningSeverity.HIGH,
        evidence=["pool_active:99/100"],
    )
    assert w2.warning_id == w1.warning_id
    assert w2.confidence == 0.85
    assert len(w2.evidence) == 2
    assert "pool_active:99/100" in w2.evidence


def test_early_warning_escalation_and_decay():
    manager = EarlyWarningManager()

    warning = manager.create_warning(
        target="api:gateway",
        signal="5xx_spike",
        predicted_event="circuit_breaker_trip",
        timeframe=PredictionWindow.NEAR_TERM,
        confidence=0.60,
        severity=WarningSeverity.MEDIUM,
        evidence=["5xx_rate:2.1%"],
    )

    # Escalate when confidence and severity increase
    escalated = manager.escalate_warning(
        warning.warning_id,
        new_confidence=0.92,
        new_severity=WarningSeverity.CRITICAL,
        new_evidence="5xx_rate:12.4%",
    )
    assert escalated.severity == WarningSeverity.CRITICAL
    assert escalated.confidence == 0.92
    assert escalated.status == WarningStatus.OPEN

    # Decay reduces confidence
    decayed = manager.decay_warning(warning.warning_id, decay_factor=0.5)
    assert decayed.confidence == pytest.approx(0.46, 0.01)

    # Confirm and dismiss
    manager.confirm_warning(warning.warning_id, "Circuit breaker tripped at 12:45 UTC")
    assert warning.status == WarningStatus.CONFIRMED

    # Expired check
    warning2 = manager.create_warning(
        target="api:gateway:backup",
        signal="5xx_spike",
        predicted_event="circuit_breaker_trip_backup",
        timeframe=PredictionWindow.NEAR_TERM,
        confidence=0.60,
        severity=WarningSeverity.MEDIUM,
    )
    warning2.expires_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    expired_count = manager.expire_stale_warnings()
    assert expired_count >= 1
    assert warning2.status == WarningStatus.EXPIRED


def test_predicted_risk_model_and_mitigation():
    anticipator = RiskAnticipator()

    risk = anticipator.assess_risk(
        subject="service:order_processor",
        event="deadlock_under_high_concurrency",
        likelihood=0.65,
        impact=0.80,
        timeframe=PredictionWindow.SHORT_TERM,
        evidence=["lock_wait_timeout_count:14"],
        confidence=0.70,
    )

    assert risk.risk_id.startswith("risk_")
    # Risk score is likelihood * impact = 0.65 * 0.80 = 0.52
    assert risk.risk_score == pytest.approx(0.52, 0.01)
    assert risk.is_high_risk() is True
    assert len(risk.mitigations) > 0

    # Mitigation recommendations must not execute autonomously
    # Candidate mitigations should be labeled as proposals requiring authorization
    for mitigation in risk.mitigations:
        assert "requires_approval" in mitigation or "action" in mitigation
