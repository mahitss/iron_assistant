"""Unit tests for Situation Lifecycle, Blast Radius Impact, and False Recovery Defense (Task 60)."""

import pytest

from app.situational_awareness.engine import SituationalAwarenessEngine
from app.situational_awareness.impact import ImpactAnalyzer
from app.situational_awareness.safety import SituationalAwarenessSafetyError
from app.situational_awareness.schemas import (
    EventIngestRequest,
    SituationSeverity,
    SituationStatus,
    TaskImpactState,
)


def test_blast_radius_multi_hop_propagation_and_plan_impact():
    """Verify that impact propagates to downstream services and marks affected strategic plan tasks as BLOCKED or AT_RISK."""
    analyzer = ImpactAnalyzer()

    # Topology: auth-api depends on db-primary, payment-service depends on auth-api
    dep_map = {
        "auth-api": ["db-primary"],
        "payment-service": ["auth-api"],
    }

    active_plans = [
        {
            "plan_id": "plan_q3_checkout",
            "tasks": [
                {
                    "id": "task_payment_gateway",
                    "required_resources": [{"id": "auth-api"}],
                },
                {
                    "id": "task_analytics_batch",
                    "required_resources": [{"id": "data-lake"}],
                },
            ],
        }
    ]

    active_goals = [
        {
            "id": "goal_high_checkout_sla",
            "related_services": ["payment-service"],
        }
    ]

    impact = analyzer.calculate_blast_radius(
        situation_id="sit_test_1",
        affected_resources=["db-primary"],
        dependency_map=dep_map,
        active_plans=active_plans,
        active_goals=active_goals,
    )

    assert impact.known_affected_services == ["db-primary"]
    assert "auth-api" in impact.potentially_affected_services
    assert "payment-service" in impact.potentially_affected_services

    assert "plan_q3_checkout" in impact.affected_plans
    assert impact.task_impacts.get("task_payment_gateway") in (
        TaskImpactState.AT_RISK,
        TaskImpactState.BLOCKED,
    )
    assert impact.task_impacts.get("task_analytics_batch") == TaskImpactState.UNBLOCKED
    assert "goal_high_checkout_sla" in impact.affected_goals


def test_false_recovery_defense_blocks_unverified_resolution():
    """Test Invariant 8 & 44 & 124: Silence != Recovery. Situations CANNOT be closed without verification evidence."""
    engine = SituationalAwarenessEngine()

    req = EventIngestRequest(
        event_type="outage",
        source="prometheus",
        subject="Database connection failure",
        resource="db-primary",
        severity=SituationSeverity.CRITICAL,
    )
    res = engine.process_event(req)
    sit_id = res["situation_id"]

    # Attempt resolution with empty verification evidence -> must fail
    with pytest.raises(SituationalAwarenessSafetyError, match="False Recovery Defense"):
        engine.resolve_situation(sit_id, actor="ops_bot", verification_evidence={})

    # Attempt resolution with is_verified=False -> must fail
    with pytest.raises(SituationalAwarenessSafetyError, match="False Recovery Defense"):
        engine.resolve_situation(
            sit_id, actor="ops_bot", verification_evidence={"is_verified": False, "note": "alerts stopped"}
        )

    # Legitimate verified resolution
    sit = engine.resolve_situation(
        sit_id,
        actor="lead_sre",
        verification_evidence={
            "is_verified": True,
            "verification_task_id": "v_task_99",
            "check": "healthcheck_200",
        },
    )
    assert sit.status == SituationStatus.RESOLVED


def test_severity_escalation_on_higher_severity_event():
    """Verify that an active situation escalates severity when a higher severity event arrives."""
    engine = SituationalAwarenessEngine()

    # Initial LOW event
    req_low = EventIngestRequest(
        event_type="warning",
        source="monitor",
        subject="Memory usage high",
        resource="app-pod-1",
        severity=SituationSeverity.LOW,
    )
    res1 = engine.process_event(req_low)
    sit_id = res1["situation_id"]
    assert res1["severity"] == SituationSeverity.LOW.value

    # Subsequent CRITICAL event on the same resource
    req_crit = EventIngestRequest(
        event_type="alert",
        source="monitor",
        subject="OOM Kill occurred",
        resource="app-pod-1",
        severity=SituationSeverity.CRITICAL,
    )
    res2 = engine.process_event(req_crit)
    assert res2["situation_id"] == sit_id
    assert res2["severity"] == SituationSeverity.CRITICAL.value
