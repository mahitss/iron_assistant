"""Tests for LocalActionExecutor end-to-end command pipeline, allowlist gating, and approval enforcement."""

import time

import pytest

from companion.src.actions.executor import LocalActionExecutor
from companion.src.approvals.verifier import ApprovalArtifactVerifier
from companion.src.device.identity import DeviceIdentityManager
from companion.src.device.state import CompanionState, DeviceStateManager
from companion.src.filesystem.sandbox import FilesystemSandbox
from companion.src.security.emergency_stop import LocalEmergencyStop
from companion.src.security.policy import LocalPolicyEngine
from companion.src.telemetry.logger import LocalAuditLogger


@pytest.fixture
def executor_setup(tmp_path):
    identity_mgr = DeviceIdentityManager(state_dir=tmp_path / "id")
    state_mgr = DeviceStateManager()
    emergency_stop = LocalEmergencyStop()
    sandbox = FilesystemSandbox(allowed_directories=[str(tmp_path / "workspace")])
    (tmp_path / "workspace").mkdir()

    policy_engine = LocalPolicyEngine(
        state_manager=state_mgr,
        emergency_stop=emergency_stop,
        allowed_filesystem_paths=[str(tmp_path / "workspace")],
    )
    audit_logger = LocalAuditLogger(log_dir=tmp_path / "logs")
    approval_verifier = ApprovalArtifactVerifier()

    executor = LocalActionExecutor(
        identity_manager=identity_mgr,
        policy_engine=policy_engine,
        approval_verifier=approval_verifier,
        audit_logger=audit_logger,
        sandbox=sandbox,
    )

    return {
        "executor": executor,
        "identity_mgr": identity_mgr,
        "state_mgr": state_mgr,
        "emergency_stop": emergency_stop,
        "approval_verifier": approval_verifier,
        "tmp_path": tmp_path,
    }


def test_executor_forbidden_shell_action_blocked(executor_setup):
    """Verify arbitrary shell/powershell commands are blocked before execution."""
    executor = executor_setup["executor"]
    device_id = executor_setup["identity_mgr"].get_or_create_device_id()

    cmd = {
        "command_id": "cmd_shell_1",
        "device_id": device_id,
        "action": "shell.execute",
        "parameters": {"cmd": "rm -rf /"},
        "timestamp": time.time(),
    }
    res = executor.execute_command(cmd)
    assert res["status"] in ("DENIED", "ERROR")
    assert res["success"] is False


def test_executor_state_off_blocks_mutating_actions(executor_setup):
    """Verify mutating actions (mouse.click) are blocked when companion is in default OFF state."""
    executor = executor_setup["executor"]
    device_id = executor_setup["identity_mgr"].get_or_create_device_id()

    cmd = {
        "command_id": "cmd_click_1",
        "device_id": device_id,
        "action": "mouse.click",
        "parameters": {"x": 100, "y": 100},
        "timestamp": time.time(),
    }
    res = executor.execute_command(cmd)
    assert res["status"] == "DENIED"
    assert "OFF" in res["reason"]


def test_executor_approval_requirement_and_execution(executor_setup):
    """Verify high-risk action requires approval token, and executes once verified."""
    executor = executor_setup["executor"]
    state_mgr = executor_setup["state_mgr"]
    device_id = executor_setup["identity_mgr"].get_or_create_device_id()

    # 1. Arm computer control
    state_mgr.transition_to(CompanionState.ARMED)
    state_mgr.set_capability("computer_control", True)

    # 2. Attempt mouse.click without approval -> DENIED by local policy
    cmd_no_appr = {
        "command_id": "cmd_mouse_no_appr",
        "device_id": device_id,
        "action": "mouse.click",
        "parameters": {"x": 200, "y": 300},
        "timestamp": time.time(),
    }
    res_no_appr = executor.execute_command(cmd_no_appr)
    assert res_no_appr["status"] == "DENIED"
    assert "approval" in res_no_appr["reason"].lower()

    # 3. Create valid approval artifact
    import datetime
    import hashlib
    import hmac

    now = datetime.datetime.now(datetime.timezone.utc)
    expires = now + datetime.timedelta(seconds=60)
    appr_id = "appr_test_123"
    signing_content = f"{appr_id}:user_test:{device_id}:mouse.click:*:{expires.isoformat()}"
    sig = hmac.new(
        b"kairo_approval_signing_secret", signing_content.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    approval_artifact = {
        "approval_id": appr_id,
        "user_id": "user_test",
        "device_id": device_id,
        "action": "mouse.click",
        "target_scope": "*",
        "expires_at": expires.isoformat(),
        "signature": sig,
    }

    # 4. Execute with approval artifact -> SUCCESS
    cmd_approved = {
        "command_id": "cmd_mouse_approved",
        "device_id": device_id,
        "action": "mouse.click",
        "parameters": {"x": 200, "y": 300},
        "authorization_context": approval_artifact,
        "timestamp": time.time(),
    }
    res_approved = executor.execute_command(cmd_approved)
    assert res_approved["status"] == "COMPLETED"
    assert res_approved["success"] is True


def test_executor_local_emergency_stop_halts_everything(executor_setup):
    """Verify local emergency stop immediately halts all actions."""
    executor = executor_setup["executor"]
    state_mgr = executor_setup["state_mgr"]
    emergency_stop = executor_setup["emergency_stop"]
    device_id = executor_setup["identity_mgr"].get_or_create_device_id()

    state_mgr.transition_to(CompanionState.ARMED)
    state_mgr.set_capability("computer_control", True)

    # Trigger emergency stop
    emergency_stop.trigger_stop("User hit emergency stop")

    cmd = {
        "command_id": "cmd_estop_1",
        "device_id": device_id,
        "action": "screen.capture",
        "parameters": {},
        "timestamp": time.time(),
    }
    res = executor.execute_command(cmd)
    assert res["status"] == "DENIED"
    assert "Emergency Stop is ACTIVE" in res["reason"]
