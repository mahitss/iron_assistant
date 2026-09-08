"""Explicit workflow run state machine with validated transitions."""

from enum import Enum


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal workflow state transition is attempted."""


# Valid transition graph
VALID_TRANSITIONS: dict[WorkflowStatus, set[WorkflowStatus]] = {
    WorkflowStatus.PENDING: {
        WorkflowStatus.RUNNING,
        WorkflowStatus.CANCELLED,
    },
    WorkflowStatus.RUNNING: {
        WorkflowStatus.WAITING_APPROVAL,
        WorkflowStatus.RETRYING,
        WorkflowStatus.COMPLETED,
        WorkflowStatus.FAILED,
        WorkflowStatus.CANCELLED,
    },
    WorkflowStatus.WAITING_APPROVAL: {
        WorkflowStatus.RUNNING,  # Approved
        WorkflowStatus.FAILED,  # Denied
        WorkflowStatus.EXPIRED,  # Approval expired
        WorkflowStatus.CANCELLED,  # User cancelled run
    },
    WorkflowStatus.RETRYING: {
        WorkflowStatus.RUNNING,
        WorkflowStatus.FAILED,
        WorkflowStatus.CANCELLED,
    },
    # Terminal states have no outbound transitions
    WorkflowStatus.COMPLETED: set(),
    WorkflowStatus.FAILED: set(),
    WorkflowStatus.CANCELLED: set(),
    WorkflowStatus.EXPIRED: set(),
}


def transition_state(current: str | WorkflowStatus, target: str | WorkflowStatus) -> WorkflowStatus:
    """Validate and perform an atomic state transition."""
    curr_status = WorkflowStatus(current) if isinstance(current, str) else current
    target_status = WorkflowStatus(target) if isinstance(target, str) else target

    if curr_status == target_status:
        return curr_status

    allowed = VALID_TRANSITIONS.get(curr_status, set())
    if target_status not in allowed:
        raise InvalidStateTransitionError(
            f"Illegal workflow state transition from '{curr_status.value}' to '{target_status.value}'."
        )

    return target_status


def is_terminal_state(status: str | WorkflowStatus) -> bool:
    """Check if status is terminal (cannot transition further)."""
    s = WorkflowStatus(status) if isinstance(status, str) else status
    return s in {
        WorkflowStatus.COMPLETED,
        WorkflowStatus.FAILED,
        WorkflowStatus.CANCELLED,
        WorkflowStatus.EXPIRED,
    }
