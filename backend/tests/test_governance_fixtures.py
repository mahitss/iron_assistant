"""12 Synthetic test fixtures and environments for Autonomous Governance,
Constitutional Reasoning, Policy Intelligence & Authority Management Engine (Task 78).
"""

from __future__ import annotations

from typing import Any

from app.policy.authority import AuthorityManagerEngine
from app.policy.constitution import ConstitutionalEngine
from app.policy.escalation_detector import AuthorityEscalationDetector
from app.policy.goal_alignment import GoalAlignmentEngine
from app.policy.governance_coordinator import GovernanceIntelligenceCoordinator
from app.policy.governance_schemas import (
    AuthorityLevel,
    GovernanceDecisionType,
    GovernanceReviewRequest,
    GovernanceState,
    PolicyTier,
    PrincipleName,
    PrincipleStrictness,
)
from app.policy.governance_state_machine import GovernanceStateMachine
from app.policy.hierarchy import PolicyHierarchyEngine
from app.security.emergency_stop import EmergencyStopService


def create_fixture_benign_read() -> tuple[GovernanceIntelligenceCoordinator, GovernanceReviewRequest]:
    """Fixture 1: Safe read-only request with appropriate limited authority."""
    auth = AuthorityManagerEngine()
    auth.issue_grant(
        subject_id="agent_reader",
        authority_level=AuthorityLevel.LIMITED,
        allowed_actions=["read_*", "fetch_*", "get_*"],
    )
    coord = GovernanceIntelligenceCoordinator(authority_manager=auth)
    req = GovernanceReviewRequest(
        goal="Fetch system telemetry",
        action="read_telemetry",
        resource="telemetry_log",
        caller_id="agent_reader",
        caller_authority=AuthorityLevel.LIMITED,
        risk_level="R1_LOW",
        required_permissions=["READ"],
    )
    return coord, req


def create_fixture_emergency_stop() -> tuple[GovernanceIntelligenceCoordinator, GovernanceReviewRequest, EmergencyStopService]:
    """Fixture 2: System where global emergency stop has been activated."""
    es = EmergencyStopService()
    es.trigger_emergency_stop(reason="Unit test emergency halt")
    coord = GovernanceIntelligenceCoordinator()
    req = GovernanceReviewRequest(
        goal="Deploy production update",
        action="deploy_service",
        caller_id="deployer_agent",
        caller_authority=AuthorityLevel.PROJECT,
        risk_level="R2_MODERATE",
    )
    return coord, req, es


def create_fixture_privilege_creep() -> tuple[GovernanceIntelligenceCoordinator, GovernanceReviewRequest]:
    """Fixture 3: Limited actor attempting a high-risk destructive action."""
    auth = AuthorityManagerEngine()
    auth.issue_grant(
        subject_id="agent_junior",
        authority_level=AuthorityLevel.LIMITED,
        allowed_actions=["read_*"],
    )
    coord = GovernanceIntelligenceCoordinator(authority_manager=auth)
    req = GovernanceReviewRequest(
        goal="Purge old user records",
        action="delete_all_records",
        resource="db_users",
        caller_id="agent_junior",
        caller_authority=AuthorityLevel.LIMITED,
        risk_level="R3_HIGH",
        is_destructive=True,
        required_permissions=["READ", "WRITE", "DESTRUCTIVE"],
    )
    return coord, req


def create_fixture_high_uncertainty_irreversible() -> tuple[GovernanceIntelligenceCoordinator, GovernanceReviewRequest]:
    """Fixture 4: High uncertainty (0.85) combined with irreversible action requiring human oversight."""
    coord = GovernanceIntelligenceCoordinator()
    coord.authority_manager.issue_grant(
        subject_id="lead_operator",
        authority_level=AuthorityLevel.ADMIN,
        allowed_actions=["*"],
    )
    req = GovernanceReviewRequest(
        goal="Migrate cluster partition topology",
        action="repartition_cluster",
        resource="cluster_nodes",
        caller_id="lead_operator",
        caller_authority=AuthorityLevel.ADMIN,
        risk_level="R3_HIGH",
        is_irreversible=True,
        uncertainty_score=0.85,
    )
    return coord, req


