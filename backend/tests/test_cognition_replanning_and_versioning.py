"""Unit tests for adaptive replanning, monotonic versioning, diff calculation, and approval invalidation (Task 41)."""

import pytest
from app.cognition.planner import CognitivePlanner
from app.cognition.plans import PlanRiskLevel, PlanStatus
from app.cognition.replanner import PlanReplanner, ReplanReason, ReplanRequest
from app.cognition.steps import PlanStep, StepRiskLevel


def test_replan_creates_monotonic_version_and_supersedes_old():
    planner = CognitivePlanner()
    goal = planner.create_goal(description="Deploy production cluster", user_id="admin_1")
    plan_v1, _, _ = planner.build_plan(goal)

    assert plan_v1.version == 1
    assert plan_v1.status == PlanStatus.READY

    # Trigger re-plan
    plan_v2, diff = planner.replan_plan(
        plan_id=plan_v1.plan_id,
        reason=ReplanReason.STATE_CHANGE,
        failure_description="Target cluster returned 503 Service Unavailable",
    )

    # v2 checks
    assert plan_v2.version == 2
    assert plan_v2.parent_plan_id == plan_v1.plan_id
    assert plan_v2.status == PlanStatus.READY

    # v1 is superseded
    assert plan_v1.status == PlanStatus.SUPERSEDED

    # Diff verification
    assert diff.old_version == 1
    assert diff.new_version == 2
    assert diff.old_plan_id == plan_v1.plan_id
    assert diff.new_plan_id == plan_v2.plan_id


def test_approval_invalidation_on_increased_risk():
    planner = CognitivePlanner()
    goal = planner.create_goal(description="Read metrics", user_id="user_1")
    plan_v1, _, _ = planner.build_plan(goal, override_risk=PlanRiskLevel.LOW)

    # Old plan was LOW risk
    assert plan_v1.risk == PlanRiskLevel.LOW

    # Create new steps with a DESTRUCTIVE action
    destructive_step = PlanStep(
        step_id="destruct_1",
        plan_id="temp",
        sequence=1,
        objective="Drop stale cache partition",
        action="drop_cache",
        risk=StepRiskLevel.DESTRUCTIVE,
    )

    req = ReplanRequest(plan_id=plan_v1.plan_id, reason=ReplanReason.NEW_INFORMATION)
    plan_v2, diff = PlanReplanner.replan(
        old_plan=plan_v1,
        request=req,
        new_steps=[destructive_step],
        new_risk=PlanRiskLevel.HIGH,
    )

    # Risk increased: approval MUST be required again (Spec 87, 88)
    assert diff.approval_required is True
    assert diff.new_risk == PlanRiskLevel.HIGH.value
