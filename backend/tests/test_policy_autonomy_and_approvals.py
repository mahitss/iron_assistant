"""Unit tests for Autonomy Budgets, Approval Bridges, Auth Freshness, and Data Classification (Task 36, Specs 48-63, 127, 128, 143-146)."""

from datetime import UTC, datetime, timedelta
import pytest
from app.policy.approvals import PolicyApprovalBridge
from app.policy.authentication import AuthFreshnessChecker
from app.policy.autonomy import AutonomyGovernor
from app.policy.data_access import DataAccessController
from app.policy.schemas import PolicyContext, PolicyDecisionType, RiskLevel


def test_tool_call_budget_exceeded_defers():
    ctx = PolicyContext(
        task={
            "id": "task_123",
            "tool_calls_count": 50,
            "budget": {"max_tool_calls": 50},
        }
    )
    dec, err, constraints = AutonomyGovernor.evaluate_task_limits(ctx)
    assert dec == PolicyDecisionType.DEFER
    assert "exceeded tool-call budget" in err
    assert constraints.get("budget_exceeded") == "tool_calls"


def test_task_duration_budget_exceeded_defers():
    ctx = PolicyContext(
        task={
            "id": "task_123",
            "duration_seconds": 4000,
            "budget": {"max_duration_seconds": 3600},
        }
    )
    dec, err, _ = AutonomyGovernor.evaluate_task_limits(ctx)
    assert dec == PolicyDecisionType.DEFER
    assert "exceeded maximum permitted run duration" in err


def test_automation_execution_limit_denies():
    ctx = PolicyContext(
        task={
            "id": "task_cron_1",
            "automation": {
                "execution_count": 100,
                "max_executions": 100,
            },
        }
    )
    dec, err, _ = AutonomyGovernor.evaluate_task_limits(ctx)
    assert dec == PolicyDecisionType.DENY
    assert "Automation execution limit reached" in err


def test_task_replanning_cannot_expand_scope():
    ctx = PolicyContext(
        task={
            "id": "task_123",
            "is_replanning": True,
            "attempting_scope_expansion": True,
        }
    )
    dec, err, _ = AutonomyGovernor.evaluate_task_limits(ctx)
    assert dec == PolicyDecisionType.DENY
    assert "Task replanning cannot silently expand policy" in err


def test_approval_expiration_denied():
    past_time = (datetime.now(UTC) - timedelta(minutes=10)).isoformat()
    claim = {
        "status": "approved",
        "action": "deploy",
        "target": "prod-api",
        "expires_at": past_time,
    }
    ctx = PolicyContext(action="deploy", target="prod-api")
    ok, err = PolicyApprovalBridge.validate_approval_claim(ctx, claim)
    assert ok is False
    assert "Approval has expired" in err


def test_approval_non_transferability_checks():
    claim = {
        "status": "approved",
        "action": "deploy",
        "target": "staging-cluster",
        "environment": "staging",
        "user_id": "user_alice",
        "expires_at": (datetime.now(UTC) + timedelta(minutes=10)).isoformat(),
    }

    # Different target
    ctx_diff_target = PolicyContext(
        action="deploy", target="production-cluster", environment="staging", user={"id": "user_alice"}
    )
    ok, err = PolicyApprovalBridge.validate_approval_claim(ctx_diff_target, claim)
    assert ok is False
    assert "target" in err

    # Different action
    ctx_diff_action = PolicyContext(
        action="delete", target="staging-cluster", environment="staging", user={"id": "user_alice"}
    )
    ok, err = PolicyApprovalBridge.validate_approval_claim(ctx_diff_action, claim)
    assert ok is False
    assert "action" in err


def test_session_expired_denied():
    ctx = PolicyContext(
        action="deploy",
        session={"id": "sess_1", "is_expired": True, "is_active": False},
    )
    dec, err = AuthFreshnessChecker.evaluate_authentication(ctx, RiskLevel.R3_HIGH)
    assert dec == PolicyDecisionType.DENY
    assert "session is expired" in err


def test_stale_authentication_requires_step_up():
    twenty_min_ago = (datetime.now(UTC) - timedelta(minutes=20)).isoformat()
    ctx = PolicyContext(
        action="deploy",
        session={"id": "sess_1", "authenticated_at": twenty_min_ago, "is_active": True},
    )
    dec, err = AuthFreshnessChecker.evaluate_authentication(ctx, RiskLevel.R3_HIGH)
    assert dec == PolicyDecisionType.REQUIRE_STEP_UP_AUTH
    assert "step-up authentication" in err


def test_restricted_data_to_unapproved_model_denied():
    ctx = PolicyContext(
        data_scope={"classification": "RESTRICTED"},
        provider_model={"provider": "openai", "model": "gpt-4"},
    )
    dec, err, _ = DataAccessController.evaluate_data_access(ctx)
    assert dec == PolicyDecisionType.DENY
    assert "cannot be sent to unapproved model provider" in err


def test_restricted_data_to_local_approved():
    ctx = PolicyContext(
        data_scope={"classification": "RESTRICTED"},
        provider_model={"provider": "local", "model": "llama3"},
    )
    dec, err, allowed_scope = DataAccessController.evaluate_data_access(ctx)
    assert dec is None
    assert allowed_scope.get("classification") == "RESTRICTED"
