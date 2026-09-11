"""Unit tests for DiscoveryState and ExperimentStatus state machines (Task 72)."""

import pytest

from app.discovery.schemas import DiscoveryState, ExperimentStatus
from app.discovery.state_machine import (
    DiscoveryStateError,
    can_transition_discovery,
    can_transition_experiment,
    is_discovery_terminal,
    is_experiment_terminal,
    validate_discovery_transition,
    validate_experiment_transition,
)


def test_discovery_valid_linear_lifecycle():
    """Verifies standard scientific discovery state progression."""
    state = DiscoveryState.CREATED
    assert can_transition_discovery(state, DiscoveryState.QUESTION_FORMED)
    state = DiscoveryState.QUESTION_FORMED
    assert can_transition_discovery(state, DiscoveryState.HYPOTHESIS_GENERATED)
    state = DiscoveryState.HYPOTHESIS_GENERATED
    assert can_transition_discovery(state, DiscoveryState.EXPERIMENT_DESIGN)
    state = DiscoveryState.EXPERIMENT_DESIGN
    assert can_transition_discovery(state, DiscoveryState.READY)
    state = DiscoveryState.READY
    assert can_transition_discovery(state, DiscoveryState.RUNNING)
    state = DiscoveryState.RUNNING
    assert can_transition_discovery(state, DiscoveryState.OBSERVING)
    state = DiscoveryState.OBSERVING
    assert can_transition_discovery(state, DiscoveryState.ANALYZING)
    state = DiscoveryState.ANALYZING
    assert can_transition_discovery(state, DiscoveryState.VALIDATING)
    state = DiscoveryState.VALIDATING
    assert can_transition_discovery(state, DiscoveryState.CONCLUDED)
    state = DiscoveryState.CONCLUDED
    assert can_transition_discovery(state, DiscoveryState.KNOWLEDGE_UPDATE)
    state = DiscoveryState.KNOWLEDGE_UPDATE
    assert can_transition_discovery(state, DiscoveryState.COMPLETED)


def test_discovery_invalid_state_transition_raises():
    """Attempting an illegal transition must raise DiscoveryStateError."""
    # Cannot jump directly from CREATED to COMPLETED
    with pytest.raises(DiscoveryStateError) as exc_info:
        validate_discovery_transition(DiscoveryState.CREATED, DiscoveryState.COMPLETED)
    assert "Invalid DiscoverySession state transition" in str(exc_info.value)

    # Cannot jump from QUESTION_FORMED to RUNNING
    with pytest.raises(DiscoveryStateError):
        validate_discovery_transition(DiscoveryState.QUESTION_FORMED, DiscoveryState.RUNNING)


def test_discovery_terminal_states():
    """Terminal discovery states cannot transition further."""
    assert is_discovery_terminal(DiscoveryState.COMPLETED)
    assert is_discovery_terminal(DiscoveryState.CANCELLED)
    assert not is_discovery_terminal(DiscoveryState.RUNNING)

    with pytest.raises(DiscoveryStateError):
        validate_discovery_transition(DiscoveryState.COMPLETED, DiscoveryState.RUNNING)


def test_experiment_valid_execution_lifecycle():
    """Verifies standard experiment execution status progression."""
    status = ExperimentStatus.PROPOSED
    assert can_transition_experiment(status, ExperimentStatus.APPROVAL_REQUIRED)
    status = ExperimentStatus.APPROVAL_REQUIRED
    assert can_transition_experiment(status, ExperimentStatus.APPROVED)
    status = ExperimentStatus.APPROVED
    assert can_transition_experiment(status, ExperimentStatus.READY)
    status = ExperimentStatus.READY
    assert can_transition_experiment(status, ExperimentStatus.RUNNING)
    status = ExperimentStatus.RUNNING
    assert can_transition_experiment(status, ExperimentStatus.COMPLETED)


def test_experiment_invalid_execution_transition_raises():
    """Illegal experiment transitions must be strictly blocked."""
    with pytest.raises(DiscoveryStateError) as exc_info:
        validate_experiment_transition(ExperimentStatus.PROPOSED, ExperimentStatus.COMPLETED)
    assert "Invalid Experiment state transition" in str(exc_info.value)

    with pytest.raises(DiscoveryStateError):
        validate_experiment_transition(ExperimentStatus.APPROVAL_REQUIRED, ExperimentStatus.RUNNING)


def test_experiment_terminal_states():
    """Completed or Cancelled experiments cannot transition."""
    assert is_experiment_terminal(ExperimentStatus.COMPLETED)
    assert is_experiment_terminal(ExperimentStatus.CANCELLED)
    assert not is_experiment_terminal(ExperimentStatus.RUNNING)

    with pytest.raises(DiscoveryStateError):
        validate_experiment_transition(ExperimentStatus.COMPLETED, ExperimentStatus.RUNNING)
