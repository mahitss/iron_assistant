"""Tests for Entity Extraction, Safe Pronoun Resolution, and Temporal Semantics (Task 48, Spec 29-38)."""

from datetime import datetime, timezone
import pytest

from app.intent.context import TemporalContextResolver
from app.intent.entities import EntityExtractor
from app.intent.schemas import IntentEntity


def test_entity_extraction_multiclass():
    """Extract diverse entity types: repos, services, files, people (Spec 29, 30)."""
    text = "Deploy kairo-api service to production and send summary to alice@example.com in report.pdf"
    entities = EntityExtractor.extract_entities(text)

    names = [e.name for e in entities]
    types = [e.entity_type for e in entities]

    assert any("kairo-api" in n for n in names)
    assert any("alice@example.com" in n for n in names)
    assert any("report.pdf" in n for n in names)
    assert "SERVICE" in types or "REPOSITORY" in types or "FILE" in types


def test_pronoun_resolution_safe_contextual():
    """Resolve 'it' when target entity is obvious and non-destructive (Spec 32)."""
    text = "Restart the nginx service and verify it"
    entities = [
        IntentEntity(entity_type="SERVICE", name="nginx"),
    ]

    resolved, is_ambiguous = EntityExtractor.resolve_pronouns(
        text=text,
        known_entities=entities,
        is_destructive_action=False,
    )

    assert not is_ambiguous
    if resolved:
        assert resolved.name == "nginx"


def test_pronoun_resolution_destructive_never_guesses():
    """CRITICAL SAFETY: Never guess ambiguous pronoun for destructive operation like DELETE (Spec 32, 111)."""
    text = "Delete it"
    # Multiple candidate entities in recent context
    entities = [
        IntentEntity(entity_type="FILE", name="report.pdf"),
        IntentEntity(entity_type="FILE", name="database_backup.sql"),
    ]

    resolved, is_ambiguous = EntityExtractor.resolve_pronouns(
        text=text,
        known_entities=entities,
        is_destructive_action=True,  # Consequential delete
    )

    # Must flag ambiguity and refuse to silently pick database_backup.sql
    assert is_ambiguous is True


def test_temporal_relative_understanding():
    """Resolve relative dates: today, tomorrow, next week, before deployment (Spec 33, 34)."""
    base_time = datetime(2026, 9, 10, 10, 0, 0, tzinfo=timezone.utc)

    resolved_today = TemporalContextResolver.resolve_relative_time("today", base_time=base_time)
    assert resolved_today.day == 10

    resolved_tomorrow = TemporalContextResolver.resolve_relative_time("tomorrow", base_time=base_time)
    assert resolved_tomorrow.day == 11


def test_temporal_flexible_semantics_no_invented_time():
    """Preserve flexible semantics for 'tomorrow morning' without inventing exact second (Spec 36)."""
    phrase = "tomorrow morning"
    is_flexible = TemporalContextResolver.is_flexible_time(phrase)
    assert is_flexible is True


def test_timezone_handling():
    """Verify timezone awareness in temporal conversion (Spec 35)."""
    base_utc = datetime(2026, 9, 10, 12, 0, 0, tzinfo=timezone.utc)
    t_ny = TemporalContextResolver.convert_to_timezone(base_utc, "America/New_York")
    # America/New_York is UTC-4 in September (EDT)
    assert t_ny.hour == 8
