"""Tests for explicit state machine transitions and terminal state enforcement (Task 39)."""

import pytest

from app.state.fabric import state_fabric
from app.state.schemas import StateDomain
from app.state.state_machine import StateMachineValidator


@pytest.fixture(autouse=True)
def clean_state():
    state_fabric.clear()
    yield
    state_fabric.clear()


@pytest.mark.asyncio
async def test_valid_task_state_transitions():
    """Tasks transition cleanly along valid paths."""
    await state_fabric.create_record(
        domain=StateDomain.TASKS,
        resource_type="task",
        resource_id="task_sm_1",
        data={"payload": "run"},
        calling_service="task_engine",
        status="RUNNING",
    )

    # RUNNING -> COMPLETED is valid
    completed = await state_fabric.transition_record(
        domain=StateDomain.TASKS,
        resource_type="task",
        resource_id="task_sm_1",
        new_status="COMPLETED",
        expected_version=1,
        calling_service="task_engine",
    )
    assert completed.status == "COMPLETED"
    assert completed.version == 2


@pytest.mark.asyncio
async def test_terminal_state_invariant_completed_task_cannot_become_running():
    """Terminal state invariant: COMPLETED task cannot transition back to RUNNING directly."""
    await state_fabric.create_record(
        domain=StateDomain.TASKS,
        resource_type="task",
        resource_id="task_sm_terminal",
        data={"payload": "done"},
        calling_service="task_engine",
        status="COMPLETED",
    )

    with pytest.raises(ValueError) as exc_info:
        await state_fabric.transition_record(
            domain=StateDomain.TASKS,
            resource_type="task",
            resource_id="task_sm_terminal",
            new_status="RUNNING",
            expected_version=1,
            calling_service="task_engine",
        )
    assert "Illegal state transition for 'task': 'COMPLETED' cannot transition to 'RUNNING'" in str(exc_info.value)


@pytest.mark.asyncio
async def test_approval_terminal_state():
    """APPROVED and REJECTED approvals are terminal."""
    with pytest.raises(ValueError):
        StateMachineValidator.validate_transition("approval", "APPROVED", "PENDING")

    with pytest.raises(ValueError):
        StateMachineValidator.validate_transition("approval", "REJECTED", "APPROVED")


def test_device_and_session_state_transitions():
    """Test device and session transitions."""
    assert StateMachineValidator.is_valid_transition("device", "CONNECTED", "DISCONNECTED")
    assert StateMachineValidator.is_valid_transition("device", "DISCONNECTED", "CONNECTED")
    assert StateMachineValidator.is_valid_transition("session", "ACTIVE", "EXPIRED")

    # REVOKED is terminal
    assert not StateMachineValidator.is_valid_transition("device", "REVOKED", "CONNECTED")
    assert not StateMachineValidator.is_valid_transition("session", "REVOKED", "ACTIVE")
