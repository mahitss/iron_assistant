"""Test suite for Attention Lifecycle, Stack, Fairness Aging, and Hysteresis (Task 70)."""

import pytest

from app.attention.lifecycle import AttentionLifecycleStateMachine, InvalidStateTransitionError
from app.attention.schemas import AttentionCandidate, AttentionState, AttentionThreshold
from app.attention.stack import AttentionStack


def test_12_state_valid_lifecycle_transitions():
    """Verify standard legal path through the 12 attention states."""
    # UNSEEN -> OBSERVED
    st = AttentionLifecycleStateMachine.transition(AttentionState.UNSEEN, AttentionState.OBSERVED)
    assert st == AttentionState.OBSERVED

    # OBSERVED -> QUEUED
    st = AttentionLifecycleStateMachine.transition(st, AttentionState.QUEUED)
    assert st == AttentionState.QUEUED

    # QUEUED -> ATTENDING
    st = AttentionLifecycleStateMachine.transition(st, AttentionState.ATTENDING)
    assert st == AttentionState.ATTENDING

    # ATTENDING -> PAUSED
    st = AttentionLifecycleStateMachine.transition(st, AttentionState.PAUSED)
    assert st == AttentionState.PAUSED

    # PAUSED -> ATTENDING (resumed)
    st = AttentionLifecycleStateMachine.transition(st, AttentionState.ATTENDING)
    assert st == AttentionState.ATTENDING

    # ATTENDING -> RESOLVED (terminal)
    st = AttentionLifecycleStateMachine.transition(st, AttentionState.RESOLVED)
    assert st == AttentionState.RESOLVED


def test_invalid_transitions_rejected():
    """Verify illegal transitions raise InvalidStateTransitionError."""
    # Cannot jump UNSEEN -> ATTENDING directly
    with pytest.raises(InvalidStateTransitionError):
        AttentionLifecycleStateMachine.transition(AttentionState.UNSEEN, AttentionState.ATTENDING)

    # Cannot jump DISMISSED -> ATTENDING directly
    with pytest.raises(InvalidStateTransitionError):
        AttentionLifecycleStateMachine.transition(AttentionState.DISMISSED, AttentionState.ATTENDING)

    # Reopening from terminal RESOLVED requires a new signal and must transition to OBSERVED first
    with pytest.raises(InvalidStateTransitionError):
        AttentionLifecycleStateMachine.transition(
            AttentionState.RESOLVED, AttentionState.QUEUED, has_new_signal=False
        )

    reopened = AttentionLifecycleStateMachine.transition(
        AttentionState.RESOLVED, AttentionState.OBSERVED, has_new_signal=True
    )
    assert reopened == AttentionState.OBSERVED


def test_attention_stack_and_queue_sorting():
    """Attention priority queue sorts candidates by score; stack manages LIFO preemption."""
    stack = AttentionStack()

    c1 = AttentionCandidate(
        title="Low priority task", attention_score=0.35, current_state=AttentionState.OBSERVED
    )
    c2 = AttentionCandidate(
        title="High priority incident",
        attention_score=0.88,
        urgency=0.9,
        current_state=AttentionState.OBSERVED,
    )
    c3 = AttentionCandidate(title="Medium task", attention_score=0.60, current_state=AttentionState.OBSERVED)

    stack.enqueue(c1)
    stack.enqueue(c2)
    stack.enqueue(c3)

    # Highest score dequeued first
    top = stack.dequeue_next()
    assert top is not None
    assert top.attention_id == c2.attention_id
    assert top.attention_score == 0.88

    second = stack.dequeue_next()
    assert second is not None
    assert second.attention_id == c3.attention_id

    third = stack.dequeue_next()
    assert third is not None
    assert third.attention_id == c1.attention_id


def test_fairness_aging_prevents_starvation():
    """Deferred candidates gain aging boost and are eventually restored to queue, preventing goal starvation."""
    stack = AttentionStack()

    cand = AttentionCandidate(
        title="Important but deferred maintenance",
        attention_score=0.40,
        current_state=AttentionState.OBSERVED,
    )
    stack.defer(cand, reason="Deferred for critical production work")

    assert cand.attention_id in stack.deferred_pool
    assert cand.current_state == AttentionState.DEFERRED
    assert cand.deferral_count == 1

    # Apply multiple aging cycles
    for _ in range(4):
        stack.apply_fairness_aging(boost_per_cycle=0.04)

    # Candidate should have accumulated aging boost and been re-enqueued automatically
    assert cand.aging_boost >= 0.12
    assert cand.attention_score > 0.40
    assert cand.current_state == AttentionState.QUEUED
    assert cand.attention_id not in stack.deferred_pool
    assert any(c.attention_id == cand.attention_id for c in stack.queue)


def test_hysteresis_dampens_alert_thrashing():
    """Hysteresis bands prevent rapid oscillation between NORMAL and HIGH around score boundary (0.70)."""
    stack = AttentionStack()
    cid = "cand-oscillating"

    # 1. Initially firmly NORMAL at score 0.65
    t1 = stack.check_hysteresis(cid, AttentionThreshold.NORMAL, 0.65, margin=0.04)
    assert t1 == AttentionThreshold.NORMAL

    # 2. Score nudges to 0.71 (just above 0.70 threshold, but within margin 0.70 + 0.04 = 0.74)
    # Should remain NORMAL, dampening thrashing
    t2 = stack.check_hysteresis(cid, AttentionThreshold.NORMAL, 0.71, margin=0.04)
    assert t2 == AttentionThreshold.NORMAL

    # 3. Score decisively exceeds margin (0.76 > 0.74) -> escalates to HIGH
    t3 = stack.check_hysteresis(cid, AttentionThreshold.HIGH, 0.76, margin=0.04)
    assert t3 == AttentionThreshold.HIGH

    # 4. Score dips to 0.69 (just below 0.70, but within margin 0.70 - 0.04 = 0.66)
    # Should remain HIGH, preventing premature de-escalation thrash
    t4 = stack.check_hysteresis(cid, AttentionThreshold.HIGH, 0.69, margin=0.04)
    assert t4 == AttentionThreshold.HIGH

    # 5. Score drops decisively below margin (0.64 < 0.66) -> de-escalates to NORMAL
    t5 = stack.check_hysteresis(cid, AttentionThreshold.HIGH, 0.64, margin=0.04)
    assert t5 == AttentionThreshold.NORMAL
