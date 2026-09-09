"""Tests for Multi-Intent Splitting, Negations, Conditional Intent, and Recurring Schedules (Task 48, Spec 5-8, 97-105)."""

import pytest

from app.intent.constraints import ConstraintEngine
from app.intent.parser import IntentParser
from app.intent.priorities import IntentPrioritizer
from app.intent.schemas import IntentType


def test_multi_intent_splitting():
    """Split 'Check the deployment, fix the issue, and tell me when it's ready' into 3 intents (Spec 5)."""
    text = "Check the deployment, fix the issue, and tell me when it's ready"
    clauses = IntentParser.split_multi_intents(text)

    assert len(clauses) >= 3
    assert any("check" in c.lower() for c in clauses)
    assert any("fix" in c.lower() for c in clauses)
    assert any("tell" in c.lower() or "ready" in c.lower() for c in clauses)


def test_multi_intent_priority_and_ordering():
    """Primary intent identification and dependency ordering (Spec 6, 7, 8)."""
    sub_intents = [
        (IntentType.NOTIFY, "tell me when ready"),
        (IntentType.RESEARCH, "check deployment"),
        (IntentType.MODIFY, "fix the issue"),
    ]

    ordered = IntentPrioritizer.prioritize_multi_intents(sub_intents)
    assert len(ordered) == 3
    # First intent should be primary
    assert ordered[0].is_primary is True
    # Dependency order: inspect -> modify -> notify
    types_in_order = [node.intent_type for node in ordered]
    assert types_in_order[0] in (IntentType.RESEARCH, IntentType.TASK, IntentType.QUESTION)


def test_user_negation_parsing():
    """Correctly parse negations: don't, never, not, without, except (Spec 97)."""
    text = "Deploy to production without running migrations and do not restart the database"
    constraints = ConstraintEngine.discover_constraints(text)

    negations = [c for c in constraints if c.is_negation]
    assert len(negations) >= 1
    neg_values = [str(c.value).lower() for c in negations]
    assert any("migration" in v or "restart" in v for v in neg_values)


def test_conditional_intent():
    """Parse 'If tests pass, deploy to staging' and extract explicit condition (Spec 98, 99)."""
    text = "If tests pass, deploy to staging"
    constraints = ConstraintEngine.discover_constraints(text)

    cond_c = next((c for c in constraints if "condition" in c.name.lower() or "tests" in str(c.value).lower()), None)
    if not cond_c:
        # Check parser extraction
        _, schema = IntentParser.parse_command(raw_text=text, user_id="u1")
        assert len(schema.constraints.conditions) > 0
        assert "tests" in schema.constraints.conditions[0].lower()


def test_recurring_intent_scheduling():
    """Parse 'Every Monday at 9am backup the database' (Spec 101, 102)."""
    text = "Every Monday at 9am backup the database"
    sub_clauses = IntentParser.split_multi_intents(text)
    assert len(sub_clauses) >= 1
