"""Test suite for Attention Interruption and Preemption Engine (Task 70)."""

from app.attention.interrupt import InterruptionPolicyEngine
from app.attention.schemas import AttentionCandidate, AttentionMode, AttentionState
from app.attention.stack import AttentionStack


def test_critical_outage_interrupts_normal_task():
    """A critical production incident must immediately preempt a normal-priority background task."""
    current_task = AttentionCandidate(
        title="Background Data Indexing",
        attention_score=0.45,
        urgency=0.30,
        severity="LOW",
        current_state=AttentionState.ATTENDING,
    )

    incoming_incident = AttentionCandidate(
        title="Production Database Outage",
        attention_score=0.92,
        urgency=0.95,
        severity="CRITICAL",
        current_state=AttentionState.OBSERVED,
    )

    decision = InterruptionPolicyEngine.evaluate_interruption(
        incoming=incoming_incident,
        current=current_task,
        mode=AttentionMode.NORMAL_MODE,
    )

    assert decision.should_interrupt is True
    assert decision.incoming_id == incoming_incident.attention_id
    assert decision.current_id == current_task.attention_id
    assert "Critical safety/incident preemption" in decision.reason


def test_low_priority_item_does_not_interrupt():
    """A low-priority item must not interrupt active work."""
    current_task = AttentionCandidate(
        title="Feature Implementation",
        attention_score=0.70,
        urgency=0.65,
        severity="MEDIUM",
        current_state=AttentionState.ATTENDING,
    )

    incoming_low = AttentionCandidate(
        title="Minor Documentation Typo",
        attention_score=0.25,
        urgency=0.10,
        severity="LOW",
        current_state=AttentionState.OBSERVED,
    )

    decision = InterruptionPolicyEngine.evaluate_interruption(
        incoming=incoming_low,
        current=current_task,
        mode=AttentionMode.NORMAL_MODE,
    )

    assert decision.should_interrupt is False
    assert "does not overcome interruption cost" in decision.reason


def test_critical_commit_phase_protection():
    """A task executing a critical non-interruptible commit is protected from non-emergency interrupts."""
    current_task = AttentionCandidate(
        title="Database Schema Migration",
        attention_score=0.65,
        urgency=0.50,
        current_state=AttentionState.ATTENDING,
    )

    incoming_high = AttentionCandidate(
        title="High Priority Customer Query",
        attention_score=0.78,
        urgency=0.70,
        severity="HIGH",
        current_state=AttentionState.OBSERVED,
    )

    decision = InterruptionPolicyEngine.evaluate_interruption(
        incoming=incoming_high,
        current=current_task,
        current_phase="critical_commit",
    )

    assert decision.should_interrupt is False
    assert "non-interruptible critical commit phase" in decision.reason


def test_focus_mode_dampens_interrupts():
    """FOCUS_MODE requires a substantially higher score delta to interrupt ongoing work."""
    current_task = AttentionCandidate(
        title="Deep Reasoning Architecture Design",
        attention_score=0.60,
        urgency=0.40,
        current_state=AttentionState.ATTENDING,
    )

    incoming = AttentionCandidate(
        title="Slack Notification Digest",
        attention_score=0.70,
        urgency=0.50,
        current_state=AttentionState.OBSERVED,
    )

    # In NORMAL_MODE, delta 0.10 might be considered with urgency, but in FOCUS_MODE it must be blocked
    decision = InterruptionPolicyEngine.evaluate_interruption(
        incoming=incoming,
        current=current_task,
        mode=AttentionMode.FOCUS_MODE,
    )

    assert decision.should_interrupt is False
    assert "FOCUS_MODE active" in decision.reason


def test_preemption_state_preservation_and_resumption():
    """Interrupted task state is preserved via snapshot reference, pushed to stack, and cleanly resumed."""
    stack = AttentionStack()

    task_a = AttentionCandidate(
        title="Task A — Research",
        attention_score=0.55,
        current_state=AttentionState.OBSERVED,
    )
    stack.set_focus(task_a)
    assert stack.current_focus is not None
    assert stack.current_focus.attention_id == task_a.attention_id

    # Preempt Task A for Incident B
    incident_b = AttentionCandidate(
        title="Task B — Critical Outage",
        attention_score=0.95,
        urgency=0.95,
        current_state=AttentionState.OBSERVED,
    )

    # Push Task A to preemption stack with snapshot
    snapshot_id = "ctx-snap-task-a-preserved-001"
    stack.push_preemption(task_a, snapshot_id=snapshot_id)

    assert task_a.current_state == AttentionState.PAUSED
    assert task_a.context_snapshot_id == snapshot_id
    assert task_a.interruption_count == 1
    assert len(stack.preempted_stack) == 1

    # Focus Incident B
    stack.set_focus(incident_b)
    assert stack.current_focus.attention_id == incident_b.attention_id

    # Incident B is resolved -> pop preemption stack and resume Task A
    stack.current_focus.current_state = AttentionState.RESOLVED
    resumed = stack.pop_resume()

    assert resumed is not None
    assert resumed.attention_id == task_a.attention_id
    assert resumed.current_state == AttentionState.ATTENDING
    assert resumed.context_snapshot_id == snapshot_id
    assert stack.current_focus.attention_id == task_a.attention_id
