"""State, role, and evidence classification definitions for Multi-Agent Orchestration."""

from enum import StrEnum


class AgentType(StrEnum):
    """Supported specialist and coordination agent types."""

    SUPERVISOR = "SUPERVISOR"
    RESEARCHER = "RESEARCHER"
    DEVELOPER = "DEVELOPER"
    ANALYST = "ANALYST"
    BROWSER = "BROWSER"


class AgentTaskStatus(StrEnum):
    """Lifecycle status for an orchestrated sub-agent task."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"


class EvidenceType(StrEnum):
    """Classification of statements in agent results to prevent hallucinated certainty."""

    OBSERVED = (
        "OBSERVED"  # Facts directly verified via tools (e.g. file content, web citation, command output)
    )
    INFERRED = "INFERRED"  # Hypotheses or conclusions drawn by reasoning
    UNKNOWN = "UNKNOWN"  # Missing details or unverified questions


# State transition graph for agent tasks
VALID_TASK_TRANSITIONS: dict[AgentTaskStatus, set[AgentTaskStatus]] = {
    AgentTaskStatus.PENDING: {
        AgentTaskStatus.RUNNING,
        AgentTaskStatus.CANCELLED,
        AgentTaskStatus.TIMED_OUT,
    },
    AgentTaskStatus.RUNNING: {
        AgentTaskStatus.WAITING_APPROVAL,
        AgentTaskStatus.COMPLETED,
        AgentTaskStatus.FAILED,
        AgentTaskStatus.CANCELLED,
        AgentTaskStatus.TIMED_OUT,
    },
    AgentTaskStatus.WAITING_APPROVAL: {
        AgentTaskStatus.RUNNING,
        AgentTaskStatus.FAILED,
        AgentTaskStatus.CANCELLED,
        AgentTaskStatus.TIMED_OUT,
    },
    AgentTaskStatus.COMPLETED: set(),
    AgentTaskStatus.FAILED: set(),
    AgentTaskStatus.CANCELLED: set(),
    AgentTaskStatus.TIMED_OUT: set(),
}


def is_task_terminal(status: AgentTaskStatus | str) -> bool:
    """Check if task is in a terminal non-resumable state."""
    st = AgentTaskStatus(status)
    return st in (
        AgentTaskStatus.COMPLETED,
        AgentTaskStatus.FAILED,
        AgentTaskStatus.CANCELLED,
        AgentTaskStatus.TIMED_OUT,
    )


def transition_task_state(
    current: AgentTaskStatus | str, new_state: AgentTaskStatus | str
) -> AgentTaskStatus:
    """Validate and transition an agent task to a new state."""
    curr_enum = AgentTaskStatus(current)
    new_enum = AgentTaskStatus(new_state)

    if curr_enum == new_enum:
        return new_enum

    valid_targets = VALID_TASK_TRANSITIONS.get(curr_enum, set())
    if new_enum not in valid_targets:
        raise ValueError(
            f"Invalid agent task transition: cannot move from '{curr_enum.value}' to '{new_enum.value}'."
        )

    return new_enum
