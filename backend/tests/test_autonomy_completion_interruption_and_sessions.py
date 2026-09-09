"""Tests for Completion Records, Interruption Cascades, Tenant Isolation, and Append-Only Journal (Task 45)."""

import pytest
from app.autonomy.engine import (
    AutonomousExecutionEngine,
    FalseCompletionError,
)
from app.autonomy.interruption import InterruptionHandler
from app.autonomy.persistence import AutonomyPersistenceManager, JournalTamperingError
from app.autonomy.sessions import (
    AutonomousScope,
    AutonomousSession,
    ScopeViolationError,
    TenantIsolationError,
)
from app.autonomy.state import AutonomousRunState


def test_false_completion_prevention_and_completion_record():
    """Verify that runs cannot be completed without verified proof for all success criteria (Spec 154-156)."""
    engine = AutonomousExecutionEngine()

    goal = engine.goal_manager.register_goal(
        title="Deploy microservice with 100% test coverage",
        description="Run unit tests, verify integration, deploy to staging.",
        user_id="user_alice",
        success_criteria=["Unit tests pass", "Integration tests pass", "Health check OK"],
    )

    run = engine.create_run(goal_id=goal.goal_id, owner_user_id="user_alice")

    # Attempting completion with incomplete verification -> FalseCompletionError
    with pytest.raises(FalseCompletionError, match="success criteria required, but only 1 verified"):
        engine.complete_run(
            run_id=run.run_id,
            verification_results=["Unit tests pass verified"],
            evidence_refs=["ev_unit_1"],
        )

    # Valid completion with all 3 criteria verified
    record = engine.complete_run(
        run_id=run.run_id,
        verification_results=[
            "Unit tests pass verified (142/142)",
            "Integration tests pass verified (18/18)",
            "Health check OK verified (HTTP 200)",
        ],
        evidence_refs=["ev_unit_1", "ev_integ_2", "ev_health_3"],
    )
    assert record.record_id.startswith("comp_")
    assert run.status == AutonomousRunState.COMPLETED
    assert run.progress_pct == 100.0


def test_interruption_handling_and_emergency_stop_cascade():
    """Verify safe pause, cancellation, and emergency stop cascading to child tasks (Spec 65-71, 111-113)."""
    ih = InterruptionHandler()

    child_halted = False

    def child_hook():
        nonlocal child_halted
        child_halted = True

    ih.register_child_hook(child_hook)

    # 1. Pause request
    ih.request_pause()
    assert ih.should_pause is True
    assert ih.should_halt_immediately is False
    assert child_halted is False

    # 2. Emergency stop request immediately halts and cascades
    ih.trigger_emergency_stop("Critical security invariant breached")
    assert ih.should_halt_immediately is True
    assert child_halted is True
    assert "Critical security invariant" in (ih.stop_reason or "")


def test_tenant_isolation_and_scope_locks():
    """Verify strict cross-user/project isolation and scope locks (Spec 4, 144, 145, 196)."""
    scope = AutonomousScope(
        allowed_directories=["src/components", "src/utils"],
        allowed_domains=["api.github.com", "crates.io"],
    )
    session = AutonomousSession(
        session_id="sess_001",
        user_id="user_alice",
        project_id="proj_kairo",
        goal_id="goal_001",
        scope=scope,
    )

    # 1. Tenant isolation: Different user rejected
    with pytest.raises(TenantIsolationError, match="Session belongs to user 'user_alice'"):
        session.validate_tenant_access(requesting_user_id="user_bob", requesting_project_id="proj_kairo")

    # 2. Tenant isolation: Different project rejected
    with pytest.raises(TenantIsolationError, match="Session belongs to project 'proj_kairo'"):
        session.validate_tenant_access(requesting_user_id="user_alice", requesting_project_id="proj_other")

    # 3. Same user & project accepted
    session.validate_tenant_access(requesting_user_id="user_alice", requesting_project_id="proj_kairo")

    # 4. Scope lock: allowed directory vs forbidden directory
    assert scope.validate_resource_in_scope("src/components/button.js") is True
    assert scope.validate_resource_in_scope("backend/secrets/keys.pem") is False

    # 5. Scope lock: allowed domain vs forbidden domain
    assert scope.validate_domain_in_scope("api.github.com") is True
    assert scope.validate_domain_in_scope("evil-exfil-server.com") is False


def test_context_compaction_no_information_loss():
    """Verify that context compaction never discards security, approvals, or verifications (Spec 127, 128)."""
    session = AutonomousSession(session_id="sess_002", user_id="u1", project_id="p1", goal_id="g1")
    session.record_security_decision("tool_read", True, "Read-only permitted")
    session.record_approval("appr_01", "write_file", "operator", True)
    session.record_failure("step_5", "timeout", "network")

    summary = session.compact_context(["Thought 1: inspect files", "Thought 2: parse ast", "Thought 3: generate plan"])
    assert "Invariants:" in summary
    assert "Security checks passed: 1" in summary
    assert "Approvals: 1" in summary
    assert "Failures recorded: 1" in summary


def test_append_only_journal_immutability():
    """Verify execution journal immutability and anti-tampering defenses (Spec 129, 130)."""
    pm = AutonomyPersistenceManager()
    run_id = "run_jrn_01"

    e1 = pm._in_memory_journals.setdefault(run_id, [])
    e1.append({"id": "j1", "event_type": "RUN_STARTED", "payload": {}, "sequence_num": 1})
    e1.append({"id": "j2", "event_type": "STEP_COMPLETED", "payload": {"step": 1}, "sequence_num": 2})

    # Tampering: truncating journal raises JournalTamperingError
    with pytest.raises(JournalTamperingError, match="truncated or deleted"):
        pm.assert_journal_immutability(run_id, [{"id": "j1", "event_type": "RUN_STARTED", "payload": {}}])

    # Tampering: rewriting historical event raises JournalTamperingError
    with pytest.raises(JournalTamperingError, match="was modified"):
        pm.assert_journal_immutability(
            run_id,
            [
                {"id": "j1", "event_type": "RUN_STARTED", "payload": {}},
                {"id": "j2", "event_type": "FORGED_EVENT", "payload": {"step": 1}},
            ],
        )
