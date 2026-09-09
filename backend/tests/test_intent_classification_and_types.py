"""Unit tests for Intent Classification across all 21 IntentTypes and deterministic commands (Spec 4, 5, 50, 51)."""

import pytest

from app.intent.classifier import CommandClassifier
from app.intent.schemas import IntentType


@pytest.mark.parametrize(
    "text,expected_type",
    [
        ("cancel the task", IntentType.CANCEL),
        ("stop it", IntentType.CANCEL),
        ("abort operation", IntentType.CANCEL),
        ("pause the task", IntentType.PAUSE),
        ("hold on", IntentType.PAUSE),
        ("resume the task", IntentType.RESUME),
        ("continue", IntentType.RESUME),
        ("try again", IntentType.RETRY),
        ("do that again", IntentType.RETRY),
        ("approve it", IntentType.APPROVE),
        ("lgtm", IntentType.APPROVE),
        ("reject it", IntentType.REJECT),
        ("deny the deployment", IntentType.REJECT),
        ("summarize this report", IntentType.SUMMARIZE),
        ("compare these two configs", IntentType.COMPARE),
        ("explain what this error means", IntentType.EXPLAIN),
        ("find the failing CI log", IntentType.SEARCH),
        ("open the deployment page", IntentType.NAVIGATE),
        ("delete the test database", IntentType.DELETE),
        ("update the staging replica count", IntentType.UPDATE),
        ("create a status summary", IntentType.CREATE),
        ("every morning check CI status", IntentType.AUTOMATE),
        ("remind me to review the pull request", IntentType.REMIND),
        ("what is kubernetes?", IntentType.QUESTION),
        ("investigate why the build is broken", IntentType.TASK),
        ("fix the failing test suite", IntentType.TASK),
    ],
)
def test_deterministic_intent_classification(text: str, expected_type: IntentType):
    """Verify high-frequency commands are deterministically and safely classified (Spec 50, 51)."""
    assert CommandClassifier.classify(text) == expected_type


def test_all_intent_types_defined():
    """Verify all 21 required intent types are exposed in IntentType enum (Spec 4)."""
    expected_all = {
        "QUESTION", "REQUEST", "TASK", "SEARCH", "CREATE", "UPDATE", "DELETE",
        "CONTROL", "NAVIGATE", "ANALYZE", "SUMMARIZE", "COMPARE", "EXPLAIN",
        "AUTOMATE", "REMIND", "APPROVE", "REJECT", "CANCEL", "PAUSE", "RESUME", "RETRY",
    }
    actual = {t.value for t in IntentType}
    assert expected_all.issubset(actual)
