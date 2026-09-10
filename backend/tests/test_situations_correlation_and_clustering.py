"""Unit tests for Event Correlation, Dependency Graph Mapping, and Clustering (Task 60)."""

from datetime import datetime, timedelta, timezone

from app.situational_awareness.clustering import EventClusterer
from app.situational_awareness.correlation import EventCorrelator
from app.situational_awareness.schemas import NormalizedEvent, SituationSeverity, SourceTrustLevel


def _make_evt(
    event_id: str,
    resource: str,
    subject: str,
    env: str = "production",
    offset_seconds: float = 0.0,
) -> NormalizedEvent:
    base = datetime(2026, 9, 10, 15, 0, 0, tzinfo=timezone.utc)
    occ = base + timedelta(seconds=offset_seconds)
    return NormalizedEvent(
        event_id=event_id,
        event_type="alert",
        source="monitor",
        source_trust=SourceTrustLevel.TRUSTED_SYSTEM,
        environment=env,
        resource=resource,
        subject=subject,
        payload={},
        severity=SituationSeverity.HIGH,
        occurred_at=occ,
        received_at=occ,
    )


def test_temporal_and_resource_correlation():
    """Verify events on the same resource within temporal window are correlated."""
    correlator = EventCorrelator(temporal_window_seconds=300.0)

    e1 = _make_evt("e1", "db-primary", "High CPU", offset_seconds=0)
    e2 = _make_evt("e2", "db-primary", "High Connection Pool", offset_seconds=60)

    res = correlator.correlate_events(e1, e2)
    assert res["is_correlated"] is True
    assert res["correlation_score"] >= 0.7
    assert any("identical resource" in r for r in res["reasons"])


def test_environment_mismatch_prevents_correlation():
    """Events occurring in different environments (staging vs production) must not be correlated."""
    correlator = EventCorrelator(temporal_window_seconds=300.0)

    e_prod = _make_evt("e_prod", "db-cluster", "CPU high", env="production", offset_seconds=0)
    e_stag = _make_evt("e_stag", "db-cluster", "CPU high", env="staging", offset_seconds=10)

    res = correlator.correlate_events(e_prod, e_stag)
    assert res["is_correlated"] is False
    assert res["correlation_score"] == 0.0


def test_dependency_graph_correlation():
    """Test correlation across services connected in the dependency topology graph."""
    correlator = EventCorrelator(temporal_window_seconds=300.0)

    # Topology: auth-api depends on db-primary
    dep_map = {
        "auth-api": ["db-primary"],
        "db-primary": [],
    }

    e_db = _make_evt("e_db", "db-primary", "Database lock contention", offset_seconds=0)
    e_api = _make_evt("e_api", "auth-api", "504 Gateway Timeout", offset_seconds=30)

    res = correlator.correlate_events(e_db, e_api, dependency_map=dep_map)
    assert res["is_correlated"] is True
    assert any("dependency graph" in r for r in res["reasons"])


def test_correlation_does_not_assert_causation():
    """Test Invariant 15: Correlation != Causation. Correlator evaluates relationship without declaring definitive cause."""
    correlator = EventCorrelator(temporal_window_seconds=300.0)

    e1 = _make_evt("e1", "service-a", "deploy", offset_seconds=0)
    e2 = _make_evt("e2", "service-a", "cpu_spike", offset_seconds=15)

    res = correlator.correlate_events(e1, e2)
    assert res["is_correlated"] is True
    # The result does not claim causal proof, only correlation score and temporal relationship
    assert "causal_proof" not in res
    assert res["temporal_relationship"] == "BEFORE"


def test_event_clustering_partitions_into_discrete_clusters():
    """Verify clusterer groups related events together and separates independent events."""
    clusterer = EventClusterer()

    # Cluster 1: Database and dependent Auth API in production
    dep_map = {"auth-api": ["db-primary"]}
    e1 = _make_evt("c1_e1", "db-primary", "slow query", offset_seconds=0)
    e2 = _make_evt("c1_e2", "auth-api", "timeout", offset_seconds=20)

    # Cluster 2: Completely independent frontend bundle in staging
    e3 = _make_evt("c2_e1", "frontend-web", "asset 404", env="staging", offset_seconds=500)

    clusters = clusterer.cluster_events([e1, e2, e3], dependency_map=dep_map)
    assert len(clusters) == 2

    # Verify cluster memberships
    c1 = next(c for c in clusters if c.environment == "production")
    c2 = next(c for c in clusters if c.environment == "staging")

    assert len(c1.events) == 2
    assert set(c1.resources) == {"db-primary", "auth-api"}
    assert len(c2.events) == 1
    assert c2.resources == ["frontend-web"]
