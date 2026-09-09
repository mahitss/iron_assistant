"""Unit tests for Environment policies, Change Freezes, Safe Mode, and Device Guardrails (Task 36, Specs 16-18, 64-66, 109-113, 122, 125, 126, 140)."""

import pytest
from app.policy.devices import DevicePolicyEnforcer
from app.policy.environments import EnvironmentPolicyManager
from app.policy.schemas import PolicyContext, PolicyDecisionType, RiskLevel


def test_safe_mode_blocks_mutations():
    mgr = EnvironmentPolicyManager()
    mgr.set_safe_mode(True)

    # Safe read should pass
    ctx_read = PolicyContext(action="read", environment="development")
    dec_read, _ = mgr.evaluate_environment_constraints(ctx_read)
    assert dec_read is None

    # Mutation should be strictly DENIED
    ctx_write = PolicyContext(action="write_config", environment="development")
    dec_write, err_write = mgr.evaluate_environment_constraints(ctx_write)
    assert dec_write == PolicyDecisionType.DENY
    assert "Safe mode is active" in err_write


def test_incident_mode_blocks_autonomous_tasks():
    mgr = EnvironmentPolicyManager()
    mgr.set_incident_mode(True)

    ctx_task = PolicyContext(
        action="update_deps",
        task={"id": "task_auto_1"},
        environment="development",
    )
    dec, err = mgr.evaluate_environment_constraints(ctx_task)
    assert dec == PolicyDecisionType.DENY
    assert "Incident mode is active" in err


def test_change_freeze_blocks_deployment():
    mgr = EnvironmentPolicyManager()
    mgr.set_change_freeze("production", True, reason="End of quarter freeze")

    ctx_deploy = PolicyContext(action="deploy_service", environment="production")
    dec, err = mgr.evaluate_environment_constraints(ctx_deploy)
    assert dec == PolicyDecisionType.DENY
    assert "Change freeze active on 'production'" in err


def test_production_deployment_requires_approval():
    mgr = EnvironmentPolicyManager()
    ctx = PolicyContext(
        action="deploy",
        environment="production",
        target={"service": "payment-gateway"},
    )
    dec, err = mgr.evaluate_environment_constraints(ctx)
    assert dec == PolicyDecisionType.REQUIRE_APPROVAL
    assert "Production deployments" in err


def test_production_stale_state_blocks_execution():
    mgr = EnvironmentPolicyManager()
    ctx = PolicyContext(
        action="deploy",
        environment="production",
        target={"service": "web", "state_is_stale": True},
    )
    dec, err = mgr.evaluate_environment_constraints(ctx)
    assert dec == PolicyDecisionType.DENY
    assert "Target state is stale" in err


def test_revoked_device_immediately_denied():
    ctx = PolicyContext(
        action="read",
        device={"id": "dev_bad_999", "is_revoked": True},
    )
    dec, err = DevicePolicyEnforcer.evaluate_device(ctx, RiskLevel.R0_READ_ONLY)
    assert dec == PolicyDecisionType.DENY
    assert "revoked" in err.lower()


def test_untrusted_device_computer_control_requires_step_up():
    ctx = PolicyContext(
        action="computer_click",
        tool="computer_click",
        device={"id": "dev_laptop", "is_trusted": False},
    )
    dec, err = DevicePolicyEnforcer.evaluate_device(ctx, RiskLevel.R2_MODERATE)
    assert dec == PolicyDecisionType.REQUIRE_STEP_UP_AUTH
    assert "untrusted device requires step-up authentication" in err


def test_device_capability_mismatch_denied():
    ctx = PolicyContext(
        action="screen_record",
        tool="computer_screenshot",
        device={
            "id": "dev_iot",
            "is_trusted": True,
            "capabilities": ["audio_capture"],  # Missing screen_capture
        },
    )
    dec, err = DevicePolicyEnforcer.evaluate_device(ctx, RiskLevel.R1_LOW)
    assert dec == PolicyDecisionType.DENY
    assert "lacks 'screen_capture' capability" in err


def test_device_reconnect_triggers_reevaluation():
    ctx = PolicyContext(
        action="computer_click",
        device={"id": "dev_reconnected", "is_trusted": True, "reconnected_needs_reeval": True},
    )
    dec, err = DevicePolicyEnforcer.evaluate_device(ctx, RiskLevel.R2_MODERATE)
    assert dec == PolicyDecisionType.DEFER
    assert "Device reconnected during task" in err
