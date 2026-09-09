"""Tests for device state transitions, default OFF, inactivity decay, and emergency stop."""

import pytest

from companion.src.device.state import CompanionState, DeviceStateManager
from companion.src.security.emergency_stop import LocalEmergencyStop


def test_state_defaults_to_safe_off():
    """Verify state manager starts strictly in OFF state with all capabilities disabled."""
    mgr = DeviceStateManager()
    assert mgr.current_state == CompanionState.OFF
    assert mgr.is_capability_enabled("computer_control") is False
    assert mgr.is_capability_enabled("microphone") is False
    assert mgr.is_capability_enabled("camera") is False
    assert mgr.is_capability_enabled("filesystem") is False

    # Cannot enable capabilities while OFF
    with pytest.raises(PermissionError):
        mgr.set_capability("computer_control", True)


def test_state_transitions_and_arm():
    """Verify explicit transitions to ARMED and capability toggling."""
    mgr = DeviceStateManager()
    mgr.transition_to(CompanionState.ARMED, "User armed system")
    assert mgr.current_state == CompanionState.ARMED

    mgr.set_capability("computer_control", True)
    assert mgr.is_capability_enabled("computer_control") is True

    # Reset to safe OFF
    mgr.reset_to_safe_off()
    assert mgr.current_state == CompanionState.OFF
    assert mgr.is_capability_enabled("computer_control") is False


def test_inactivity_auto_decay():
    """Verify that prolonged inactivity decays active state back to safe OFF."""
    # Set short timeout of 0.1 seconds for test
    mgr = DeviceStateManager(inactivity_timeout_seconds=0.1)
    mgr.transition_to(CompanionState.ARMED)
    mgr.set_capability("camera", True)

    import time

    time.sleep(0.15)

    assert mgr.current_state == CompanionState.OFF
    assert mgr.is_capability_enabled("camera") is False


def test_local_emergency_stop_cutoff():
    """Verify local emergency stop immediately sets atomic flag and triggers callbacks."""
    estop = LocalEmergencyStop()
    assert estop.is_stopped is False

    callback_fired = []
    estop.register_halt_callback(lambda: callback_fired.append(True))

    estop.trigger_stop("Critical hazard")
    assert estop.is_stopped is True
    assert len(callback_fired) == 1

    # Reset back to unhalted
    estop.reset_stop()
    assert estop.is_stopped is False
