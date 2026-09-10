"""Test suite for Kairo Continuous Learning Experiences and Outcome Evaluation (Task 52)."""

from datetime import datetime, timezone
import pytest

from app.learning.experiences import Experience, ExperienceManager
from app.learning.outcomes import LearningOutcome, OutcomeEvaluator
from app.learning.schemas import ExperienceSource, ExperienceStatus


def test_experience_creation_with_task52_fields():
    """Verify Experience model supports full Task 52 fields."""
    exp = Experience(
        task_id="task-101",
        intent_id="intent-99",
        goal_id="goal-42",
        context_refs=["ctx-auth-service", "proj-kairo"],
        actions=[{"tool": "run_command", "args": {"cmd": "pytest"}}],
        outcome="SUCCESS",
        verification={"verified": True, "method": "automated_tests"},
        environment={"os": "linux", "runtime": "python3.11"},
        provenance={"recorded_by": "test_runner"},
        privacy_scope="PROJECT",
        status=ExperienceStatus.RAW,
        source=ExperienceSource.SYSTEM,
    )

    assert exp.experience_id.startswith("exp_")
    assert exp.task_id == "task-101"
    assert exp.intent_id == "intent-99"
    assert exp.goal_id == "goal-42"
    assert len(exp.context_refs) == 2
    assert exp.status == ExperienceStatus.RAW
    assert exp.source == ExperienceSource.SYSTEM
    assert exp.verification["verified"] is True


def test_experience_manager_crud_and_status_transitions():
    """Verify experience manager records, retrieves, and updates status cleanly."""
    mgr = ExperienceManager()
    exp = mgr.record_experience(
        task_id="task-102",
        actions=[{"action": "deploy"}],
        outcome="SUCCESS",
        verification={"verified": True},
        source=ExperienceSource.AGENT,
        privacy_scope="USER",
    )

    assert mgr.get_experience(exp.experience_id) is not None
    assert exp.status == ExperienceStatus.RAW

    # Transition to EVALUATED
    updated = mgr.update_status(exp.experience_id, ExperienceStatus.EVALUATED)
    assert updated.status == ExperienceStatus.EVALUATED

    # Transition to CONSOLIDATED
    consolidated = mgr.update_status(exp.experience_id, ExperienceStatus.CONSOLIDATED)
    assert consolidated.status == ExperienceStatus.CONSOLIDATED

    # Filter by status and source
    list_res = mgr.list_experiences(status=ExperienceStatus.CONSOLIDATED)
    assert len(list_res) == 1
    assert list_res[0].experience_id == exp.experience_id

    # Expiration
    expired = mgr.update_status(exp.experience_id, ExperienceStatus.EXPIRED)
    assert expired.status == ExperienceStatus.EXPIRED


def test_outcome_evaluator_expected_vs_actual_match():
    """Verify outcome evaluation calculates zero deviation when actual matches expected."""
    evaluator = OutcomeEvaluator()
    expected = {"http_status": 200, "error_count": 0}
    actual = {"http_status": 200, "error_count": 0}

    outcome = evaluator.evaluate(
        expected=expected,
        actual=actual,
        verification_telemetry={"tests_passed": True},
        task_id="task-eval-1",
    )

    assert isinstance(outcome, LearningOutcome)
    assert outcome.deviation == 0.0
    assert outcome.verified is True
    assert outcome.expected == expected
    assert outcome.actual == actual


def test_outcome_evaluator_deviation_and_unverified():
    """Verify outcome evaluator computes partial deviation and flags unverified outcome."""
    evaluator = OutcomeEvaluator()
    expected = {"http_status": 200, "rows_migrated": 100}
    actual = {"http_status": 200, "rows_migrated": 50}

    outcome = evaluator.evaluate(
        expected=expected,
        actual=actual,
        verification_telemetry={"tests_passed": False},
        task_id="task-eval-2",
    )

    assert outcome.deviation > 0.0
    assert outcome.verified is False
    assert outcome.learning_trust_weight < 0.5  # unverified has lower trust weight


def test_outcome_evaluator_unknown_outcome_not_treated_as_failure():
    """Unknown outcome is not automatically failure."""
    evaluator = OutcomeEvaluator()
    expected = {"status": "completed"}
    actual = {"status": "unknown", "reason": "remote server disconnected before ack"}

    outcome = evaluator.evaluate(
        expected=expected,
        actual=actual,
        verification_telemetry=None,
    )

    assert outcome.verified is False
    # Verify deviation reflects uncertainty without throwing critical safety failure
    assert outcome.deviation <= 1.0
