"""Tests for Autonomy Levels, Anti-Self-Modification, Governance Policies, and Replanning (Task 45)."""

import pytest
from app.autonomy.policies import AutonomyPolicyEngine, DomainWorkflowType, PolicyDeniedError
from app.autonomy.replanning import PlanDiff, ReplanningManager
from app.autonomy.safety import (
    ActionClassification,
    AutonomyLevel,
    AutonomySafetyGuard,
    SafetyViolationError,
)


def test_autonomy_level_and_action_gating():
    """Verify action gating across autonomy levels: ASSISTED, SUPERVISED, CONDITIONAL, AUTONOMOUS (Spec 134-143)."""
    # 1. READ and ANALYZE are always permitted
    assert AutonomySafetyGuard.validate_action_against_autonomy_level(ActionClassification.READ, AutonomyLevel.ASSISTED) is True
    assert AutonomySafetyGuard.validate_action_against_autonomy_level(ActionClassification.ANALYZE, AutonomyLevel.ASSISTED) is True

    # 2. ASSISTED blocks WRITE without pre-approval (Spec 135)
    with pytest.raises(SafetyViolationError, match="blocked under ASSISTED"):
        AutonomySafetyGuard.validate_action_against_autonomy_level(ActionClassification.WRITE, AutonomyLevel.ASSISTED, is_pre_approved=False)

    assert AutonomySafetyGuard.validate_action_against_autonomy_level(ActionClassification.WRITE, AutonomyLevel.ASSISTED, is_pre_approved=True) is True

    # 3. SUPERVISED allows WRITE but blocks DEPLOY/DELETE without pre-approval (Spec 136)
    assert AutonomySafetyGuard.validate_action_against_autonomy_level(ActionClassification.WRITE, AutonomyLevel.SUPERVISED) is True
    with pytest.raises(SafetyViolationError, match="requires explicit human approval under SUPERVISED"):
        AutonomySafetyGuard.validate_action_against_autonomy_level(ActionClassification.DEPLOY, AutonomyLevel.SUPERVISED, is_pre_approved=False)

    # 4. AUTONOMOUS blocks unapproved PRIVILEGED actions (Spec 138, 139)
    with pytest.raises(SafetyViolationError, match="PRIVILEGED actions cannot be executed autonomously"):
        AutonomySafetyGuard.validate_action_against_autonomy_level(ActionClassification.PRIVILEGED, AutonomyLevel.AUTONOMOUS, is_pre_approved=False)


def test_anti_self_modification_protection():
    """Verify that Kairo cannot modify its own security, safety, or governance code (Spec 191, 195)."""
    # 1. Block modifications targeting protected system directories
    with pytest.raises(SafetyViolationError, match="ANTI-SELF-MODIFICATION BLOCKED"):
        AutonomySafetyGuard.validate_anti_self_modification(
            target_resource="backend/app/security/jwt.py",
            proposed_change="def verify_token(): return True",
        )

    with pytest.raises(SafetyViolationError, match="ANTI-SELF-MODIFICATION BLOCKED"):
        AutonomySafetyGuard.validate_anti_self_modification(
            target_resource="app/policy/enforcer.py",
            proposed_change="allow_all = True",
        )

    # 2. Block prohibited privilege escalation phrases
    with pytest.raises(SafetyViolationError, match="Prohibited directive"):
        AutonomySafetyGuard.validate_anti_self_modification(
            target_resource="scripts/worker.py",
            proposed_change="disable security checks for this session",
        )


def test_policy_fail_closed_principles():
    """Verify fail-closed governance when policy or security services are unavailable (Spec 176-179)."""
    # 1. Degraded read-only is allowed (Spec 180)
    pe_down = AutonomyPolicyEngine(policy_service_available=False, security_service_available=False)
    assert pe_down.evaluate_action_policy(ActionClassification.READ, "docs/readme.md", {}) is True

    # 2. Consequential operations fail-closed when policy service is down
    with pytest.raises(PolicyDeniedError, match="Fail-closed principle denies consequential operation"):
        pe_down.evaluate_action_policy(ActionClassification.WRITE, "src/index.js", {"content": "update"})

    # 3. Security checks down -> fail closed
    pe_sec_down = AutonomyPolicyEngine(policy_service_available=True, security_service_available=False)
    with pytest.raises(PolicyDeniedError, match="Security checks unavailable"):
        pe_sec_down.evaluate_action_policy(ActionClassification.DEPLOY, "cluster/prod", {})


def test_domain_workflow_policies():
    """Verify domain workflow constraints for coding, deployment, and deletion (Spec 181-190)."""
    pe = AutonomyPolicyEngine()

    # Coding requires prior test plan (Spec 182)
    with pytest.raises(PolicyDeniedError, match="requires pre-defined test and review plan"):
        pe.validate_domain_workflow(DomainWorkflowType.CODING, {"is_modification": True, "has_prior_test_plan": False})

    # Deployment requires rollback strategy and health check (Spec 184)
    with pytest.raises(PolicyDeniedError, match="requires a verified rollback strategy"):
        pe.validate_domain_workflow(DomainWorkflowType.DEPLOYMENT, {"has_rollback_strategy": False})

    # Wide deletion prohibited (Spec 190)
    with pytest.raises(PolicyDeniedError, match="Prohibited wide deletion target"):
        pe.validate_domain_workflow(DomainWorkflowType.DELETION, {"target_resource": "/"})


def test_adaptive_replanning_and_diffs():
    """Verify plan diff calculation, plan versioning, and approval invalidation (Spec 73-80)."""
    rm = ReplanningManager(materiality_threshold=1)
    old_steps = [{"step_id": "step_1", "action": "read"}, {"step_id": "step_2", "action": "write"}]
    new_steps = [
        {"step_id": "step_1", "action": "read"},
        {"step_id": "step_3", "action": "validate"},
        {"step_id": "step_2", "action": "write"},
    ]

    diff = rm.calculate_plan_diff(old_steps, new_steps)
    assert "step_3" in diff.added_steps
    assert diff.is_material_change is True

    new_v, fresh_approval_needed = rm.create_replan_version(current_version=1, diff=diff)
    assert new_v == 2
    assert fresh_approval_needed is True
