"""State machine and lifecycle management for Kairo Autonomous Discovery Engine (Task 72).

Enforces valid transitions for:
- DiscoveryState (18-state scientific lifecycle)
- ExperimentStatus (10-state execution lifecycle)
"""

from app.discovery.schemas import DiscoveryState, ExperimentStatus

# Allowed transitions for DiscoverySession
DISCOVERY_TRANSITIONS: dict[DiscoveryState, set[DiscoveryState]] = {
    DiscoveryState.CREATED: {
        DiscoveryState.QUESTION_FORMED,
        DiscoveryState.CANCELLED,
        DiscoveryState.BLOCKED,
        DiscoveryState.FAILED,
    },
    DiscoveryState.QUESTION_FORMED: {
        DiscoveryState.HYPOTHESIS_GENERATED,
        DiscoveryState.INCONCLUSIVE,
        DiscoveryState.CANCELLED,
        DiscoveryState.BLOCKED,
        DiscoveryState.FAILED,
    },
    DiscoveryState.HYPOTHESIS_GENERATED: {
        DiscoveryState.EXPERIMENT_DESIGN,
        DiscoveryState.INCONCLUSIVE,
        DiscoveryState.NEEDS_HUMAN_REVIEW,
        DiscoveryState.CANCELLED,
        DiscoveryState.BLOCKED,
    },
    DiscoveryState.EXPERIMENT_DESIGN: {
        DiscoveryState.AWAITING_APPROVAL,
        DiscoveryState.READY,
        DiscoveryState.RUNNING,
        DiscoveryState.CONCLUDED,
        DiscoveryState.NEEDS_HUMAN_REVIEW,
        DiscoveryState.BLOCKED,
        DiscoveryState.CANCELLED,
        DiscoveryState.FAILED,
    },
    DiscoveryState.AWAITING_APPROVAL: {
        DiscoveryState.READY,
        DiscoveryState.BLOCKED,
        DiscoveryState.CANCELLED,
        DiscoveryState.NEEDS_HUMAN_REVIEW,
    },
    DiscoveryState.READY: {
        DiscoveryState.RUNNING,
        DiscoveryState.CONCLUDED,
        DiscoveryState.AWAITING_APPROVAL,
        DiscoveryState.BLOCKED,
        DiscoveryState.CANCELLED,
    },
    DiscoveryState.RUNNING: {
        DiscoveryState.OBSERVING,
        DiscoveryState.FAILED,
        DiscoveryState.BLOCKED,
        DiscoveryState.CANCELLED,
        DiscoveryState.NEEDS_HUMAN_REVIEW,
    },
    DiscoveryState.OBSERVING: {
        DiscoveryState.ANALYZING,
        DiscoveryState.FAILED,
        DiscoveryState.BLOCKED,
        DiscoveryState.INCONCLUSIVE,
    },
    DiscoveryState.ANALYZING: {
        DiscoveryState.VALIDATING,
        DiscoveryState.CONCLUDED,
        DiscoveryState.INCONCLUSIVE,
        DiscoveryState.EXPERIMENT_DESIGN,  # Iterative hypothesis/experiment design loop
        DiscoveryState.FAILED,
    },
    DiscoveryState.VALIDATING: {
        DiscoveryState.CONCLUDED,
        DiscoveryState.KNOWLEDGE_UPDATE,
        DiscoveryState.NEEDS_HUMAN_REVIEW,
        DiscoveryState.INCONCLUSIVE,
        DiscoveryState.FAILED,
    },
    DiscoveryState.CONCLUDED: {
        DiscoveryState.KNOWLEDGE_UPDATE,
        DiscoveryState.COMPLETED,
        DiscoveryState.EXPERIMENT_DESIGN,  # Subsequent follow-up experiment
    },
    DiscoveryState.KNOWLEDGE_UPDATE: {
        DiscoveryState.COMPLETED,
        DiscoveryState.NEEDS_HUMAN_REVIEW,
        DiscoveryState.FAILED,
    },
    DiscoveryState.NEEDS_HUMAN_REVIEW: {
        DiscoveryState.READY,
        DiscoveryState.EXPERIMENT_DESIGN,
        DiscoveryState.CONCLUDED,
        DiscoveryState.CANCELLED,
        DiscoveryState.BLOCKED,
    },
    DiscoveryState.BLOCKED: {
        DiscoveryState.READY,
        DiscoveryState.EXPERIMENT_DESIGN,
        DiscoveryState.CANCELLED,
        DiscoveryState.FAILED,
    },
    DiscoveryState.INCONCLUSIVE: {
        DiscoveryState.EXPERIMENT_DESIGN,
        DiscoveryState.COMPLETED,
        DiscoveryState.CANCELLED,
    },
    DiscoveryState.COMPLETED: set(),  # Terminal
    DiscoveryState.FAILED: {DiscoveryState.EXPERIMENT_DESIGN},  # Can be re-opened or kept terminal
    DiscoveryState.CANCELLED: set(),  # Terminal
}


