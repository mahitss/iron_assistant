"""Unit tests for Adaptation, Sunk Cost Defense, Progress, and Commitments (Task 58)."""

from __future__ import annotations

import pytest

from app.planning.adaptation import adaptation_engine
from app.planning.commitments import commitment_manager
from app.planning.engine import strategic_planning_engine
from app.planning.outcomes import outcome_tracker
from app.planning.progress import progress_tracker
from app.planning.schemas import (
    CurrentStateAssessment,
    DesiredStateDefinition,
    HealthStatus,
    TaskStatus,
)


def _build_test_plan():
    curr = CurrentStateAssessment(summary="Current")
    des = DesiredStateDefinition(summary="Target", completion_invariants=["Done"])
    return strategic_planning_engine.synthesize_strategic_plan(
        name="Test Strategic Plan",
        purpose="Testing adaptation",
        current_state=curr,
        desired_state=des,
    )


def test_drift_detection_and_sunk_cost_defense():
    plan = _build_test_plan()

    # Mark 2 tasks completed, 1 failed (2 out of 3 = 66% completed)
    plan.tasks[0].status = TaskStatus.COMPLETED
    plan.tasks[1].status = TaskStatus.COMPLETED
    plan.tasks[2].status = TaskStatus.FAILED

    drift = adaptation_engine.evaluate_drift(plan)

    assert drift["is_replanning_required"] is True
    assert drift["sunk_cost_defense_triggered"] is True
    assert any("SUNK COST DEFENSE ACTIVATED" in r for r in drift["reasons"])
    assert drift["health"] == HealthStatus.REPLANNING_REQUIRED


def test_outcome_based_progress_tracking():
    plan = _build_test_plan()

    # When 0 tasks or milestones are reached
    prog_initial = progress_tracker.compute_plan_progress(plan)
    assert prog_initial["composite_progress_pct"] == 0.0
    assert prog_initial["is_fully_completed"] is False

    # Complete 1 task out of 3, but 0 milestones verified
    plan.tasks[0].status = TaskStatus.COMPLETED
    prog_mid = progress_tracker.compute_plan_progress(plan)
    # 33.3% tasks * 0.30 weight = ~10% composite
    assert prog_mid["composite_progress_pct"] > 0.0
    assert prog_mid["composite_progress_pct"] < 25.0
    assert prog_mid["is_fully_completed"] is False


def test_commitment_authorization_boundary():
    cmt = commitment_manager.propose_commitment(
        plan_id="plan_123",
        title="Delivery SLA",
        description="Deliver by Q4",
    )
    assert cmt.status == "PROPOSED"
    assert cmt.is_authorized is False

    # Unauthorized role rejected
    ok, err = commitment_manager.authorize_commitment(cmt, authorizer="guest_user", authorizer_role="GUEST")
    assert ok is False
    assert cmt.is_authorized is False
    assert "lacks authority" in err

    # Authorized executive role approved
    ok, err = commitment_manager.authorize_commitment(cmt, authorizer="vp_engineering", authorizer_role="EXECUTIVE")
    assert ok is True
    assert cmt.is_authorized is True
    assert cmt.status == "AUTHORIZED"


def test_outcome_recording_and_calibration():
    plan = _build_test_plan()
    # Expected duration is sum of task duration_expected (1.0 + 2.5 + 1.5 = 5.0h)
    outcome = outcome_tracker.record_plan_outcome(
        plan=plan,
        success=True,
        actual_duration_hours=7.5,
        actual_cost=1200.0,
        lessons_learned=["Underestimated verification suite duration"],
    )

    assert outcome.success is True
    assert outcome.actual_duration == 7.5
    assert outcome.estimation_error == pytest.approx(0.5, 0.01)  # (7.5 - 5.0) / 5.0 = 0.50 (+50% overrun)

    calib_factor = outcome_tracker.get_calibration_factor()
    assert calib_factor > 1.0  # History shows things took longer than estimated
