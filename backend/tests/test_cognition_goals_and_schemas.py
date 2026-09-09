"""Unit tests for Cognitive Goal domain models, scopes, and schemas (Task 41)."""

import pytest
from app.cognition.goals import Goal, GoalPriority, GoalScope, GoalStatus, GoalType


def test_goal_creation_and_defaults():
    scope = GoalScope(user_id="user_123", project_id="proj_abc", allowed_resources=["src/"])
    goal = Goal(
        description="Prepare my project for production.",
        goal_type=GoalType.OPERATIONAL,
        priority=GoalPriority.HIGH,
        scope=scope,
    )

    assert goal.goal_id.startswith("goal_")
    assert goal.status == GoalStatus.PENDING
    assert goal.priority == GoalPriority.HIGH
    assert goal.goal_type == GoalType.OPERATIONAL
    assert len(goal.success_criteria) >= 1
    assert "src/" in goal.scope.allowed_resources


def test_goal_success_criteria_enforcement():
    scope = GoalScope(user_id="user_456")
    # Empty success criteria automatically defaults to measurable criteria
    goal = Goal(
        description="Verify service readiness",
        success_criteria=[],
        scope=scope,
    )
    assert len(goal.success_criteria) == 1
    assert "verified" in goal.success_criteria[0].lower()


def test_goal_types_enumeration():
    expected_types = {
        "INFORMATIONAL", "ANALYTICAL", "CREATIVE", "OPERATIONAL",
        "MAINTENANCE", "DEVELOPMENT", "AUTOMATION", "RESEARCH", "MULTI_STEP"
    }
    actual_types = {gt.value for gt in GoalType}
    assert expected_types == actual_types
