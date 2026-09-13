"""Unit tests for individual governance intelligence engines (Task 78)."""

from __future__ import annotations

import pytest

from app.policy.authority import AuthorityManagerEngine
from app.policy.constitution import ConstitutionalEngine
from app.policy.escalation_detector import AuthorityEscalationDetector
from app.policy.goal_alignment import GoalAlignmentEngine
from app.policy.governance_schemas import (
    AuthorityLevel,
    GovernanceDecisionType,
    GovernanceReviewRequest,
    GovernanceState,
    PolicyTier,
    PrincipleName,
    PrincipleStrictness,
)
from app.policy.governance_state_machine import (
    GovernanceStateMachine,
    GovernanceTransitionError,
)
from app.policy.hierarchy import PolicyHierarchyEngine


# ==============================================================================
# ConstitutionalEngine Tests
# ==============================================================================

def test_constitutional_engine_defaults() -> None:
    """Verify default constitution loads all 11 canonical principles."""
    engine = ConstitutionalEngine()
    assert len(engine.constitution.principles) == 11
    p_safety = engine.get_principle(PrincipleName.SAFETY)
    assert p_safety is not None
    assert p_safety.strictness == PrincipleStrictness.MANDATORY
    assert p_safety.weight == 1.0


def test_constitutional_engine_evaluation_safe_vs_destructive() -> None:
    """Safe action yields 1.0 score; destructive+irreversible action flags violations."""
    engine = ConstitutionalEngine()

    # 1. Safe read
    score_safe, evals_safe, viols_safe = engine.evaluate_action(
        action="read_log",
        resource="app.log",
        risk_level="R1_LOW",
    )
    assert score_safe >= 0.95
    assert len(viols_safe) == 0

    # 2. Destructive and irreversible
    score_dest, evals_dest, viols_dest = engine.evaluate_action(
        action="delete_prod_database",
        resource="postgres_main",
        risk_level="R4_CRITICAL",
        is_irreversible=True,
        is_destructive=True,
    )
    assert score_dest < 0.80
    assert any("SAFETY" in v or "REVERSIBILITY" in v for v in viols_dest)


def test_constitutional_engine_update_principle() -> None:
    """Admin principle update adjusts weight and strictness."""
    engine = ConstitutionalEngine()
    ok = engine.update_principle(
        name=PrincipleName.TRANSPARENCY,
        weight=0.75,
        strictness=PrincipleStrictness.MANDATORY,
    )
    assert ok is True
    p = engine.get_principle(PrincipleName.TRANSPARENCY)
    assert p.weight == 0.75
    assert p.strictness == PrincipleStrictness.MANDATORY


# ==============================================================================
# AuthorityManagerEngine Tests
# ==============================================================================

def test_authority_manager_grants_and_resolution() -> None:
    """Validate issuing grants, scope matching, and explicit denial overriding."""
    mgr = AuthorityManagerEngine()

    mgr.issue_grant(
        subject_id="agent_db",
        authority_level=AuthorityLevel.PROJECT,
        allowed_scopes=["project_finance"],
        allowed_actions=["select_*", "insert_*"],
        denied_actions=["drop_*", "delete_*"],
    )

    # 1. Allowed action
    allowed, reason, level = mgr.check_authority(
        subject_id="agent_db",
        action="select_invoices",
        scope="project_finance",
        required_level=AuthorityLevel.LIMITED,
    )
    assert allowed is True
    assert level == AuthorityLevel.PROJECT

    # 2. Explicitly denied action
    denied, d_reason, _ = mgr.check_authority(
        subject_id="agent_db",
        action="drop_table_invoices",
        scope="project_finance",
    )
    assert denied is False
    assert "explicitly denied" in d_reason

    # 3. Out of scope
    denied_scope, s_reason, _ = mgr.check_authority(
        subject_id="agent_db",
        action="select_invoices",
        scope="unauthorized_project",
    )
    assert denied_scope is False


def test_authority_manager_least_privilege_analysis() -> None:
    """Least privilege identifies excessive permission requests."""
    mgr = AuthorityManagerEngine()

    rec = mgr.analyze_least_privilege(
        requested_permissions=["READ", "WRITE", "DESTRUCTIVE"],
        action="read_account_balance",
    )
    assert rec.reduction_possible is True
    assert "WRITE" in rec.excess_permissions_requested
    assert "DESTRUCTIVE" in rec.excess_permissions_requested
    assert rec.minimum_permissions_needed == ["READ"]
    assert rec.recommended_authority_level == AuthorityLevel.LIMITED


# ==============================================================================
# PolicyHierarchyEngine Tests
# ==============================================================================

