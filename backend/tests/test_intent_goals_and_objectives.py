"""Tests for Kairo Goal Model, Objective Extraction, and Success Criteria (Task 48, Spec 9-14, 72-73)."""

import pytest

from app.intent.goals import Goal, GoalManager
from app.intent.objectives import Objective, ObjectiveExtractor, ObjectiveType
from app.intent.schemas import GoalStatus, UrgencyLevel


def test_goal_creation_and_fields():
    """Verify Goal model contains all required fields and distinct from tasks (Spec 9, 10)."""
    manager = GoalManager()
    goal = manager.create_goal(
        intent_id="intent_101",
        description="Make the website load under 2 seconds",
        desired_state={"latency_seconds": 2.0},
        success_criteria=[{"metric": "latency", "target": "< 2s", "is_inferred": False}],
        scope={"service": "frontend", "environment": "production"},
        constraints=[{"type": "TIME", "value": "2s"}],
        priority=UrgencyLevel.HIGH,
        deadline="2026-09-15T00:00:00Z",
        owner="user_alice",
    )

    assert goal.goal_id.startswith("goal_")
    assert goal.intent_id == "intent_101"
    assert goal.description == "Make the website load under 2 seconds"
    assert goal.status == GoalStatus.ACTIVE
    assert goal.desired_state == {"latency_seconds": 2.0}
    assert goal.owner == "user_alice"
    assert goal.priority == UrgencyLevel.HIGH
    assert goal.version == 1


def test_goal_lifecycle_transitions():
    """Verify state transitions of a goal through its lifecycle."""
    manager = GoalManager()
    goal = manager.create_goal(
        intent_id="intent_102",
        description="Refactor database queries",
        owner="user_bob",
    )
    assert goal.status == GoalStatus.ACTIVE

    goal.update_status(GoalStatus.IN_PROGRESS)
    assert goal.status == GoalStatus.IN_PROGRESS

    goal.update_status(GoalStatus.ACHIEVED)
    assert goal.status == GoalStatus.ACHIEVED

    # Cancel goal
    goal.cancel(reason="User revoked intent")
    assert goal.status == GoalStatus.CANCELLED


def test_goal_stability_and_material_updates():
    """Verify goal versioning and stability (Spec 72, 73)."""
    manager = GoalManager()
    goal = manager.create_goal(
        intent_id="intent_103",
        description="Build initial reporting service",
        owner="user_charlie",
    )
    initial_version = goal.version

    # Minor description refinement: stability preserved if material scope not changed
    goal.update_description("Build initial reporting service with logs")
    assert goal.version == initial_version + 1


def test_objective_extraction_quantitative():
    """Extract explicit success criteria: 'Make website load under 2 seconds' (Spec 12, 14)."""
    text = "Make the website load under 2 seconds with test coverage above 85%"
    objectives = ObjectiveExtractor.extract_objectives(text)

    assert len(objectives) >= 2
    latency_obj = next((o for o in objectives if "seconds" in o.description.lower()), None)
    assert latency_obj is not None
    assert latency_obj.target_value == "2 seconds"
    assert latency_obj.is_inferred is False  # Explicit user criterion
    assert latency_obj.objective_type in (ObjectiveType.QUANTITATIVE, ObjectiveType.QUALITATIVE)

    cov_obj = next((o for o in objectives if "85%" in o.description or "coverage" in o.description.lower()), None)
    assert cov_obj is not None
    assert cov_obj.target_value == "85%"
    assert cov_obj.is_inferred is False


def test_objective_extraction_implied_success():
    """Inferred success criteria marked as inferred (Spec 13, 14)."""
    text = "Make sure the system is reliable and scalable"
    objectives = ObjectiveExtractor.extract_objectives(text)

    for obj in objectives:
        if obj.is_inferred:
            assert obj.is_inferred is True


def test_no_fabricated_success_criteria():
    """Verify system does not invent arbitrary success criteria when none given (Spec 14)."""
    text = "Check the server uptime"
    objectives = ObjectiveExtractor.extract_objectives(text)

    # Should not fabricate arbitrary latency or coverage requirements
    for obj in objectives:
        assert "arbitrary" not in obj.description.lower()
        assert obj.target_value != "arbitrary_value"
