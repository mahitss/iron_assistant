"""Test suite for Lesson Extraction, Scope Containment, and Anti-Overgeneralization (Task 52)."""

import pytest

from app.learning.corrections import CorrectionHandler
from app.learning.feedback import FeedbackProcessor
from app.learning.generalization import GeneralizationGuard, OvergeneralizationError
from app.learning.lessons import LessonExtractor
from app.learning.schemas import (
    FeedbackType,
    GeneralizationScope,
    LessonStatus,
    LessonType,
)


def test_lesson_extraction_requires_empirical_evidence():
    """INVARIANT 120: Never extract/fabricate lessons without source experiences or empirical evidence."""
    extractor = LessonExtractor()
    with pytest.raises(ValueError, match="INVARIANT 120"):
        extractor.extract_lesson(
            statement="Always check dependency compatibility",
            lesson_type=LessonType.SUCCESS_PATTERN,
            source_experiences=[],
            evidence=[],
        )


def test_lesson_extraction_and_reinforcement_and_supersession():
    """Verify complete lesson lifecycle: extraction, reinforcement, and supersession."""
    extractor = LessonExtractor()
    lesson1 = extractor.extract_lesson(
        statement="Run lint before pushing code to main",
        lesson_type=LessonType.PLANNING_PATTERN,
        source_experiences=["exp-1"],
        evidence=[{"result": "lint error caught before CI"}],
        confidence=0.7,
        scope=GeneralizationScope.PROJECT,
    )

    assert lesson1.lesson_id.startswith("lsn_")
    assert lesson1.reinforcement_count == 1
    assert lesson1.confidence == 0.7

    # Reinforce with new evidence
    reinforced = extractor.reinforce_lesson(lesson1.lesson_id, {"result": "saved CI rerun"})
    assert reinforced.reinforcement_count == 2
    assert reinforced.confidence == 0.75
    assert len(reinforced.evidence) == 2

    # Supersede with improved lesson
    lesson2 = extractor.extract_lesson(
        statement="Run pre-commit hooks containing lint and format before pushing",
        lesson_type=LessonType.PLANNING_PATTERN,
        source_experiences=["exp-2"],
        evidence=[{"result": "pre-commit caught both format and lint"}],
        confidence=0.85,
        scope=GeneralizationScope.PROJECT,
    )
    extractor.supersede_lesson(lesson1.lesson_id, lesson2.lesson_id, reason="More comprehensive check")

    old_lesson = extractor.get_lesson(lesson1.lesson_id)
    assert old_lesson.status == LessonStatus.SUPERSEDED
    assert old_lesson.validity["superseded_by"] == lesson2.lesson_id


def test_anti_overgeneralization_single_event_blocked_for_global():
    """INVARIANT 14 & 18: One event cannot create broad/global rules."""
    # Attempting to generalize 1 experience to GLOBAL scope must raise OvergeneralizationError
    with pytest.raises(OvergeneralizationError, match="INVARIANT 14 & 18"):
        GeneralizationGuard.validate_generalization(
            target_scope=GeneralizationScope.GLOBAL,
            experience_count=1,
            is_explicit_user_directive=False,
            is_verified_pattern=False,
        )

    # 5 verified experiences allow GLOBAL scope
    assert GeneralizationGuard.validate_generalization(
        target_scope=GeneralizationScope.GLOBAL,
        experience_count=5,
        is_explicit_user_directive=False,
        is_verified_pattern=True,
    ) is True


def test_anti_overgeneralization_user_preference_requires_repetition():
    """INVARIANT 20: Weak/single behavior cannot be promoted into permanent USER preference."""
    with pytest.raises(OvergeneralizationError, match="INVARIANT 20"):
        GeneralizationGuard.validate_generalization(
            target_scope=GeneralizationScope.USER,
            experience_count=1,
            is_explicit_user_directive=False,
        )

    # 3 repetitions qualify for USER preference
    assert GeneralizationGuard.validate_generalization(
        target_scope=GeneralizationScope.USER,
        experience_count=3,
        is_explicit_user_directive=False,
    ) is True


def test_cross_user_isolation_blocks_leakage():
    """INVARIANT 133: Never transfer private user learning to another user."""
    with pytest.raises(PermissionError, match="Cross-user learning leakage detected"):
        GeneralizationGuard.assert_cross_user_isolation("user-alice", "user-bob", GeneralizationScope.USER)

    # Same user is allowed
    GeneralizationGuard.assert_cross_user_isolation("user-alice", "user-alice", GeneralizationScope.USER)


def test_feedback_weighting_and_user_overrides():
    """INVARIANT 26, 27, 29, 122: Explicit feedback > passive behavior; explicit instruction overrides learned preference."""
    processor = FeedbackProcessor()

    # Passive observation gets low weight (0.1)
    rec_passive = processor.process_feedback(
        target_id="strat-1",
        feedback_type=FeedbackType.APPROVE,
        user_id="user-1",
        is_explicit=False,
    )
    assert rec_passive["weight"] == 0.1

    # Explicit correction gets full weight (1.0)
    rec_explicit = processor.process_feedback(
        target_id="strat-1",
        feedback_type=FeedbackType.CORRECT,
        user_id="user-1",
        comment="Don't use verbose logging here",
        is_explicit=True,
    )
    assert rec_explicit["weight"] == 1.0

    # User edit pattern tracking
    for _ in range(3):
        processor.process_feedback(
            target_id="draft-1",
            feedback_type=FeedbackType.EDIT,
            user_id="user-1",
            edit_diff={"tone": "concise"},
        )
    candidate_prefs = processor.get_candidate_preference_from_edits("user-1", min_repetitions=3)
    assert len(candidate_prefs) == 1

    # Current explicit instruction overrides learned preference
    overridden, msg = processor.enforce_user_override(
        learned_preference={"tone": "concise"},
        current_explicit_instruction="Make this formal and detailed",
    )
    assert overridden is True
    assert "Make this formal and detailed" in msg


def test_user_correction_scope_disambiguation():
    """INVARIANT 22-24: Explicit negative directives disambiguate scope and prompt when ambiguous."""
    handler = CorrectionHandler()

    # Ambiguous directive prompts user
    record = handler.handle_correction(
        target_action="generate_chart",
        user_directive="Don't ever do that again!",
    )
    assert record.is_ambiguous is True
    assert record.clarification_prompt is not None
    assert record.scope == GeneralizationScope.TASK  # Defaults to narrowest reasonable scope

    # Scoped directive cleanly resolves
    record2 = handler.handle_correction(
        target_action="delete_branch",
        user_directive="Don't do that in this project",
    )
    assert record2.is_ambiguous is False
    assert record2.scope == GeneralizationScope.PROJECT