def create_fixture_probe_hammering() -> tuple[GovernanceIntelligenceCoordinator, GovernanceReviewRequest]:
    """Fixture 5: Caller attempting repeated denied actions in rapid succession."""
    detector = AuthorityEscalationDetector(probe_threshold=3, window_seconds=60)
    auth = AuthorityManagerEngine()
    auth.issue_grant(
        subject_id="agent_probe",
        authority_level=AuthorityLevel.LIMITED,
        denied_actions=["restricted_*"],
    )
    coord = GovernanceIntelligenceCoordinator(
        authority_manager=auth,
        escalation_detector=detector,
    )
    # Pre-record 3 denials
    dummy_req = GovernanceReviewRequest(
        goal="Probe boundary",
        action="restricted_call",
        caller_id="agent_probe",
        caller_authority=AuthorityLevel.LIMITED,
    )
    for _ in range(3):
        detector.record_attempt("agent_probe", dummy_req, denied=True)

    test_req = GovernanceReviewRequest(
        goal="Probe again",
        action="restricted_call_v4",
        caller_id="agent_probe",
        caller_authority=AuthorityLevel.LIMITED,
    )
    return coord, test_req


def create_fixture_control_weakening() -> tuple[GovernanceIntelligenceCoordinator, GovernanceReviewRequest]:
    """Fixture 6: Direct attempt to weaken or disable governance controls."""
    coord = GovernanceIntelligenceCoordinator()
    req = GovernanceReviewRequest(
        goal="Speed up workflow",
        action="bypass_approval_and_disable_security",
        caller_id="agent_sneaky",
        caller_authority=AuthorityLevel.LIMITED,
    )
    return coord, req


def create_fixture_multi_tier_conflict() -> tuple[GovernanceIntelligenceCoordinator, GovernanceReviewRequest]:
    """Fixture 7: Direct conflict between SYSTEM tier DENY and WORKFLOW tier ALLOW."""
    coord = GovernanceIntelligenceCoordinator()
    coord.register_policy(
        policy_id="sys_pol_deny_drop",
        tier=PolicyTier.SYSTEM,
        action="drop_table",
        decision=GovernanceDecisionType.DENIED,
        reason="System tier prohibits raw table drops.",
    )
    coord.register_policy(
        policy_id="wf_pol_allow_drop",
        tier=PolicyTier.WORKFLOW,
        action="drop_table",
        decision=GovernanceDecisionType.ALLOWED,
        reason="Workflow tier allows table drop for cleanup.",
    )
    req = GovernanceReviewRequest(
        goal="Clean up temp table",
        action="drop_table",
        caller_id="system_admin",
        caller_authority=AuthorityLevel.ADMIN,
    )
    return coord, req


def create_fixture_self_approval_attempt() -> tuple[GovernanceIntelligenceCoordinator, str]:
    """Fixture 8: Pre-seeded review in REQUIRES_HUMAN state."""
    coord = GovernanceIntelligenceCoordinator()
    req = GovernanceReviewRequest(
        goal="Irreversible mutation",
        action="destructive_cleanup",
        caller_id="agent_worker",
        caller_authority=AuthorityLevel.PROJECT,
        is_irreversible=True,
        is_destructive=True,
    )
    import asyncio
    res = asyncio.run(coord.evaluate_review(req))
    return coord, res.review_id


def create_fixture_least_privilege_reduction() -> tuple[AuthorityManagerEngine, list[str], str]:
    """Fixture 9: Excess permissions requested for a read-only query."""
    auth = AuthorityManagerEngine()
    requested = ["READ", "WRITE", "DESTRUCTIVE", "ADMIN"]
    action = "read_configuration_file"
    return auth, requested, action


def create_fixture_state_machine_transitions() -> type[GovernanceStateMachine]:
    """Fixture 10: Governance state machine for transition validation."""
    return GovernanceStateMachine


def create_fixture_goal_divergence() -> tuple[GoalAlignmentEngine, dict[str, Any]]:
    """Fixture 11: Destructive action performed when user requested read-only inspection."""
    engine = GoalAlignmentEngine()
    params = {
        "goal": "Inspect system logs",
        "action": "delete_all_logs",
        "resource": "system_logs",
        "user_intent": "read_only audit of system logs",
        "is_destructive": True,
        "is_irreversible": True,
    }
    return engine, params


def create_fixture_human_resolution_lifecycle() -> tuple[GovernanceIntelligenceCoordinator, GovernanceReviewRequest]:
    """Fixture 12: Complete lifecycle: Review -> REQUIRES_HUMAN -> Human Approval -> EXECUTABLE."""
    coord = GovernanceIntelligenceCoordinator()
    req = GovernanceReviewRequest(
        goal="High uncertainty research exploration",
        action="execute_novel_counterfactual",
        caller_id="research_agent",
        caller_authority=AuthorityLevel.PROJECT,
        uncertainty_score=0.90,
    )
    return coord, req
