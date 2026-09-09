"""Unit tests for Reference Resolution and Timezone-Aware Temporal Context (Spec 11-20, 35, 36)."""

from datetime import UTC, datetime
import pytest

from app.intent.context import TemporalContextResolver
from app.intent.references import ReferenceResolver
from app.intent.schemas import ResolutionMethod


def test_reference_priority_attachment_over_conversation():
    """Verify 'this' prioritizes direct attachment over earlier objects (Spec 12, 13)."""
    attachments = [{"name": "pipeline_error.log", "type": "document"}]
    recent_artifacts = [{"id": "art_99", "name": "previous_doc.pdf"}]

    resolved, ambiguous, detected = ReferenceResolver.resolve_references(
        text="Explain this",
        attachments=attachments,
        recent_artifacts=recent_artifacts,
    )

    assert "this" in detected
    assert resolved["this"] is not None
    assert resolved["this"]["name"] == "pipeline_error.log"
    assert resolved["this"]["method"] == ResolutionMethod.EXPLICIT


def test_the_repo_single_vs_multiple_disambiguation():
    """Verify 'the repo' resolves if unique, but flags ambiguity if multiple exist (Spec 16)."""
    # Single repo
    resolved_single, amb_single, _ = ReferenceResolver.resolve_references(
        text="Check the repo",
        project_context={"name": "Kairo", "repositories": ["kairo-core"]},
    )
    assert resolved_single["the_repo"]["name"] == "kairo-core"
    assert len(amb_single) == 0

    # Multiple repos
    resolved_multi, amb_multi, _ = ReferenceResolver.resolve_references(
        text="Check the repo",
        project_context={"name": "Kairo", "repositories": ["kairo-backend", "kairo-frontend"]},
    )
    assert resolved_multi["the_repo"] is None
    assert len(amb_multi) == 1
    assert "kairo-backend" in amb_multi[0]["candidates"]
    assert "kairo-frontend" in amb_multi[0]["candidates"]


def test_timezone_aware_temporal_yesterday():
    """Verify 'yesterday' calculates exact start and end timestamps in user timezone (Spec 18, 19)."""
    # Fixed test time: 2026-09-09 10:00:00 UTC
    now_dt = datetime(2026, 9, 9, 10, 0, 0, tzinfo=UTC)

    # In America/New_York (UTC-4), 10:00 UTC is 06:00 AM Sept 9.
    # Yesterday in NY is Sept 8 00:00 to Sept 8 23:59:59 NY time.
    keyword, start_utc, end_utc = TemporalContextResolver.resolve_temporal_range(
        text="continue what we were doing yesterday",
        user_timezone="America/New_York",
        now_dt=now_dt,
    )

    assert keyword == "yesterday"
    assert start_utc is not None and end_utc is not None
    # Sept 8 00:00 EDT is Sept 8 04:00 UTC
    assert start_utc == datetime(2026, 9, 8, 4, 0, 0, tzinfo=UTC)


def test_conversation_vs_task_resolution_separation():
    """Verify 'continue that discussion' does not resolve to an autonomous task (Spec 35, 36)."""
    active_task = {"id": "task_123", "title": "CI Investigation"}
    resolved, _, detected = ReferenceResolver.resolve_references(
        text="continue our discussion about python",
        active_task=active_task,
    )

    # "the_task" or task control references were not in the query
    assert "the_task" not in detected
