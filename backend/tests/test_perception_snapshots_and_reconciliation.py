"""Tests for Environment Snapshots, Missing Sources Handling, State Reconciliation, and Entity Resolution (Task 46)."""

from datetime import datetime, timezone
import pytest

from app.perception.environment import EnvironmentBoundaryGuard, EnvironmentIsolationError, EnvironmentType
from app.perception.events import EventType, PerceptionEvent
from app.perception.observations import Observation
from app.perception.reconciliation import EntityResolver, StateConflict, StateReconciler
from app.perception.snapshots import EnvironmentSnapshot, SnapshotManager
from app.perception.sources import PerceptionSource, SourceType


def utc_now():
    return datetime.now(timezone.utc)


def test_environment_snapshot_creation_and_versioning():
    mgr = SnapshotManager()

    snap1 = mgr.create_snapshot(
        environment="PRODUCTION",
        services={"kairo_api": {"status": "HEALTHY"}},
        deployments={"kairo_prod": {"version": "v1.0"}},
        is_atomic=True,
    )
    assert snap1.version == 1
    assert snap1.environment == "PRODUCTION"
    assert snap1.is_atomic is True

    snap2 = mgr.create_snapshot(
        environment="PRODUCTION",
        services={"kairo_api": {"status": "DEGRADED"}},
        deployments={"kairo_prod": {"version": "v1.1"}},
        is_atomic=False,
    )
    assert snap2.version == 2
    assert snap2.services["kairo_api"]["status"] == "DEGRADED"
    assert snap2.is_atomic is False


def test_partial_snapshot_and_missing_sources_as_unknown():
    """Enforce Spec 34, 35: If some sources unavailable, mark missing data. Unavailable observation becomes UNKNOWN, not HEALTHY."""
    mgr = SnapshotManager()

    snap = mgr.create_snapshot(
        environment="STAGING",
        services={"frontend_app": {"status": "HEALTHY"}},
        missing_sources=["redis_cluster", "billing_worker"],
    )

    assert "redis_cluster" in snap.missing_sources
    # Missing source state is UNKNOWN, NEVER fabricated as HEALTHY
    assert snap.services["redis_cluster"]["status"] == "UNKNOWN"
    assert snap.services["redis_cluster"]["reliability"] == 0.0


def test_environment_boundary_isolation():
    """Enforce Spec 77, 78: A production observation must not silently become development state."""
    # Production observation in production context is allowed
    EnvironmentBoundaryGuard.validate_environment_access("PRODUCTION", "PRODUCTION")

    # Production observation in development context is blocked
    with pytest.raises(EnvironmentIsolationError, match="Cross-environment contamination"):
        EnvironmentBoundaryGuard.validate_environment_access("PRODUCTION", "DEVELOPMENT")


def test_state_reconciliation_weaker_observation_cannot_overwrite():
    """Enforce Spec 114-117: Do not silently overwrite authoritative state with weaker observation.
    Preserve conflict when sources disagree.
    """
    reconciler = StateReconciler()

    # Register authoritative source (weight 1.0)
    reconciler.register_authoritative_state(
        subject="service:payment:status",
        state_value="HEALTHY",
        source_id="src_k8s_authoritative",
        authority_weight=1.0,
    )

    # Weaker telemetry observation (weight 0.6) claiming UNHEALTHY
    weak_source = PerceptionSource("src_third_party", SourceType.API, "External Monitor", reliability=0.6)
    weak_obs = Observation.from_event(
        PerceptionEvent("e_weak", EventType.UPDATED, "src_third_party", "service:payment:status", payload="UNHEALTHY"),
        weak_source,
    )

    accepted, conflict = reconciler.reconcile_observation(weak_obs, weak_source)

    # Rejected because candidate authority (0.6) < authoritative authority (1.0)
    assert accepted is False
    assert conflict is not None
    assert conflict.authoritative_state == "HEALTHY"
    assert conflict.observed_state == "UNHEALTHY"
    assert conflict.candidate_source_id == "src_third_party"


def test_entity_resolver_and_ambiguity_protection():
    """Enforce Spec 123-125: If uncertain, do NOT merge entities blindly."""
    resolver = EntityResolver()
    resolver.register_entity("srv_prod_api", ["api.kairo.internal", "10.0.0.4"])

    # High confidence match resolves
    assert resolver.resolve_entity("10.0.0.4") == "srv_prod_api"

    # Ambiguous entity resolution: if confidence < 0.95, do not merge blindly
    res = resolver.safe_merge_entities("srv_prod_api", "srv_staging_api", confidence=0.7)
    # Kept distinct
    assert res == "srv_prod_api"
    assert resolver.resolve_entity("srv_staging_api") is None

    # High confidence merge succeeds
    res_high = resolver.safe_merge_entities("srv_prod_api", "api-gateway", confidence=0.99)
    assert res_high == "srv_prod_api"
    assert resolver.resolve_entity("api-gateway") == "srv_prod_api"
