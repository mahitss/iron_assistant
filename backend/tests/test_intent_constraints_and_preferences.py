"""Tests for Constraint Discovery, Conflict Detection, and Preference Overrides (Task 48, Spec 15-24, 121)."""

import pytest

from app.intent.constraints import (
    ConstraintCategory,
    ConstraintEngine,
    ConstraintPriority,
    DiscoveredConstraint,
)
from app.intent.preferences import (
    PreferenceConfidence,
    PreferenceResolver,
    PreferenceScope,
    UserPreference,
)
from app.intent.schemas import ConstraintType


def test_constraint_extraction_categories():
    """Verify discovery of budget, time, format, and technology constraints (Spec 15, 16)."""
    text = "Deploy the container using Docker with budget under $500 before 5pm in JSON format"
    constraints = ConstraintEngine.discover_constraints(text)

    categories = {c.category for c in constraints}
    assert ConstraintCategory.BUDGET in categories
    assert ConstraintCategory.TIME in categories
    assert ConstraintCategory.TECHNOLOGY in categories
    assert ConstraintCategory.FORMAT in categories

    # Budget constraint verification
    budget_c = next(c for c in constraints if c.category == ConstraintCategory.BUDGET)
    assert "$500" in str(budget_c.value)
    assert budget_c.constraint_type == ConstraintType.HARD


def test_constraint_conflict_detection():
    """Detect contradictory constraints (Spec 18)."""
    c1 = DiscoveredConstraint(
        name="format_json",
        category=ConstraintCategory.FORMAT,
        constraint_type=ConstraintType.HARD,
        value="json",
    )
    c2 = DiscoveredConstraint(
        name="format_csv",
        category=ConstraintCategory.FORMAT,
        constraint_type=ConstraintType.HARD,
        value="csv",
    )

    conflicts = ConstraintEngine.check_conflicts([c1, c2])
    assert len(conflicts) > 0
    assert "conflicting" in str(conflicts[0]).lower() or "format" in str(conflicts[0]).lower()


def test_hard_vs_soft_constraints():
    """Verify hard vs soft constraint classification and ranking (Spec 16, 17, 19)."""
    hard = DiscoveredConstraint(
        name="strict_budget",
        category=ConstraintCategory.BUDGET,
        constraint_type=ConstraintType.HARD,
        value=100.0,
        priority=1,
    )
    soft = DiscoveredConstraint(
        name="preferred_theme",
        category=ConstraintCategory.FORMAT,
        constraint_type=ConstraintType.SOFT,
        value="dark_mode",
        priority=3,
    )

    assert hard.constraint_type == ConstraintType.HARD
    assert soft.constraint_type == ConstraintType.SOFT
    assert hard.priority < soft.priority  # Lower number = higher priority


def test_preference_override_by_explicit_instruction():
    """Current explicit user instruction strictly overrides older memory preference (Spec 23, 24)."""
    resolver = PreferenceResolver()
    # User had an established preference for Python
    resolver.store_preference(
        UserPreference(
            key="default_language",
            value="python",
            confidence=PreferenceConfidence.STRONGLY_ESTABLISHED,
            scope=PreferenceScope.GLOBAL,
        )
    )

    # Current explicit prompt requests TypeScript
    resolved = resolver.resolve_preference(
        key="default_language",
        explicit_override="typescript",
    )

    assert resolved == "typescript"  # Explicit instruction strictly wins


def test_preference_confidence_and_scopes():
    """Verify preference confidence levels and scopes (Spec 21, 22)."""
    pref = UserPreference(
        key="notifications_channel",
        value="slack",
        confidence=PreferenceConfidence.EXPLICIT,
        scope=PreferenceScope.PROJECT,
    )

    assert pref.confidence == PreferenceConfidence.EXPLICIT
    assert pref.scope == PreferenceScope.PROJECT
    assert pref.to_dict()["key"] == "notifications_channel"


def test_memory_cannot_override_explicit_instruction():
    """Memory preference cannot override explicit instruction even if confidence is 1.0 (Spec 24)."""
    resolver = PreferenceResolver()
    resolver.store_preference(
        UserPreference(
            key="test_runner",
            value="pytest",
            confidence=PreferenceConfidence.EXPLICIT,
            scope=PreferenceScope.GLOBAL,
        )
    )

    # User says "Run tests with unittest"
    effective_value = resolver.resolve_preference(
        key="test_runner",
        explicit_override="unittest",
    )
    assert effective_value == "unittest"
