"""Unit tests for Blameless Postmortems and Cross-Engine Learning Dispatch (Task 61)."""

from app.incident_response.learning import IncidentLearningEngine
from app.incident_response.postmortem import PostmortemEngine
from app.incident_response.schemas import (
    CausalHypothesisItem,
    HypothesisStatus,
    IncidentActionItem,
    IncidentResponse,
    IncidentSeverity,
    IncidentStatus,
)


def test_blameless_postmortem_distinguishes_root_cause_and_contributing_factors():
    """Test Invariant 90-95: Postmortem separates root cause from contributing factors and formulates preventive tasks."""
    engine = PostmortemEngine()

    hyp = CausalHypothesisItem(
        hypothesis_id="hyp_verified_1",
        candidate_cause="Memory leak in auth token serializer",
        status=HypothesisStatus.VERIFIED,
        confidence=0.92,
    )

    action_ok = IncidentActionItem(
        action_id="act_1",
        incident_id="inc_pm_01",
        action_type="ROLLBACK",
        title="Rollback token serializer commit",
        status="COMPLETED",
    )

    inc = IncidentResponse(
        incident_id="inc_pm_01",
        title="Auth service memory exhaustion",
        environment="production",
        severity=IncidentSeverity.HIGH,
        status=IncidentStatus.RESOLVED,
        affected_resources=["auth-pod-1", "auth-pod-2", "auth-pod-3"],
        affected_services=["auth-service", "gateway"],
        affected_goals=["goal_99_9_uptime"],
        hypotheses=[hyp],
        actions=[action_ok],
    )

    pm = engine.generate_postmortem(inc)

    assert pm.incident_id == "inc_pm_01"
    assert pm.root_cause == "Memory leak in auth token serializer"
    assert len(pm.contributing_factors) >= 1
    assert any("coupling" in f.lower() or "contention" in f.lower() for f in pm.contributing_factors)
    assert len(pm.what_worked) >= 2
    assert len(pm.action_items) >= 2
    assert len(pm.lessons_learned) >= 1


def test_postmortem_with_root_cause_unknown_avoids_forced_blame():
    """Test Invariant 92 & 93: When root cause is unverified, postmortem explicitly states ROOT_CAUSE_UNKNOWN."""
    engine = PostmortemEngine()

    inc = IncidentResponse(
        incident_id="inc_pm_unk",
        title="Transient latency jitter",
        environment="production",
        severity=IncidentSeverity.MEDIUM,
        status=IncidentStatus.RESOLVED,
        hypotheses=[],
        actions=[],
    )

    pm = engine.generate_postmortem(inc)
    assert pm.root_cause == "ROOT_CAUSE_UNKNOWN"


def test_learning_dispatch_formats_feedback_for_decision_and_planning():
    """Test Invariant 96-98: Postmortem learnings dispatch feedback to Decision Engine and Planning."""
    postmortem_eng = PostmortemEngine()
    learning_eng = IncidentLearningEngine()

    inc = IncidentResponse(
        incident_id="inc_learn_01",
        title="Cache node failure",
        environment="production",
        severity=IncidentSeverity.HIGH,
        status=IncidentStatus.RESOLVED,
        selected_option_id="opt_scale",
        affected_plans=["plan_q3_infrastructure"],
    )
    pm = postmortem_eng.generate_postmortem(inc)

    dispatch_res = learning_eng.dispatch_learnings(inc, pm)

    assert dispatch_res["is_dispatched"] is True
    assert dispatch_res["decision_feedback"]["was_successful"] is True
    assert len(dispatch_res["planning_proposals"]) >= 1
    assert dispatch_res["planning_proposals"][0]["target_plan_id"] == "plan_q3_infrastructure"
    assert dispatch_res["memory_record"]["incident_id"] == "inc_learn_01"
