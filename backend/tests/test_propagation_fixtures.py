"""Deterministic graph topology fixtures for risk propagation tests (Spec 74)."""

from datetime import UTC, datetime, timedelta
import pytest

from app.propagation.schemas import (
    EpistemicCategory,
    PropagationEdge,
    RedundancyState,
    RelationshipType,
    TemporalDelay,
)
from app.propagation.snapshots import GraphSnapshot, GraphSnapshotEngine


@pytest.fixture
def snapshot_engine() -> GraphSnapshotEngine:
    return GraphSnapshotEngine()


@pytest.fixture
def direct_link_fixture(snapshot_engine: GraphSnapshotEngine) -> GraphSnapshot:
    """Fixture 1: A -> B (Direct Link)."""
    edges = [
        PropagationEdge(
            edge_id="e_ab",
            source_entity="A",
            target_entity="B",
            relationship_type=RelationshipType.DEPENDS_ON,
            confidence=0.95,
            temporal_delay=TemporalDelay(expected_delay_seconds=1.0),
        )
    ]
    return snapshot_engine.create_snapshot(edges=edges)


@pytest.fixture
def second_order_fixture(snapshot_engine: GraphSnapshotEngine) -> GraphSnapshot:
    """Fixture 2: A -> B -> C (Second-order Link)."""
    edges = [
        PropagationEdge(
            edge_id="e_ab",
            source_entity="A",
            target_entity="B",
            relationship_type=RelationshipType.DEPENDS_ON,
            confidence=0.90,
            temporal_delay=TemporalDelay(expected_delay_seconds=1.5),
        ),
        PropagationEdge(
            edge_id="e_bc",
            source_entity="B",
            target_entity="C",
            relationship_type=RelationshipType.DEPENDS_ON,
            confidence=0.85,
            temporal_delay=TemporalDelay(expected_delay_seconds=2.0),
        ),
    ]
    return snapshot_engine.create_snapshot(edges=edges)


@pytest.fixture
def higher_order_fixture(snapshot_engine: GraphSnapshotEngine) -> GraphSnapshot:
    """Fixture 3: A -> B -> C -> D (Higher-order Cascade)."""
    edges = [
        PropagationEdge(edge_id="e_ab", source_entity="A", target_entity="B", relationship_type=RelationshipType.DEPENDS_ON, confidence=0.9),
        PropagationEdge(edge_id="e_bc", source_entity="B", target_entity="C", relationship_type=RelationshipType.DEPENDS_ON, confidence=0.9),
        PropagationEdge(edge_id="e_cd", source_entity="C", target_entity="D", relationship_type=RelationshipType.DEPENDS_ON, confidence=0.9),
    ]
    return snapshot_engine.create_snapshot(edges=edges)


@pytest.fixture
def diamond_fixture(snapshot_engine: GraphSnapshotEngine) -> GraphSnapshot:
    """Fixture 4: Diamond topology: A -> B, A -> C, B -> D, C -> D."""
    edges = [
        PropagationEdge(edge_id="e_ab", source_entity="A", target_entity="B", relationship_type=RelationshipType.DEPENDS_ON, confidence=0.9),
        PropagationEdge(edge_id="e_ac", source_entity="A", target_entity="C", relationship_type=RelationshipType.DEPENDS_ON, confidence=0.9),
        PropagationEdge(edge_id="e_bd", source_entity="B", target_entity="D", relationship_type=RelationshipType.DEPENDS_ON, confidence=0.85),
        PropagationEdge(edge_id="e_cd", source_entity="C", target_entity="D", relationship_type=RelationshipType.DEPENDS_ON, confidence=0.85),
    ]
    return snapshot_engine.create_snapshot(edges=edges)


@pytest.fixture
def cycle_fixture(snapshot_engine: GraphSnapshotEngine) -> GraphSnapshot:
    """Fixture 5: Cycle topology: A -> B -> C -> A (Amplifying feedback loop)."""
    edges = [
        PropagationEdge(edge_id="e_ab", source_entity="A", target_entity="B", relationship_type=RelationshipType.AMPLIFIES, confidence=0.9),
        PropagationEdge(edge_id="e_bc", source_entity="B", target_entity="C", relationship_type=RelationshipType.AMPLIFIES, confidence=0.9),
        PropagationEdge(edge_id="e_ca", source_entity="C", target_entity="A", relationship_type=RelationshipType.AMPLIFIES, confidence=0.9),
    ]
    return snapshot_engine.create_snapshot(edges=edges)


@pytest.fixture
def redundant_fixture(snapshot_engine: GraphSnapshotEngine) -> GraphSnapshot:
    """Fixture 6: A -> B where B has verified redundancy B2."""
    edges = [
        PropagationEdge(
            edge_id="e_ab",
            source_entity="A",
            target_entity="B",
            relationship_type=RelationshipType.DEPENDS_ON,
            confidence=0.9,
            redundancy_state=RedundancyState.FULL,
            redundancy_alternatives=["B2"],
        )
    ]
    return snapshot_engine.create_snapshot(edges=edges)


@pytest.fixture
def unknown_redundancy_fixture(snapshot_engine: GraphSnapshotEngine) -> GraphSnapshot:
    """Fixture 7: A -> B where redundancy status is unrecorded (REDUNDANCY_UNKNOWN)."""
    edges = [
        PropagationEdge(
            edge_id="e_ab",
            source_entity="A",
            target_entity="B",
            relationship_type=RelationshipType.DEPENDS_ON,
            confidence=0.9,
            redundancy_state=RedundancyState.REDUNDANCY_UNKNOWN,
        )
    ]
    return snapshot_engine.create_snapshot(edges=edges)


@pytest.fixture
def disputed_edge_fixture(snapshot_engine: GraphSnapshotEngine) -> GraphSnapshot:
    """Fixture 8: A -> B with conflicting evidence (CONFLICTING_EVIDENCE)."""
    edges = [
        PropagationEdge(
            edge_id="e_ab",
            source_entity="A",
            target_entity="B",
            relationship_type=RelationshipType.DEPENDS_ON,
            confidence=0.6,
            is_disputed=True,
            dispute_reason="Conflicting evidence: telemetry logs show zero runtime dependency.",
        )
    ]
    return snapshot_engine.create_snapshot(edges=edges)


@pytest.fixture
def historical_expired_edge_fixture(snapshot_engine: GraphSnapshotEngine) -> GraphSnapshot:
    """Fixture 9: A -> B valid in the past, expired at current analysis time."""
    now = datetime.now(UTC)
    edges = [
        PropagationEdge(
            edge_id="e_ab",
            source_entity="A",
            target_entity="B",
            relationship_type=RelationshipType.DEPENDS_ON,
            confidence=0.9,
            valid_from=now - timedelta(days=60),
            valid_until=now - timedelta(days=10),
        )
    ]
    return snapshot_engine.create_snapshot(edges=edges, as_of_timestamp=now)
