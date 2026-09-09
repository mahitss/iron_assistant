"""Tests for freshness policies, staleness evaluation, source registry, and conflict resolution (Task 32, Spec 29-35, 60, 87, 88)."""

from datetime import UTC, datetime, timedelta
import pytest

from app.world.conflicts import (
    ConflictResolutionAction,
    ConflictType,
    StateConflictEngine,
)
from app.world.entities import (
    ConfidenceLevel,
    EntityType,
    ObservationType,
    WorldEntitySchema,
)
from app.world.freshness import FreshnessPolicy
from app.world.registry import (
    SourceAuthority,
    SourceOfTruthRegistry,
)


def test_freshness_ttl_matrix():
    """Verify entity-specific TTL thresholds (Spec 31)."""
    assert FreshnessPolicy.get_default_ttl(EntityType.DEVICE) == 60
    assert FreshnessPolicy.get_default_ttl(EntityType.SERVICE) == 120
    assert FreshnessPolicy.get_default_ttl(EntityType.TASK) == 300
    assert FreshnessPolicy.get_default_ttl(EntityType.REPOSITORY) == 600
    assert FreshnessPolicy.get_default_ttl(EntityType.PROJECT) == 3600


def test_is_stale_evaluation():
    """Verify staleness detection based on observed_at and TTL (Spec 29, 30)."""
    now = datetime.now(UTC)
    recent_time = now - timedelta(seconds=20)
    old_time = now - timedelta(seconds=200)

    # Device TTL is 60s:
    # 20s old -> Fresh
    assert FreshnessPolicy.is_stale(observed_at=recent_time, entity_type=EntityType.DEVICE, now=now) is False

    # 200s old -> Stale
    assert FreshnessPolicy.is_stale(observed_at=old_time, entity_type=EntityType.DEVICE, now=now) is True


def test_source_of_truth_authoritative_mapping():
    """Verify authoritative source mappings (Spec 32)."""
    assert SourceOfTruthRegistry.is_source_authoritative(EntityType.DEVICE, "local_companion") is True
    assert SourceOfTruthRegistry.is_source_authoritative(EntityType.DEVICE, "model_inference") is False
    assert SourceOfTruthRegistry.is_source_authoritative(EntityType.REPOSITORY, "github") is True
    assert SourceOfTruthRegistry.is_source_authoritative(EntityType.TASK, "task_engine") is True
    assert SourceOfTruthRegistry.is_source_authoritative(EntityType.SERVICE, "observability") is True


def test_conflict_detection_version_mismatch():
    """Verify incoming updates with older state versions are rejected (Spec 34, 87)."""
    now = datetime.now(UTC)
    existing = WorldEntitySchema(
        id="ent_svc_1",
        type=EntityType.SERVICE,
        name="API",
        owner_id="u1",
        source="observability",
        source_id="svc_1",
        state="HEALTHY",
        state_version=5,
        observed_at=now - timedelta(seconds=10),
    )

    conflict = StateConflictEngine.evaluate_conflict(
        existing_entity=existing,
        new_state="DEGRADED",
        new_version=3,  # Regressive version
        new_source="observability",
        new_observed_at=now,
        new_authority=SourceAuthority.AUTHORITATIVE_SYSTEM,
    )

    assert conflict is not None
    c_type, c_action, _ = conflict
    assert c_type == ConflictType.VERSION_MISMATCH
    assert c_action == ConflictResolutionAction.REJECT_UPDATE


def test_conflict_detection_stale_timestamp():
    """Verify incoming updates with older observation timestamps are rejected (Spec 34, 88)."""
    now = datetime.now(UTC)
    existing = WorldEntitySchema(
        id="ent_dev_1",
        type=EntityType.DEVICE,
        name="PC",
        owner_id="u1",
        source="local_companion",
        source_id="dev_1",
        state="CONNECTED",
        observed_at=now,
    )

    past_time = now - timedelta(seconds=50)
    conflict = StateConflictEngine.evaluate_conflict(
        existing_entity=existing,
        new_state="DISCONNECTED",
        new_version=None,
        new_source="local_companion",
        new_observed_at=past_time,  # Outdated event arrived late
        new_authority=SourceAuthority.AUTHORITATIVE_SYSTEM,
    )

    assert conflict is not None
    c_type, c_action, _ = conflict
    assert c_type == ConflictType.STALE_UPDATE
    assert c_action == ConflictResolutionAction.REJECT_UPDATE


def test_conflict_detection_unauthorized_source_overwrite():
    """Verify non-authoritative source cannot overwrite authoritative state (Spec 33, 34)."""
    now = datetime.now(UTC)
    existing = WorldEntitySchema(
        id="ent_repo_1",
        type=EntityType.REPOSITORY,
        name="kairo",
        owner_id="u1",
        source="github",  # Authoritative source for repo
        source_id="repo_1",
        state="SYNCED",
        observed_at=now - timedelta(seconds=5),
    )

    # A non-authoritative source (e.g. user prompt text or model inference) tries to change repo state
    conflict = StateConflictEngine.evaluate_conflict(
        existing_entity=existing,
        new_state="ERROR",
        new_version=None,
        new_source="model_inference",
        new_observed_at=now,
        new_authority=SourceAuthority.DERIVED_INFERENCE,
    )

    assert conflict is not None
    c_type, c_action, _ = conflict
    assert c_type == ConflictType.UNAUTHORIZED_SOURCE
    assert c_action == ConflictResolutionAction.REJECT_UPDATE


def test_authoritative_source_wins_contradictory_state():
    """Verify authoritative source update succeeds and updates state (Spec 33, 35, 60)."""
    now = datetime.now(UTC)
    existing = WorldEntitySchema(
        id="ent_svc_1",
        type=EntityType.SERVICE,
        name="Backend",
        owner_id="u1",
        source="observability",
        source_id="svc_1",
        state="HEALTHY",
        observed_at=now - timedelta(seconds=10),
    )

    conflict = StateConflictEngine.evaluate_conflict(
        existing_entity=existing,
        new_state="UNHEALTHY",
        new_version=None,
        new_source="observability",  # Authoritative source declares unhealthy
        new_observed_at=now,
        new_authority=SourceAuthority.AUTHORITATIVE_SYSTEM,
    )

    assert conflict is not None
    c_type, c_action, _ = conflict
    assert c_type == ConflictType.CONTRADICTORY_STATE
    assert c_action == ConflictResolutionAction.APPLY_AUTHORITATIVE