# Allowed transitions for Experiment execution
EXPERIMENT_TRANSITIONS: dict[ExperimentStatus, set[ExperimentStatus]] = {
    ExperimentStatus.PROPOSED: {
        ExperimentStatus.READY,
        ExperimentStatus.APPROVAL_REQUIRED,
        ExperimentStatus.BLOCKED,
        ExperimentStatus.CANCELLED,
    },
    ExperimentStatus.APPROVAL_REQUIRED: {
        ExperimentStatus.APPROVED,
        ExperimentStatus.BLOCKED,
        ExperimentStatus.CANCELLED,
    },
    ExperimentStatus.APPROVED: {
        ExperimentStatus.READY,
        ExperimentStatus.RUNNING,
        ExperimentStatus.CANCELLED,
    },
    ExperimentStatus.READY: {
        ExperimentStatus.RUNNING,
        ExperimentStatus.BLOCKED,
        ExperimentStatus.CANCELLED,
    },
    ExperimentStatus.RUNNING: {
        ExperimentStatus.COMPLETED,
        ExperimentStatus.FAILED,
        ExperimentStatus.INVALID,
        ExperimentStatus.CANCELLED,
    },
    ExperimentStatus.BLOCKED: {
        ExperimentStatus.READY,
        ExperimentStatus.PROPOSED,
        ExperimentStatus.CANCELLED,
    },
    ExperimentStatus.COMPLETED: set(),  # Terminal
    ExperimentStatus.FAILED: {ExperimentStatus.PROPOSED},  # Can retry proposal
    ExperimentStatus.INVALID: {ExperimentStatus.PROPOSED},  # Can redesign proposal
    ExperimentStatus.CANCELLED: set(),  # Terminal
}


class DiscoveryStateError(Exception):
    """Raised when an invalid state transition is requested."""

    def __init__(self, current_state: str, target_state: str, entity: str = "discovery"):
        super().__init__(f"Invalid {entity} state transition from '{current_state}' to '{target_state}'.")
        self.current_state = current_state
        self.target_state = target_state
        self.entity = entity


def can_transition_discovery(current: DiscoveryState, target: DiscoveryState) -> bool:
    """Check whether a discovery session transition is permissible."""
    if current == target:
        return True
    return target in DISCOVERY_TRANSITIONS.get(current, set())


def validate_discovery_transition(current: DiscoveryState, target: DiscoveryState) -> None:
    """Validate and raise if discovery session transition is invalid."""
    if not can_transition_discovery(current, target):
        raise DiscoveryStateError(current.value, target.value, entity="DiscoverySession")


def can_transition_experiment(current: ExperimentStatus, target: ExperimentStatus) -> bool:
    """Check whether an experiment transition is permissible."""
    if current == target:
        return True
    return target in EXPERIMENT_TRANSITIONS.get(current, set())


def validate_experiment_transition(current: ExperimentStatus, target: ExperimentStatus) -> None:
    """Validate and raise if experiment transition is invalid."""
    if not can_transition_experiment(current, target):
        raise DiscoveryStateError(current.value, target.value, entity="Experiment")


def is_discovery_terminal(state: DiscoveryState) -> bool:
    """Returns True if the discovery state is final."""
    return state in {DiscoveryState.COMPLETED, DiscoveryState.CANCELLED}


def is_experiment_terminal(status: ExperimentStatus) -> bool:
    """Returns True if the experiment status is final."""
    return status in {ExperimentStatus.COMPLETED, ExperimentStatus.CANCELLED}
