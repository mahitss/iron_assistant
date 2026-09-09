"""Tests for Multi-Factor Budgets, SLA Deadlines, Progress Tracking, and Loop Detection (Task 45)."""

from datetime import datetime, timedelta, timezone
import pytest
from app.autonomy.budgets import (
    AutonomousBudget,
    BudgetExhaustedError,
)
from app.autonomy.deadlines import (
    DeadlineExhaustedError,
    DeadlineTracker,
)
from app.autonomy.progress import (
    NoProgressLoopError,
    ProgressTracker,
)


def test_multifactor_budget_tracking_and_exhaustion():
    """Verify resource quotas: model calls, tool calls, costs, and pre-check enforcement (Spec 54-56)."""
    b = AutonomousBudget(max_model_calls=5, max_tool_calls=3, max_cost_usd=1.0)
    assert b.is_exhausted is False

    # Consume safely
    b.check_and_consume(model_calls=2, tool_calls=1, cost_usd=0.20)
    assert b.used_model_calls == 2
    assert b.used_tool_calls == 1

    # Over-consumption raises BudgetExhaustedError before mutating
    with pytest.raises(BudgetExhaustedError):
        b.check_and_consume(tool_calls=5)  # Would exceed max_tool_calls (3)

    # Derive child budget (Spec 55)
    child_b = b.derive_child_budget(fraction=0.5)
    assert child_b.max_model_calls <= b.max_model_calls
    assert child_b.max_tool_calls <= b.max_tool_calls


def test_deadline_tracking_and_step_propagation():
    """Verify SLA deadline expiration and step timeout allocation (Spec 51-53)."""
    future = datetime.now(timezone.utc) + timedelta(minutes=10)
    dt = DeadlineTracker(deadline=future)
    assert dt.is_expired is False
    assert dt.remaining_seconds > 0

    # Propagated timeout bounds sub-step to safe fraction of remaining SLA
    step_to = dt.propagate_step_timeout(max_step_timeout=30.0)
    assert step_to <= 30.0

    # Expired deadline raises DeadlineExhaustedError
    past = datetime.now(timezone.utc) - timedelta(seconds=1)
    dt_expired = DeadlineTracker(deadline=past)
    assert dt_expired.is_expired is True
    with pytest.raises(DeadlineExhaustedError):
        dt_expired.validate_deadline()


def test_progress_calculation_and_no_fake_progress():
    """Verify objective progress based on verified work, not model calls (Spec 57-61)."""
    pt = ProgressTracker()
    snapshot = pt.calculate_progress(
        total_steps=10,
        completed_steps=5,
        total_criteria=2,
        verified_criteria=1,
        verified_artifacts=3,
    )
    # 5/10 steps = 50%, 1/2 criteria = 50% -> overall = 50%
    assert snapshot.percentage == 50.0
    assert "5/10 steps finished" in snapshot.summary


def test_no_progress_and_oscillating_loop_detection():
    """Verify loop detection: stagnation across cycles and A -> B -> A -> B patterns (Spec 148-152)."""
    pt = ProgressTracker(max_stagnant_cycles=3)

    # Stagnant cycles without completing any new steps
    pt.record_step_execution("step_1", completed_count=1)
    pt.record_step_execution("step_1", completed_count=1)
    pt.record_step_execution("step_1", completed_count=1)
    with pytest.raises(NoProgressLoopError, match="No verified progress made"):
        pt.record_step_execution("step_1", completed_count=1)

    # Oscillating loop: step_A -> step_B -> step_A -> step_B -> step_A -> step_B
    pt_osc = ProgressTracker(max_stagnant_cycles=10)
    pt_osc.record_step_execution("step_A", completed_count=1)
    pt_osc.record_step_execution("step_B", completed_count=2)
    pt_osc.record_step_execution("step_A", completed_count=3)
    pt_osc.record_step_execution("step_B", completed_count=4)
    pt_osc.record_step_execution("step_A", completed_count=5)
    with pytest.raises(NoProgressLoopError, match="Repeating execution pattern"):
        pt_osc.record_step_execution("step_B", completed_count=6)
