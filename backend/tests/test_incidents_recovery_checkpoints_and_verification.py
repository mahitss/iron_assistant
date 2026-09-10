"""Unit tests for Phased Recovery Plans, Checkpoint Barriers, and False Recovery Defense (Task 61)."""

import pytest

from app.incident_response.checkpoints import CheckpointManager
from app.incident_response.engine import IncidentResponseEngine
from app.incident_response.recovery import RecoveryEngine
from app.incident_response.safety import IncidentResponseSafetyError
from app.incident_response.schemas import (
    IncidentStatus,
    RecoveryState,
)


def test_recovery_plan_generation_and_checkpoints():
    """Verify recovery plan is generated with sequential steps and verification checkpoints."""
    engine = RecoveryEngine()

    plan = engine.build_recovery_plan(
        incident_id="inc_rec_01",
        strategy="rollback",
        target_resource="checkout-svc",
    )

    assert plan.incident_id == "inc_rec_01"
    assert plan.strategy == "rollback"
    assert plan.status == RecoveryState.NOT_STARTED
    assert len(plan.steps) == 2
    assert len(plan.checkpoints) == 2
    assert plan.current_step_index == 0


def test_checkpoint_verification_barrier_enforcement():
    """Test Invariant 43: Verification barrier must pass before advancing recovery steps."""
    rec_engine = RecoveryEngine()
    chk_mgr = CheckpointManager()

    plan = rec_engine.build_recovery_plan("inc_rec_02", "scale", "auth-api")
    chk1_id = plan.checkpoints[0].checkpoint_id

    # 1. Attempt verification with empty/failed evidence -> rejected
    passed, msg = chk_mgr.verify_checkpoint(plan, chk1_id, verification_evidence={"is_verified": False})
    assert passed is False
    assert "Verification criteria not satisfied" in msg
    assert plan.current_step_index == 0
    assert plan.status != RecoveryState.RECOVERED

    # 2. Provide valid verified evidence -> succeeds and advances step
    passed2, msg2 = chk_mgr.verify_checkpoint(
        plan,
        chk1_id,
        verification_evidence={"is_verified": True, "healthy_replicas": 5},
    )
    assert passed2 is True
    assert plan.checkpoints[0].is_passed is True
    assert plan.current_step_index == 1
    assert plan.status == RecoveryState.RECOVERED


def test_anti_blind_recovery_pauses_on_environmental_drift():
    """Test Invariant 44 & 45: Environmental drift pauses recovery plan execution for revalidation."""
    rec_engine = RecoveryEngine()
    chk_mgr = CheckpointManager()

    plan = rec_engine.build_recovery_plan("inc_drift", "rollback", "cart-svc")
    chk1_id = plan.checkpoints[0].checkpoint_id

    # Environmental drift detected
    passed, msg = chk_mgr.verify_checkpoint(
        plan,
        chk1_id,
        verification_evidence={"is_verified": True},
        environmental_drift=True,
    )

    assert passed is False
    assert "drift detected" in msg
    assert plan.status == RecoveryState.PARTIAL


def test_false_recovery_defense_on_incident_resolution():
    """Test Invariant 8 & 10: Alerts disappearing alone does not resolve an incident without verified evidence."""
    engine = IncidentResponseEngine()

    situation = {
        "situation_id": "sit_res_test",
        "title": "Outage on order-db",
        "environment": "production",
        "severity": "HIGH",
        "affected_resources": ["order-db"],
    }
    inc = engine.create_incident_from_situation(situation)

    # Attempt resolution without verification -> must raise error
    with pytest.raises(IncidentResponseSafetyError, match="False Recovery Defense"):
        engine.resolve_incident(inc.incident_id, actor="ops_bot", verification_evidence={})

    with pytest.raises(IncidentResponseSafetyError, match="False Recovery Defense"):
        engine.resolve_incident(
            inc.incident_id, actor="ops_bot", verification_evidence={"is_verified": False, "note": "quiet"}
        )

    # Legitimate verified resolution
    resolved = engine.resolve_incident(
        inc.incident_id,
        actor="lead_sre",
        verification_evidence={"is_verified": True, "check": "e2e_healthcheck_ok"},
        resolution_notes="Full recovery verified across pods",
    )
    assert resolved.status == IncidentStatus.RESOLVED
    assert resolved.resolved_at is not None
    assert resolved.postmortem is not None


def test_reopen_incident_on_recurrence():
    """Test Invariant 87: Recurrence reopens incident back to INVESTIGATING status."""
    engine = IncidentResponseEngine()

    situation = {
        "situation_id": "sit_reopen_test",
        "title": "Intermittent packet drop",
        "environment": "production",
        "severity": "MEDIUM",
        "affected_resources": ["gateway-1"],
    }
    inc = engine.create_incident_from_situation(situation)
    engine.resolve_incident(
        inc.incident_id,
        actor="sre",
        verification_evidence={"is_verified": True},
    )
    assert inc.status == IncidentStatus.RESOLVED

    # Recurrence occurs
    reopened = engine.reopen_incident(inc.incident_id, actor="monitor", reason="Packet drop resumed")
    assert reopened.status == IncidentStatus.INVESTIGATING
    assert reopened.resolved_at is None
