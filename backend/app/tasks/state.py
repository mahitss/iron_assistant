"""State machine definitions and validated transition logic for Tasks and Steps (Spec 4, 8)."""

from typing import Set
from app.tasks.schemas import StepStatus, TaskStatus


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal state transition is attempted."""

    def __init__(self, entity_type: str, current_state: str, requested_state: str) -> None:
        super().__init__(
            f"Illegal {entity_type} state transition from '{current_state}' to '{requested_state}'"
        )
        self.entity_type = entity_type
        self.current_state = current_state
        self.requested_state = requested_state


class TaskStateMachine:
    """Authoritative state machine governing Task lifecycle transitions."""

    _TERMINAL_STATES: Set[TaskStatus] = {
        TaskStatus.COMPLETED,
        TaskStatus.PARTIALLY_COMPLETED,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
        TaskStatus.TIMED_OUT,
    }

    # Explicit allowed transition graph
    _ALLOWED_TRANSITIONS: dict[TaskStatus, Set[TaskStatus]] = {
        TaskStatus.QUEUED: {
            TaskStatus.PLANNING,
            TaskStatus.CANCELLED,
            TaskStatus.TIMED_OUT,
            TaskStatus.BLOCKED,
        },
        TaskStatus.PLANNING: {
            TaskStatus.RUNNING,
            TaskStatus.WAITING_APPROVAL,
            TaskStatus.WAITING_USER,
            TaskStatus.FAILED,
            TaskStatus.BLOCKED,
            TaskStatus.CANCELLED,
            TaskStatus.TIMED_OUT,
        },
        TaskStatus.WAITING_APPROVAL: {
            TaskStatus.RUNNING,
            TaskStatus.CANCELLED,
            TaskStatus.FAILED,
            TaskStatus.PAUSED,
            TaskStatus.TIMED_OUT,
            TaskStatus.BLOCKED,
        },
        TaskStatus.WAITING_USER: {
            TaskStatus.PLANNING,
            TaskStatus.RUNNING,
            TaskStatus.CANCELLED,
            TaskStatus.PAUSED,
            TaskStatus.FAILED,
            TaskStatus.TIMED_OUT,
        },
        TaskStatus.RUNNING: {
            TaskStatus.WAITING_APPROVAL,
            TaskStatus.WAITING_USER,
            TaskStatus.PAUSED,
            TaskStatus.REPLANNING,
            TaskStatus.VERIFYING,
            TaskStatus.COMPLETED,
            TaskStatus.PARTIALLY_COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
            TaskStatus.TIMED_OUT,
            TaskStatus.BLOCKED,
        },
        TaskStatus.PAUSED: {
            TaskStatus.RUNNING,
            TaskStatus.CANCELLED,
            TaskStatus.TIMED_OUT,
        },
        TaskStatus.REPLANNING: {
            TaskStatus.RUNNING,
            TaskStatus.WAITING_APPROVAL,
            TaskStatus.WAITING_USER,
            TaskStatus.FAILED,
            TaskStatus.BLOCKED,
            TaskStatus.CANCELLED,
            TaskStatus.TIMED_OUT,
        },
        TaskStatus.VERIFYING: {
            TaskStatus.COMPLETED,
            TaskStatus.PARTIALLY_COMPLETED,
            TaskStatus.REPLANNING,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
            TaskStatus.TIMED_OUT,
        },
        TaskStatus.BLOCKED: {
            TaskStatus.REPLANNING,
            TaskStatus.CANCELLED,
            TaskStatus.FAILED,
        },
        # Terminal states have no outbound transitions
        TaskStatus.COMPLETED: set(),
        TaskStatus.PARTIALLY_COMPLETED: set(),
        TaskStatus.FAILED: set(),
        TaskStatus.CANCELLED: set(),
        TaskStatus.TIMED_OUT: set(),
    }

    @classmethod
    def is_terminal(cls, status: TaskStatus) -> bool:
        """Check if state is terminal."""
        return status in cls._TERMINAL_STATES

    @classmethod
    def can_transition(cls, from_state: TaskStatus, to_state: TaskStatus) -> bool:
        """Return True if transition is valid according to transition matrix."""
        if from_state == to_state:
            return True
        allowed = cls._ALLOWED_TRANSITIONS.get(from_state, set())
        return to_state in allowed

    @classmethod
    def validate_transition(cls, from_state: TaskStatus, to_state: TaskStatus) -> None:
        """Validate state transition or raise InvalidStateTransitionError."""
        if not cls.can_transition(from_state, to_state):
            raise InvalidStateTransitionError("Task", from_state.value, to_state.value)


class StepStateMachine:
    """Authoritative state machine governing TaskStep node transitions."""

    _TERMINAL_STATES: Set[StepStatus] = {
        StepStatus.COMPLETED,
        StepStatus.FAILED,
        StepStatus.SKIPPED,
        StepStatus.CANCELLED,
    }

    _ALLOWED_TRANSITIONS: dict[StepStatus, Set[StepStatus]] = {
        StepStatus.PENDING: {
            StepStatus.READY,
            StepStatus.SKIPPED,
            StepStatus.CANCELLED,
            StepStatus.BLOCKED,
        },
        StepStatus.READY: {
            StepStatus.RUNNING,
            StepStatus.WAITING_APPROVAL,
            StepStatus.SKIPPED,
            StepStatus.CANCELLED,
            StepStatus.BLOCKED,
        },
        StepStatus.WAITING_APPROVAL: {
            StepStatus.RUNNING,
            StepStatus.CANCELLED,
            StepStatus.FAILED,
            StepStatus.BLOCKED,
        },
        StepStatus.RUNNING: {
            StepStatus.COMPLETED,
            StepStatus.FAILED,
            StepStatus.CANCELLED,
            StepStatus.WAITING_APPROVAL,
            StepStatus.BLOCKED,
        },
        StepStatus.BLOCKED: {
            StepStatus.READY,
            StepStatus.FAILED,
            StepStatus.CANCELLED,
            StepStatus.SKIPPED,
        },
        # Terminal states
        StepStatus.COMPLETED: set(),
        StepStatus.FAILED: {StepStatus.READY},  # Allows retry into READY state
        StepStatus.SKIPPED: set(),
        StepStatus.CANCELLED: set(),
    }

    @classmethod
    def is_terminal(cls, status: StepStatus) -> bool:
        """Check if step state is terminal."""
        return status in cls._TERMINAL_STATES

    @classmethod
    def can_transition(cls, from_state: StepStatus, to_state: StepStatus) -> bool:
        """Check if step transition is legal."""
        if from_state == to_state:
            return True
        allowed = cls._ALLOWED_TRANSITIONS.get(from_state, set())
        return to_state in allowed

    @classmethod
    def validate_transition(cls, from_state: StepStatus, to_state: StepStatus) -> None:
        """Validate step state transition or raise error."""
        if not cls.can_transition(from_state, to_state):
            raise InvalidStateTransitionError("TaskStep", from_state.value, to_state.value)
