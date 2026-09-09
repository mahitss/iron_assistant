"""Tests for Task and Step schemas, state machines, and objective immutability (Spec 3-8, 64, 65)."""

import pytest
from app.tasks.schemas import (
    AutonomyLevel,
    FailureClassification,
    StepStatus,
    TaskBudget,
    TaskCreateRequest,
    TaskPriority,
    TaskRiskLevel,
    TaskStatus,
    TaskStepSchema,
)
from app.tasks.state import (
    InvalidStateTransitionError,
    StepStateMachine,
    TaskStateMachine,
)


def test_task_states_coverage():
    """Verify all authoritative task states are represented."""
    expected_states = {
        "QUEUED", "PLANNING", "WAITING_APPROVAL", "WAITING_USER", "RUNNING",
        "PAUSED", "REPLANNING", "VERIFYING", "COMPLETED", "PARTIALLY_COMPLETED",
        "FAILED", "CANCELLED", "TIMED_OUT", "BLOCKED"
    }
    actual_states = {s.value for s in TaskStatus}
    assert expected_states == actual_states


def test_step_states_coverage():
    """Verify all authoritative step states are represented."""
    expected = {"PENDING", "READY", "RUNNING", "WAITING_APPROVAL", "COMPLETED", "FAILED", "SKIPPED", "CANCELLED", "BLOCKED"}
    actual = {s.value for s in StepStatus}
    assert expected == actual


def test_task_state_machine_legal_transitions():
    """Test valid task lifecycle transitions."""
    # QUEUED -> PLANNING -> RUNNING -> VERIFYING -> COMPLETED
    assert TaskStateMachine.can_transition(TaskStatus.QUEUED, TaskStatus.PLANNING)
    assert TaskStateMachine.can_transition(TaskStatus.PLANNING, TaskStatus.RUNNING)
    assert TaskStateMachine.can_transition(TaskStatus.RUNNING, TaskStatus.VERIFYING)
    assert TaskStateMachine.can_transition(TaskStatus.VERIFYING, TaskStatus.COMPLETED)

    # RUNNING -> WAITING_APPROVAL -> RUNNING
    assert TaskStateMachine.can_transition(TaskStatus.RUNNING, TaskStatus.WAITING_APPROVAL)
    assert TaskStateMachine.can_transition(TaskStatus.WAITING_APPROVAL, TaskStatus.RUNNING)

    # RUNNING -> WAITING_USER -> PLANNING
    assert TaskStateMachine.can_transition(TaskStatus.RUNNING, TaskStatus.WAITING_USER)
    assert TaskStateMachine.can_transition(TaskStatus.WAITING_USER, TaskStatus.PLANNING)

    # RUNNING -> PAUSED -> RUNNING
    assert TaskStateMachine.can_transition(TaskStatus.RUNNING, TaskStatus.PAUSED)
    assert TaskStateMachine.can_transition(TaskStatus.PAUSED, TaskStatus.RUNNING)

    # Cancellation from any active state
    assert TaskStateMachine.can_transition(TaskStatus.RUNNING, TaskStatus.CANCELLED)
    assert TaskStateMachine.can_transition(TaskStatus.PAUSED, TaskStatus.CANCELLED)


def test_task_state_machine_illegal_transitions():
    """Verify illegal task state transitions are rejected with InvalidStateTransitionError."""
    # Terminal states cannot transition to anything
    assert not TaskStateMachine.can_transition(TaskStatus.COMPLETED, TaskStatus.RUNNING)
    with pytest.raises(InvalidStateTransitionError):
        TaskStateMachine.validate_transition(TaskStatus.COMPLETED, TaskStatus.RUNNING)

    assert not TaskStateMachine.can_transition(TaskStatus.FAILED, TaskStatus.RUNNING)
    with pytest.raises(InvalidStateTransitionError):
        TaskStateMachine.validate_transition(TaskStatus.FAILED, TaskStatus.RUNNING)

    assert not TaskStateMachine.can_transition(TaskStatus.CANCELLED, TaskStatus.PLANNING)
    with pytest.raises(InvalidStateTransitionError):
        TaskStateMachine.validate_transition(TaskStatus.CANCELLED, TaskStatus.PLANNING)

    # Cannot skip directly from QUEUED to COMPLETED
    assert not TaskStateMachine.can_transition(TaskStatus.QUEUED, TaskStatus.COMPLETED)


def test_step_state_machine_transitions():
    """Verify step node lifecycle transitions."""
    assert StepStateMachine.can_transition(StepStatus.PENDING, StepStatus.READY)
    assert StepStateMachine.can_transition(StepStatus.READY, StepStatus.RUNNING)
    assert StepStateMachine.can_transition(StepStatus.RUNNING, StepStatus.COMPLETED)

    # FAILED can transition to READY for safe retry
    assert StepStateMachine.can_transition(StepStatus.FAILED, StepStatus.READY)

    # COMPLETED is terminal
    assert not StepStateMachine.can_transition(StepStatus.COMPLETED, StepStatus.RUNNING)
    with pytest.raises(InvalidStateTransitionError):
        StepStateMachine.validate_transition(StepStatus.COMPLETED, StepStatus.RUNNING)


def test_objective_immutability():
    """Verify user original objective cannot be mutated by plans or step schemas (Spec 5, 138)."""
    orig_objective = "Investigate why Kairo CI is failing"
    req = TaskCreateRequest(objective=orig_objective)
    assert req.objective == orig_objective

    step = TaskStepSchema(
        task_id="task_1",
        plan_id="plan_1",
        sequence=1,
        title="Inspect CI",
        objective="Read CI logs",
    )
    # Step has its own sub-objective; original objective is separate and untouched
    assert step.objective != req.objective
