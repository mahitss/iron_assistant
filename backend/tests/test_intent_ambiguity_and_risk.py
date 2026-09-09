"""Unit tests for Ambiguity Detection, Critical Risk Bounding, and Clarification Continuity (Spec 39-49, 143, 144, 148, 149, 159)."""

import pytest

from app.intent.ambiguity import AmbiguityAnalyzer
from app.intent.parser import IntentParser
from app.intent.schemas import AmbiguityLevel, IntentErrorState, IntentRiskLevel, IntentType


def test_ambiguity_two_repositories_asks_user():
    """Verify 'Deploy Kairo' with multiple matching repos triggers clarification with options (Spec 143)."""
    _, intent = IntentParser.parse_command(
        raw_text="Deploy Kairo",
        user_id="user_test_1",
        project_context={"name": "Kairo", "repositories": ["Kairo-prod", "Kairo-old"]},
    )

    assert intent.ambiguity.ambiguous is True
    assert intent.status == IntentErrorState.WAITING_USER.value
    # Options should be generated for the user
    options = intent.ambiguity.resolution_options
    assert len(options) >= 2
    option_labels = [opt.label for opt in options]
    assert "Kairo-prod" in option_labels
    assert "Kairo-old" in option_labels


def test_high_risk_delete_it_never_guesses():
    """Verify 'Delete it' with multiple candidates results in CRITICAL ambiguity without guessing (Spec 43, 44, 144)."""
    recent_artifacts = [
        {"id": "file_1", "name": "app.py"},
        {"id": "file_2", "name": "main.py"},
    ]

    _, intent = IntentParser.parse_command(
        raw_text="Delete it",
        user_id="user_test_1",
        recent_artifacts=recent_artifacts,
    )

    assert intent.type == IntentType.DELETE
    assert intent.risk == IntentRiskLevel.HIGH
    assert intent.ambiguity.ambiguous is True
    assert intent.ambiguity.level == AmbiguityLevel.CRITICAL
    assert intent.status == IntentErrorState.WAITING_USER.value
    # Target was NOT arbitrarily guessed
    assert intent.target is None or intent.target.stable_entity_id is None


def test_clarification_continuity_resolves_target():
    """Verify answering a clarification question reconstructs target safely (Spec 48, 149)."""
    # First turn: ambiguous
    _, intent1 = IntentParser.parse_command(
        raw_text="Deploy Kairo",
        user_id="user_test_1",
        project_context={"name": "Kairo", "repositories": ["Kairo-prod", "Kairo-staging"]},
    )
    assert intent1.ambiguity.ambiguous is True

    # Second turn with clarification answer
    _, intent2 = IntentParser.parse_command(
        raw_text="Deploy Kairo",
        user_id="user_test_1",
        project_context={"name": "Kairo", "repositories": ["Kairo-prod", "Kairo-staging"]},
        clarification_response="Kairo-staging",
    )

    assert intent2.ambiguity.ambiguous is False
    assert intent2.status == "READY"
    assert intent2.target is not None
    assert intent2.target.name == "Kairo-staging"


def test_clarification_loop_limit_prevents_infinite_recursion():
    """Verify bounded clarification attempts prevent infinite clarification loops (Spec 159)."""
    report = AmbiguityAnalyzer.analyze(
        intent_type=IntentType.TASK,
        risk_level=IntentRiskLevel.NORMAL,
        ambiguous_candidates=[{"reference": "the repo", "candidates": ["repoA", "repoB"]}],
        clarification_attempts=3,
    )

    assert report.ambiguous is True
    assert report.level == AmbiguityLevel.CRITICAL
    assert "clarification_limit_reached" in report.missing_information
    assert len(report.resolution_options) == 0
