"""Unit tests for Early Warning Hysteresis, Deduplication, and Leading Indicators (Task 74, Spec 20, 24-28, 65, 66, 68)."""

from datetime import datetime, timedelta, timezone
import pytest

from app.prediction.early_warning import (
    EarlyWarningHysteresisConfig,
    EarlyWarningManager,
)
from app.prediction.indicators import LeadingIndicatorRegistry
from app.prediction.schemas import (
    EarlyWarningResolution,
    EarlyWarningSeverity,
    EarlyWarningState,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def test_anti_flapping_hysteresis_activation_and_hold():
    """Verify warning activates at >=0.75 and stays active when risk drops to 0.68 (Spec 26)."""
    cfg = EarlyWarningHysteresisConfig(
        activation_threshold=0.75,
        deactivation_threshold=0.60,
        min_persistence_seconds=0,
    )
    manager = EarlyWarningManager(hysteresis_config=cfg)

    # Risk = 0.70 (below activation threshold 0.75): Should NOT activate
    w1 = manager.process_signal_with_hysteresis(
        target="db_cluster",
        signal="connection_load",
        predicted_event="connection_exhaustion",
        risk_score=0.70,
    )
    assert w1 is None

    # Risk = 0.78 (crosses activation threshold 0.75): Activates warning
    w2 = manager.process_signal_with_hysteresis(
        target="db_cluster",
        signal="connection_load",
        predicted_event="connection_exhaustion",
        risk_score=0.78,
    )
    assert w2 is not None
    assert w2.state == EarlyWarningState.ACTIVE

    # Flapping test: Risk drops to 0.68 (below 0.75, but above deactivation 0.60):
    # Warning must STAY ACTIVE due to hysteresis
    w3 = manager.process_signal_with_hysteresis(
        target="db_cluster",
        signal="connection_load",
        predicted_event="connection_exhaustion",
        risk_score=0.68,
    )
    assert w3 is not None
    assert w3.warning_id == w2.warning_id
    assert w3.state == EarlyWarningState.ACTIVE
    assert w3.hysteresis_active is True

    # Risk drops to 0.55 (below deactivation threshold 0.60):
    # Warning resolves with resolution=RISK_DECREASED
    w4 = manager.process_signal_with_hysteresis(
        target="db_cluster",
        signal="connection_load",
        predicted_event="connection_exhaustion",
        risk_score=0.55,
    )
    assert w4 is not None
    assert w4.state == EarlyWarningState.RESOLVED
    assert w4.resolution == EarlyWarningResolution.RISK_DECREASED


def test_warning_deduplication_via_stable_fingerprint():
    """Verify repeated telemetry updates identical warning in place without spamming (Spec 27)."""
    manager = EarlyWarningManager()

    w1 = manager.create_warning(
        target="auth_service",
        signal="token_expiry_mismatch",
        predicted_event="auth_token_storm",
        confidence=0.82,
        severity=EarlyWarningSeverity.WARNING,
        evidence=["jwt_clock_skew:45s"],
    )

    # Identical target, signal, predicted_event within active window
    w2 = manager.create_warning(
        target="auth_service",
        signal="token_expiry_mismatch",
        predicted_event="auth_token_storm",
        confidence=0.86,
        severity=EarlyWarningSeverity.WARNING,
        evidence=["jwt_clock_skew:52s"],
    )

    assert w1.warning_id == w2.warning_id
    assert len(manager.list_all()) == 1
    assert w2.confidence == 0.86
    assert "jwt_clock_skew:52s" in w2.evidence


def test_warning_lead_time_tracking_on_event_occurrence():
    """Verify lead time calculation between warning creation and event occurrence (Spec 66, 68)."""
    manager = EarlyWarningManager()
    past_created = utc_now() - timedelta(minutes=15)

    w = manager.create_warning(
        target="api_gateway",
        signal="rate_limit_saturation",
        predicted_event="service_throttling",
        confidence=0.85,
    )
    w.created_at = past_created  # simulate 15 minutes ago

    # Confirm actual event occurred
    manager.confirm_warning(w.warning_id, evidence_details="Throttling observed at 14:15")

    assert w.state == EarlyWarningState.RESOLVED
    assert w.resolution == EarlyWarningResolution.EVENT_OCCURRED
    assert w.lead_time_seconds is not None
    assert w.lead_time_seconds >= 900.0  # >= 15 minutes lead time


def test_warning_to_attention_candidate_payload():
    """Verify structured attention candidate formatting without incident confusion (Spec 28, 29)."""
    manager = EarlyWarningManager()
    w = manager.create_warning(
        target="payment_pipeline",
        signal="declines_accelerating",
        predicted_event="gateway_disconnect",
        confidence=0.88,
        severity=EarlyWarningSeverity.CRITICAL,
        evidence=["decline_code_99_spike"],
    )

    attn = w.to_attention_candidate_dict()

    assert attn["source_type"] == "early_warning"
    assert attn["source_id"] == w.warning_id
    assert "Early Warning: gateway_disconnect on payment_pipeline" in attn["title"]
    assert attn["severity"] == "CRITICAL"
    assert attn["urgency"] == 0.9
    assert attn["risk"] > 0.8


def test_leading_indicators_empirical_reliability_tracking():
    """Verify LeadingIndicatorRegistry computes deviation and Bayesian updates (Spec 20)."""
    registry = LeadingIndicatorRegistry()

    registry.register_indicator(
        indicator_id="swap_usage_pct",
        target="vm_host_oom",
        relationship="positive_correlation",
        direction="increasing",
        expected_lead_time_minutes=20,
        baseline_value=10.0,
        current_value=45.0,  # +35 deviation
    )

    # Record 4 true positives and 1 false positive
    for _ in range(4):
        registry.record_observation("swap_usage_pct", target_occurred=True)
    registry.record_observation("swap_usage_pct", target_occurred=False)

    ind = registry.get_indicator("swap_usage_pct")
    assert ind is not None
    assert ind.historical_reliability == pytest.approx(4.0 / 5.0, 0.05)
    assert ind.reliability_score > 0.70
    assert ind.deviation == pytest.approx(35.0, 0.1)
