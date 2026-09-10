"""Test suite for Reusable Workflow Learning, Heuristics, Policy Re-checks, and Boundaries (Task 52)."""

import pytest

from app.learning.heuristics import HeuristicManager, HeuristicPolicyInferenceError
from app.learning.schemas import GeneralizationScope
from app.learning.workflows import WorkflowManager, WorkflowPolicyViolationError


def test_workflow_registration_and_promotion_bounds():
    """INVARIANT 62-64: Reusable workflows require repeated verified success before promotion."""
    mgr = WorkflowManager()
    wf = mgr.register_workflow(
        name="Safe Deployment Pipeline",
        steps=[
            {"step": 1, "action": "run_tests"},
            {"step": 2, "action": "build_docker"},
            {"step": 3, "action": "deploy_staging"},
        ],
        preconditions=[{"check": "git_clean"}],
        expected_outcome={"deployed": True},
        verification={"health_check": 200},
        failure_modes=["network_timeout", "test_failure"],
    )

    assert wf.status == "CANDIDATE"
    assert wf.success_count == 0

    # Cannot promote with 0 successes
    with pytest.raises(ValueError, match="INVARIANT 64"):
        mgr.promote_workflow(wf.workflow_id, min_successes=3)

    # Record 3 successful executions
    for _ in range(3):
        mgr.record_execution_outcome(wf.workflow_id, was_successful=True)

    promoted = mgr.promote_workflow(wf.workflow_id, min_successes=3)
    assert promoted.status == "ACTIVE"
    assert promoted.success_count == 3


def test_workflow_deprecation_and_versioning():
    """INVARIANT 65 & 66: Workflows can evolve, be versioned, and be deprecated."""
    mgr = WorkflowManager()
    wf = mgr.register_workflow(
        name="Legacy Deploy",
        steps=[{"step": 1, "action": "scp_binary"}],
        version="0.9.0",
    )

    deprecated = mgr.deprecate_workflow(wf.workflow_id, reason="Migrated to Container Registry")
    assert deprecated.status == "DEPRECATED"
    assert any("Migrated to Container Registry" in mode for mode in deprecated.failure_modes)


def test_workflow_rechecks_current_active_policy():
    """INVARIANT 67: Stored workflow must re-check current active policy before execution."""
    mgr = WorkflowManager()
    wf = mgr.register_workflow(
        name="Cloud Infrastructure Cleanup",
        steps=[
            {"step": 1, "action": "inspect_buckets"},
            {"step": 2, "action": "delete_s3_bucket"},
        ],
    )

    # Simulated policy checker blocking destructive cloud deletions
    def strict_policy_checker(action_name: str) -> bool:
        if action_name == "delete_s3_bucket":
            return False  # Not allowed by current security policy
        return True

    with pytest.raises(WorkflowPolicyViolationError, match="INVARIANT 67"):
        mgr.validate_workflow_against_policy(wf.workflow_id, strict_policy_checker)


def test_heuristic_registration_requires_empirical_evidence():
    """INVARIANT 70: Heuristics must not be created without empirical evidence."""
    hm = HeuristicManager()
    with pytest.raises(ValueError, match="INVARIANT 70"):
        hm.register_heuristic(
            condition="modifying auth token",
            recommendation="run auth integration tests",
            evidence=[],
        )


def test_heuristic_never_infers_security_policy():
    """INVARIANT 73: The learning engine must never infer security or authorization policy."""
    hm = HeuristicManager()
    with pytest.raises(HeuristicPolicyInferenceError, match="INVARIANT 73"):
        hm.register_heuristic(
            condition="admin user login",
            recommendation="grant authorization policy bypass without approval",
            evidence=[{"log": "admin requested fast path"}],
        )


def test_heuristic_conflict_resolution_and_priority():
    """INVARIANT 71 & 72: Resolves heuristic conflicts by priority, verified confidence, and recency."""
    hm = HeuristicManager()
    h1 = hm.register_heuristic(
        condition="database migration postgres",
        recommendation="create snapshot backup before applying migration",
        evidence=[{"incident": "corrupted table restored from snapshot"}],
        confidence=0.85,
        priority=2,
    )
    h2 = hm.register_heuristic(
        condition="database migration postgres",
        recommendation="run migration with verbose logs only",
        evidence=[{"incident": "slow migration"}],
        confidence=0.6,
        priority=1,
    )

    resolved = hm.resolve_conflicts("Applying database migration postgres on production")
    assert len(resolved) == 2
    # Highest priority (h1) comes first
    assert resolved[0].heuristic_id == h1.heuristic_id
    assert resolved[1].heuristic_id == h2.heuristic_id
