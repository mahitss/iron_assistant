"""Unit tests for Policy Conflict Resolution, Scope Hierarchy, and Boundary Enforcement (Task 36, Specs 8, 9, 74, 75, 124, 129, 131)."""

import pytest
from app.policy.conflicts import ConflictResolver
from app.policy.schemas import (
    PolicyContext,
    PolicyDecisionType,
    PolicyRule,
    PolicyScope,
)
from app.policy.scope import ScopeHierarchyEvaluator


def test_deny_strictly_overrides_allow():
    allow_rule = PolicyRule(
        policy_id="allow-staging-deploy",
        name="Allow Staging Deploy",
        priority=10,
        decision=PolicyDecisionType.ALLOW,
    )
    deny_rule = PolicyRule(
        policy_id="deny-after-hours",
        name="Deny Deploy After Hours",
        priority=1,  # Lower priority number, but DENY strictly wins
        decision=PolicyDecisionType.DENY,
    )

    win_decision, win_rule, matched_ids = ConflictResolver.resolve([allow_rule, deny_rule])
    assert win_decision == PolicyDecisionType.DENY
    assert win_rule.policy_id == "deny-after-hours"
    assert "allow-staging-deploy" in matched_ids
    assert "deny-after-hours" in matched_ids


def test_decision_precedence_hierarchy():
    allow_rule = PolicyRule(
        policy_id="allow-rule",
        name="Allow Rule",
        priority=100,
        decision=PolicyDecisionType.ALLOW,
    )
    approval_rule = PolicyRule(
        policy_id="approval-rule",
        name="Approval Rule",
        priority=50,
        decision=PolicyDecisionType.REQUIRE_APPROVAL,
    )

    win_decision, win_rule, _ = ConflictResolver.resolve([allow_rule, approval_rule])
    assert win_decision == PolicyDecisionType.REQUIRE_APPROVAL
    assert win_rule.policy_id == "approval-rule"


def test_cross_user_boundary_default_deny():
    ctx = PolicyContext(
        user={"id": "user_alice", "role": "user"},
        target={"owner_id": "user_bob", "id": "doc_123"},
    )
    ok, err = ScopeHierarchyEvaluator.validate_cross_boundary_access(ctx)
    assert ok is False
    assert "Cross-user access denied" in err


def test_cross_user_admin_override():
    ctx = PolicyContext(
        user={"id": "user_admin", "role": "admin"},
        target={"owner_id": "user_bob", "id": "doc_123"},
    )
    ok, err = ScopeHierarchyEvaluator.validate_cross_boundary_access(ctx)
    assert ok is True
    assert err is None


def test_cross_project_boundary_default_deny():
    ctx = PolicyContext(
        user={"id": "user_1", "role": "developer"},
        project={"id": "project_alpha", "allowed_projects": []},
        target={"project_id": "project_beta", "id": "repo_456"},
    )
    ok, err = ScopeHierarchyEvaluator.validate_cross_boundary_access(ctx)
    assert ok is False
    assert "Cross-project access denied" in err


def test_task_scope_expansion_blocked():
    ctx = PolicyContext(
        task={
            "id": "task_123",
            "authorized_scope": {
                "allowed_resources": ["repo_alpha", "repo_docs"],
                "environments": ["development"],
            },
        },
        target={"repository": "repo_secret_finance"},
        environment="development",
    )
    ok, err = ScopeHierarchyEvaluator.validate_task_scope_expansion(ctx)
    assert ok is False
    assert "Scope expansion violation" in err


def test_task_environment_mismatch_blocked():
    ctx = PolicyContext(
        task={
            "id": "task_123",
            "authorized_scope": {
                "allowed_resources": ["repo_alpha"],
                "environments": ["development", "staging"],
            },
        },
        target={"repository": "repo_alpha"},
        environment="production",  # Attempting production without auth
    )
    ok, err = ScopeHierarchyEvaluator.validate_task_scope_expansion(ctx)
    assert ok is False
    assert "Task environment violation" in err
