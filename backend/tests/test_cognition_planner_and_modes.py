"""Unit tests for reasoning modes, decomposition, and plan building (Task 41)."""

import pytest
from app.cognition.goals import Goal, GoalPriority, GoalScope, GoalType
from app.cognition.planner import CognitivePlanner
from app.cognition.plans import PlanRiskLevel, PlanStatus
from app.cognition.reasoning import ReasoningEngine, ReasoningMode
from app.cognition.steps import StepRiskLevel


def test_reasoning_mode_selection():
    # Diagnostic
    mode_diag = ReasoningEngine.select_mode("Fix failing CI pipeline in repository", "DEVELOPMENT")
    assert mode_diag == ReasoningMode.DIAGNOSTIC

    # Research
    mode_res = ReasoningEngine.select_mode("Research latest WebAssembly benchmarks", "RESEARCH")
    assert mode_res == ReasoningMode.RESEARCH

    # Direct
    mode_direct = ReasoningEngine.select_mode("Check status", "OPERATIONAL", is_complex=False)
    assert mode_direct == ReasoningMode.DIRECT

    # Decomposition
    mode_decomp = ReasoningEngine.select_mode("Prepare complete project deployment", "OPERATIONAL")
    assert mode_decomp == ReasoningMode.DECOMPOSITION


def test_planner_build_diagnostic_plan():
    planner = CognitivePlanner()
    goal = planner.create_goal(
        description="Fix failing CI run in backend",
        user_id="dev_user",
        project_id="proj_1",
    )

    plan, validation, alternatives = planner.build_plan(goal)

    assert plan.plan_id.startswith("plan_")
    assert plan.version == 1
    assert plan.reasoning_mode == ReasoningMode.DIAGNOSTIC.value
    assert len(plan.steps) >= 4

    # Verify Read-First: first step must be READ
    assert plan.steps[0].risk == StepRiskLevel.READ
    assert "inspect" in plan.steps[0].objective.lower()

    # Validation must be successful
    assert validation.is_valid
    assert validation.is_feasible
    assert validation.quality_score >= 0.8

    # Alternatives must be generated
    assert len(alternatives) >= 2
    assert any(alt.name == "Low-Risk Hardened Path" for alt in alternatives)
