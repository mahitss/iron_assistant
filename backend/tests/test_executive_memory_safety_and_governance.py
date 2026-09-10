"""Tests for Safety, Governance, Privacy, Secret Redaction, and Authoritative Supremacy."""

import pytest

from app.executive_memory.checkpoints import CheckpointManager
from app.executive_memory.next_actions import NextActionEngine
from app.executive_memory.open_loops import OpenLoopManager
from app.executive_memory.priorities import PriorityEngine
from app.executive_memory.privacy import ExecutivePrivacyGuard
from app.executive_memory.reconciliation import StateReconciler
from app.executive_memory.safety import ExecutiveSafetyGuard


def test_reconciliation_authoritative_systems_win():
    """INVARIANTS 123, 204: When conflict occurs between synthesized state and source systems, source systems win."""
    reconciler = StateReconciler()

    synthesized = {
        "status": "COMPLETED",
        "tasks": ["t1", "t2"],
        "active_goal": "Goal A",
    }
    authoritative = {
        "status": "ACTIVE",  # Source says still ACTIVE!
        "tasks": ["t1", "t2", "t3"],
        "active_goal": "Goal A",
    }

    report = reconciler.reconcile(
        scope_id="proj_1",
        synthesized_state=synthesized,
        authoritative_state=authoritative,
    )

    assert report.drift_detected is True
    assert "status" in report.discrepancies
    # Authoritative source state strictly wins
    assert report.reconciled_state["status"] == "ACTIVE"
    assert len(report.reconciled_state["tasks"]) == 3


def test_user_priority_and_intent_supremacy():
    """INVARIANTS 71 & 214: Explicit user priorities and intent strictly override algorithmic ranking."""
    priority_engine = PriorityEngine()

    open_loops = [
        {"loop_id": "l1", "priority": "LOW", "description": "Write docs", "due_at": None, "dependencies": []},
        {"loop_id": "l2", "priority": "HIGH", "description": "Fix memory leak", "due_at": None, "dependencies": []},
    ]

    # Learned/algorithmic ranking would put l2 first
    ranked = priority_engine.rank_loops(open_loops)
    assert ranked[0]["loop_id"] == "l2"

    # User explicitly overrides l1 to top priority
    user_overrides = {"l1": 1000}
    overridden = priority_engine.rank_loops(open_loops, user_overrides=user_overrides)
    assert overridden[0]["loop_id"] == "l1"

    # NextActionEngine intent supremacy
    open_loop_mgr = OpenLoopManager()
    open_loop_mgr.create_open_loop(description="Refactor DB schema", project_id="p1")
    next_action_engine = NextActionEngine(open_loop_mgr=open_loop_mgr)

    actions = next_action_engine.generate_from_open_loops(
        project_id="p1",
        explicit_user_intent="Stop all refactoring and run stress tests",
    )
    assert len(actions) == 1
    assert "Stop all refactoring and run stress tests" in actions[0].objective
    assert "Explicit user intent" in actions[0].rationale


def test_privacy_guard_and_secret_redaction():
    """INVARIANTS 107-112, 189-192: Cross-project isolation and secret redaction."""
    # Redaction
    text_with_secrets = "User deployed with bearer token sk_live_998877665544332211 and password=SuperSecretPassword123!"
    redacted = ExecutivePrivacyGuard.redact_secrets(text_with_secrets)
    assert "sk_live_" not in redacted
    assert "SuperSecretPassword123!" not in redacted
    assert "[REDACTED]" in redacted

    # Isolation check
    allowed = ExecutivePrivacyGuard.check_access(
        requester_user_id="user_alice",
        requester_project_id="proj_alice",
        target_project_id="proj_alice",
        target_user_id="user_alice",
    )
    assert allowed is True

    denied = ExecutivePrivacyGuard.check_access(
        requester_user_id="user_alice",
        requester_project_id="proj_alice",
        target_project_id="proj_bob",
        target_user_id="user_bob",
    )
    assert denied is False


def test_checkpoint_revalidation_before_resumption():
    """INVARIANTS 156-161: Resuming a checkpoint requires revalidating dependencies against current authoritative state."""
    ckpt_mgr = CheckpointManager()

    ckpt = ckpt_mgr.create_checkpoint(
        workflow_id="wf_migration",
        goal="Migrate DB to PostgreSQL",
        state={"step": 2, "records_transferred": 500},
        progress="50%",
        dependencies=["dep_db_online", "dep_token_valid"],
        authorization={"authorized_by": "admin", "scope": "migration"},
        next_step="Transfer remaining 500 records",
    )

    # Resumption fails if dependencies are missing from current state
    stale_state = {"dependencies_active": ["dep_db_online"]}  # missing dep_token_valid
    with pytest.raises(ValueError) as exc_info:
        ckpt_mgr.resume(ckpt.checkpoint_id, current_authoritative_state=stale_state)
    assert "Unsatisfied dependencies" in str(exc_info.value)

    # Resumption succeeds when dependencies are validated
    valid_state = {"dependencies_active": ["dep_db_online", "dep_token_valid"]}
    res = ckpt_mgr.resume(ckpt.checkpoint_id, current_authoritative_state=valid_state)
    assert res["status"] == "RESUMED"
    assert res["next_step"] == "Transfer remaining 500 records"
