"""Unit tests for Reasoning State Machine & Lifecycle (Task 71)."""

import pytest

from app.reasoning.schemas import (
    ReasoningDepth,
    ReasoningSession,
    ReasoningState,
)
from app.reasoning.state_machine import (
    IllegalStateTransitionError,
    ReasoningStateMachine,
)


def test_reasoning_state_machine_happy_path():
    """Verify standard happy path progression across deliberation states."""
    sm = ReasoningStateMachine()
    session = ReasoningSession(
        question="Why did the API latency spike?",
        current_state=ReasoningState.CREATED,
    )

    # CREATED -> UNDERSTANDING
    assert sm.can_transition(session.current_state, ReasoningState.UNDERSTANDING)
    sm.transition(session, ReasoningState.UNDERSTANDING)
    assert session.current_state == ReasoningState.UNDERSTANDING

    # UNDERSTANDING -> DECOMPOSING
    sm.transition(session, ReasoningState.DECOMPOSING)
    assert session.current_state == ReasoningState.DECOMPOSING

    # DECOMPOSING -> HYPOTHESIS_GENERATION
    sm.transition(session, ReasoningState.HYPOTHESIS_GENERATION)
    assert session.current_state == ReasoningState.HYPOTHESIS_GENERATION

    # HYPOTHESIS_GENERATION -> EVIDENCE_COLLECTION
    sm.transition(session, ReasoningState.EVIDENCE_COLLECTION)
    assert session.current_state == ReasoningState.EVIDENCE_COLLECTION

    # EVIDENCE_COLLECTION -> EVIDENCE_EVALUATION
    sm.transition(session, ReasoningState.EVIDENCE_EVALUATION)
    assert session.current_state == ReasoningState.EVIDENCE_EVALUATION

    # EVIDENCE_EVALUATION -> DELIBERATING
    sm.transition(session, ReasoningState.DELIBERATING)
    assert session.current_state == ReasoningState.DELIBERATING

    # DELIBERATING -> CONCLUDING
    sm.transition(session, ReasoningState.CONCLUDING)
    assert session.current_state == ReasoningState.CONCLUDING

    # CONCLUDING -> VERIFYING
    sm.transition(session, ReasoningState.VERIFYING)
    assert session.current_state == ReasoningState.VERIFYING

    # VERIFYING -> COMPLETED
    sm.transition(session, ReasoningState.COMPLETED)
    assert session.current_state == ReasoningState.COMPLETED


def test_reasoning_state_machine_rejects_illegal_jump():
    """Verify strict rejection of invalid jumps (e.g. UNCERTAIN directly to VERIFYING or COMPLETED)."""
    sm = ReasoningStateMachine()
    session = ReasoningSession(
        question="Investigate database deadlock",
        current_state=ReasoningState.UNCERTAIN,
    )

    # UNCERTAIN cannot jump directly to VERIFYING
    assert not sm.can_transition(session.current_state, ReasoningState.VERIFYING)
    with pytest.raises(IllegalStateTransitionError):
        sm.transition(session, ReasoningState.VERIFYING)

    # UNCERTAIN cannot jump directly to COMPLETED
    assert not sm.can_transition(session.current_state, ReasoningState.COMPLETED)
    with pytest.raises(IllegalStateTransitionError):
        sm.transition(session, ReasoningState.COMPLETED)

    # CREATED cannot jump directly to CONCLUDING
    session.current_state = ReasoningState.CREATED
    with pytest.raises(IllegalStateTransitionError):
        sm.transition(session, ReasoningState.CONCLUDING)


def test_reasoning_terminal_states():
    """Verify terminal state detection (FAILED, ABORTED, COMPLETED)."""
    sm = ReasoningStateMachine()
    assert sm.is_terminal(ReasoningState.COMPLETED)
    assert sm.is_terminal(ReasoningState.FAILED)
    assert sm.is_terminal(ReasoningState.ABORTED)
    assert not sm.is_terminal(ReasoningState.DELIBERATING)
    assert not sm.is_terminal(ReasoningState.CONCLUDING)


def test_reasoning_depth_budget_initialization():
    """Verify cognitive resource budgeting per depth tier."""
    from app.reasoning.budget import BudgetCoordinator

    bc = BudgetCoordinator()

    quick = bc.initialize_budget(ReasoningDepth.QUICK)
    assert quick.max_depth == 1
    assert quick.max_iterations <= 5
    assert quick.max_tool_calls == 1

    standard = bc.initialize_budget(ReasoningDepth.STANDARD)
    assert standard.max_depth == 3
    assert standard.max_subproblems == 6

    critical = bc.initialize_budget(ReasoningDepth.CRITICAL)
    assert critical.max_depth == 4
    assert critical.max_latency_sec >= 120.0
    assert critical.max_tool_calls >= 10