def test_policy_hierarchy_higher_tier_precedence() -> None:
    """Higher-tier policy strictly overrides lower-tier policy."""
    candidates = [
        {
            "policy_id": "pol_workflow_allow",
            "tier": PolicyTier.WORKFLOW,
            "decision": GovernanceDecisionType.ALLOWED,
            "reason": "Workflow step allows execution",
        },
        {
            "policy_id": "pol_system_deny",
            "tier": PolicyTier.SYSTEM,
            "decision": GovernanceDecisionType.DENIED,
            "reason": "System root guardrail prohibits action",
        },
    ]

    win_decision, win_policy, conflicts = PolicyHierarchyEngine.resolve_conflicting_policies(candidates)
    assert win_decision == GovernanceDecisionType.DENIED
    assert win_policy["policy_id"] == "pol_system_deny"
    assert len(conflicts) > 0


def test_policy_hierarchy_tie_breaking_within_tier() -> None:
    """Within the same tier, DENIED beats REQUIRES_HUMAN and ALLOWED."""
    candidates = [
        {
            "policy_id": "pol_sec_allow",
            "tier": PolicyTier.SECURITY,
            "decision": GovernanceDecisionType.ALLOWED,
            "reason": "Sec rule A allows",
        },
        {
            "policy_id": "pol_sec_deny",
            "tier": PolicyTier.SECURITY,
            "decision": GovernanceDecisionType.DENIED,
            "reason": "Sec rule B denies",
        },
    ]

    win_decision, win_policy, _ = PolicyHierarchyEngine.resolve_conflicting_policies(candidates)
    assert win_decision == GovernanceDecisionType.DENIED
    assert win_policy["policy_id"] == "pol_sec_deny"


# ==============================================================================
# GovernanceStateMachine Tests
# ==============================================================================

def test_governance_state_machine_legal_and_illegal_transitions() -> None:
    """Validate 8-state lifecycle transition graph and error handling."""
    sm = GovernanceStateMachine

    # 1. Valid transitions
    s1 = sm.transition(GovernanceState.PENDING_REVIEW, GovernanceState.REQUIRES_HUMAN)
    assert s1 == GovernanceState.REQUIRES_HUMAN

    s2 = sm.transition(s1, GovernanceState.APPROVED)
    assert s2 == GovernanceState.APPROVED

    s3 = sm.transition(s2, GovernanceState.EXECUTABLE)
    assert s3 == GovernanceState.EXECUTABLE

    # 2. Illegal transition (PENDING_REVIEW directly to EXECUTABLE raises error)
    with pytest.raises(GovernanceTransitionError):
        sm.transition(GovernanceState.PENDING_REVIEW, GovernanceState.EXECUTABLE)

    # 3. Terminal state cannot transition anywhere
    with pytest.raises(GovernanceTransitionError):
        sm.transition(GovernanceState.DENIED, GovernanceState.APPROVED)


# ==============================================================================
# GoalAlignmentEngine Tests
# ==============================================================================

def test_goal_alignment_possible_not_permissible() -> None:
    """Ensure possible does not imply permissible under conflicting intent."""
    engine = GoalAlignmentEngine()

    # Destructive action with read-only user intent
    report = engine.evaluate_alignment(
        goal="Audit security config",
        action="delete_security_group",
        resource="sg-1234",
        user_intent="read_only security audit",
        is_destructive=True,
    )
    assert report.safety_aligned is False
    assert report.user_goals_aligned is False
    assert len(report.conflicts_detected) >= 2


# ==============================================================================
# AuthorityEscalationDetector Tests
# ==============================================================================

def test_escalation_detector_control_weakening_and_hammering() -> None:
    """Detect governance tampering and probe velocity hammering."""
    detector = AuthorityEscalationDetector(probe_threshold=3, window_seconds=60)

    # 1. Control weakening signature
    req_weaken = GovernanceReviewRequest(
        goal="Bypass test",
        action="disable_system_security_check",
        caller_id="agent_adversary",
        caller_authority=AuthorityLevel.LIMITED,
    )
    rep_weaken = detector.detect_escalation(req_weaken, AuthorityLevel.LIMITED)
    assert rep_weaken.is_escalation_attempt is True
    assert rep_weaken.bypass_technique == "CONTROL_WEAKENING"
    assert rep_weaken.severity == "CRITICAL"

    # 2. Probe hammering
    req_probe = GovernanceReviewRequest(
        goal="Probe test",
        action="access_secret",
        caller_id="agent_spammer",
        caller_authority=AuthorityLevel.LIMITED,
    )
    for _ in range(3):
        detector.record_attempt("agent_spammer", req_probe, denied=True)

    rep_probe = detector.detect_escalation(req_probe, AuthorityLevel.LIMITED)
    assert rep_probe.is_escalation_attempt is True
    assert rep_probe.bypass_technique == "PROBE_HAMMERING"
