"""Unit tests for EmergencyStopService kill switch and model tampering resistance."""

import pytest

from app.security.emergency_stop import EmergencyStopService
from app.security.exceptions import EmergencyStopActiveError, SecurityError
from app.security.permissions import PermissionLevel


def test_emergency_stop_lifecycle():
    """Verify emergency stop activation blocks side-effects and reset restores execution."""
    svc = EmergencyStopService()

    assert svc.is_stopped("user_1") is False

    # Normal state allows execution
    svc.verify_can_execute("git_push", PermissionLevel.WRITE, "user_1")

    # Activate emergency stop
    svc.trigger_emergency_stop("user_1", reason="Testing kill switch")
    assert svc.is_stopped("user_1") is True

    # Safe read operations are still permitted
    svc.verify_can_execute("git_status", PermissionLevel.READ, "user_1")

    # Side-effecting operations are strictly blocked
    with pytest.raises(EmergencyStopActiveError):
        svc.verify_can_execute("git_push", PermissionLevel.WRITE, "user_1")

    with pytest.raises(EmergencyStopActiveError):
        svc.verify_can_execute("browser_click", PermissionLevel.EXTERNAL, "user_1")

    # Reset restores operations
    svc.reset_emergency_stop("user_1", is_human_user=True)
    assert svc.is_stopped("user_1") is False
    svc.verify_can_execute("git_push", PermissionLevel.WRITE, "user_1")


def test_model_cannot_reset_emergency_stop():
    """Verify that an automated model attempt to reset the emergency stop is rejected."""
    svc = EmergencyStopService()
    svc.trigger_emergency_stop("user_1", reason="Safety containment")

    # Simulated LLM calling reset with is_human_user=False
    with pytest.raises(SecurityError) as exc:
        svc.reset_emergency_stop("user_1", is_human_user=False)

    assert "The AI model cannot reset an emergency stop" in str(exc.value)
    # Remains stopped!
    assert svc.is_stopped("user_1") is True
