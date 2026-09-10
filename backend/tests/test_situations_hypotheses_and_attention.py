"""Unit tests for Causal Hypotheses and Attention Prioritization (Task 60)."""

from datetime import datetime, timezone

from app.situational_awareness.attention import AttentionEngine
from app.situational_awareness.hypotheses import HypothesisEngine
from app.situational_awareness.schemas import (
    CausalConfidence,
    NormalizedEvent,
    Situation,
    SituationSeverity,
    SituationStatus,
    SourceTrustLevel,
)


def _make_event(
    event_id: str,
    event_type: str,
    subject: str,
    resource: str = "web-svc",
    is_anomaly: bool = False,
) -> NormalizedEvent:
    now = datetime.now(timezone.utc)
    return NormalizedEvent(
        event_id=event_id,
        event_type=event_type,
        source="system",
        source_trust=SourceTrustLevel.TRUSTED_SYSTEM,
        environment="production",
        resource=resource,
        subject=subject,
        payload={},
        severity=SituationSeverity.HIGH,
        is_anomaly=is_anomaly,
        occurred_at=now,
        received_at=now,
    )


def test_hypotheses_generation_for_deployment_and_database():
    """Verify that deployment and database events generate structured, ranked causal hypotheses."""
    engine = HypothesisEngine()

    e_deploy = _make_event("e1", "deployment_finished", "Deployed release v3.4.0", resource="web-svc")
    e_db = _make_event("e2", "database_slow_query", "Lock timeout on users table", resource="db-master")

    hypotheses = engine.generate_hypotheses(
        situation_id="sit_hyp_1",
        events=[e_deploy, e_db],
        affected_resources=["web-svc", "db-master"],
    )

    assert len(hypotheses) >= 2
    causes = [h.candidate_cause for h in hypotheses]
    assert any("deployment" in c.lower() for c in causes)
    assert any("database" in c.lower() for c in causes)

    # Check diagnostic recommendations exist
    for h in hypotheses:
        assert len(h.recommended_diagnostics) > 0
        assert h.confidence_level in (
            CausalConfidence.SUPPORTED,
            CausalConfidence.LIKELY,
            CausalConfidence.VERIFIED,
        )


def test_empty_events_returns_root_cause_unknown():
    """Test Invariant 67 & 29: Unknown root cause is valid when telemetry is insufficient."""
    engine = HypothesisEngine()

    hypotheses = engine.generate_hypotheses(
        situation_id="sit_empty",
        events=[],
        affected_resources=[],
    )

    assert len(hypotheses) == 1
    assert hypotheses[0].candidate_cause == "ROOT_CAUSE_UNKNOWN"
    assert hypotheses[0].confidence_level == CausalConfidence.UNKNOWN


def test_attention_priority_scoring():
    """Test Invariant 73 & 74: Multi-factor attention scoring without automatic execution."""
    att_engine = AttentionEngine()

    crit_sit = Situation(
        situation_id="sit_crit",
        title="Critical Payment Outage",
        description="Payment processing down",
        status=SituationStatus.DETECTED,
        severity=SituationSeverity.CRITICAL,
        confidence=0.95,
        environment="production",
        affected_resources=["payment-gateway", "stripe-connector"],
        affected_plans=["q3_plan"],
        affected_goals=["goal_revenue"],
    )

    att_item = att_engine.score_attention(crit_sit)
    assert att_item.situation_id == "sit_crit"
    assert att_item.composite_priority >= 0.80
    assert att_item.requires_human_action is True

    # Low severity situation with no goal impact
    low_sit = Situation(
        situation_id="sit_low",
        title="Minor log notice",
        description="Non-critical log trace",
        status=SituationStatus.MONITORING,
        severity=SituationSeverity.INFO,
        confidence=0.90,
        environment="development",
    )

    low_att = att_engine.score_attention(low_sit)
    assert low_att.composite_priority < att_item.composite_priority
    assert low_att.requires_human_action is False


def test_flapping_detection_on_rapid_transitions():
    """Test Invariant 47: Flapping detection triggers when situation repeatedly oscillates status."""
    att_engine = AttentionEngine(flapping_threshold=3, flapping_window_seconds=60.0)

    sit_id = "sit_flap"
    # Transition 1
    assert not att_engine.record_transition_and_check_flapping(sit_id, SituationStatus.DETECTED)
    # Transition 2
    assert not att_engine.record_transition_and_check_flapping(sit_id, SituationStatus.RESOLVED)
    # Transition 3 -> Reopened rapidly -> triggers flapping alert
    assert att_engine.record_transition_and_check_flapping(sit_id, SituationStatus.DETECTED)
