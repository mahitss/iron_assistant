"""Unit tests for propagation domain schemas, graph snapshots, and bounded traversal (Task 75)."""

from datetime import UTC, datetime, timedelta
import pytest

from app.propagation.schemas import (
    BoundaryType,
    CascadeStatus,
    CascadeType,
    CriticalityLevel,
    EpistemicCategory,
    FeedbackType,
    ImpactDimensions,
    PropagationAnalysis,
    PropagationEdge,
    PropagationScope,
    RedundancyState,
    RelationshipType,
    TemporalDelay,
    TriggerType,
)
from app.propagation.snapshots import GraphSnapshotEngine
from app.propagation.traversal import BoundedPropagationTraverser


def test_propagation_domain_schemas_and_invariants():
    """Verify schema initialization, defaults, and multi-dimensional impact (Spec 4, 17, 18)."""
    impact = ImpactDimensions(
        operational_impact=0.75,
        resource_impact=0.60,
        schedule_impact_seconds=3600.0,
        reliability_impact=0.50,
        security_impact=0.20,
        financial_impact=None,  # Never fabricated!
        user_impact=0.65,
        strategic_impact=0.40,
    )
    severity = impact.composite_severity()
    assert 0.0 <= severity <= 1.0
    assert severity > 0.4

    analysis = PropagationAnalysis(
        trigger="Database latency spike",
        trigger_type=TriggerType.PERFORMANCE_DEGRADATION,
        origin_entity="db_primary",
        scope=PropagationScope.SERVICE,
    )
    assert analysis.status == CascadeStatus.DISCOVERED
    assert analysis.confidence >= 0.5
    assert not analysis.is_truncated


def test_graph_snapshot_temporal_filtering_and_zero_leakage():
    """Verify that graph snapshot freezes state and excludes future or expired edges (Spec 6, 49, 62)."""
    engine = GraphSnapshotEngine()
    now = datetime.now(UTC)

    edges = [
        PropagationEdge(
            edge_id="e_past",
            source_entity="A",
            target_entity="B",
            relationship_type=RelationshipType.DEPENDS_ON,
            valid_from=now - timedelta(days=10),
            valid_until=now + timedelta(days=10),
        ),
        PropagationEdge(
            edge_id="e_future_leaked",
            source_entity="B",
            target_entity="C",
            relationship_type=RelationshipType.DEPENDS_ON,
            valid_from=now + timedelta(days=5),  # FUTURE EDGE
        ),
        PropagationEdge(
            edge_id="e_expired",
            source_entity="A",
            target_entity="D",
            relationship_type=RelationshipType.DEPENDS_ON,
            valid_until=now - timedelta(days=1),  # EXPIRED EDGE
        ),
    ]

    snapshot = engine.create_snapshot(edges=edges, as_of_timestamp=now)

    # Invariant: Only currently valid edges must be retained
    retained_edge_ids = [e.edge_id for e in snapshot.get_edges()]
    assert "e_past" in retained_edge_ids
    assert "e_future_leaked" not in retained_edge_ids
    assert "e_expired" not in retained_edge_ids
    assert snapshot.edge_count == 1


def test_bounded_traversal_direct_and_second_order_effects():
    """Verify Depth 1 (Direct) and Depth 2 (Second-Order) distinction (Spec 7, 8, 9)."""
    engine = GraphSnapshotEngine()
    edges = [
        PropagationEdge(
            edge_id="e_ab",
            source_entity="service_a",
            target_entity="service_b",
            relationship_type=RelationshipType.DEPENDS_ON,
            epistemic_category=EpistemicCategory.DEPENDENCY,
            confidence=0.90,
            temporal_delay=TemporalDelay(expected_delay_seconds=2.0),
        ),
        PropagationEdge(
            edge_id="e_bc",
            source_entity="service_b",
            target_entity="service_c",
            relationship_type=RelationshipType.CAUSES,
            epistemic_category=EpistemicCategory.CAUSAL_RELATIONSHIP,
            confidence=0.80,
            temporal_delay=TemporalDelay(expected_delay_seconds=3.0),
        ),
    ]
    snapshot = engine.create_snapshot(edges=edges)
    traverser = BoundedPropagationTraverser(max_depth=3)

    result = traverser.traverse("service_a", snapshot)

    assert not result.is_truncated
    assert len(result.direct_effects) == 1
    assert result.direct_effects[0].target_entity == "service_b"
    assert result.direct_effects[0].confidence == 0.90

    assert len(result.second_order_effects) == 1
    second = result.second_order_effects[0]
    assert second.target_entity == "service_c"
    assert second.intermediate_entity == "service_b"
    assert "service_b causally affects service_c" in second.explanation
    # Weakest link confidence decay
    assert second.confidence <= 0.80


def test_bounded_traversal_bounds_and_truncation_handling():
    """Verify max depth, max nodes, timeout, and explicit PROPAGATION_TRUNCATED marking (Spec 10)."""
    engine = GraphSnapshotEngine()
    # Build a deep chain: N0 -> N1 -> N2 -> N3 -> N4 -> N5
    edges = [
        PropagationEdge(edge_id=f"e_{i}", source_entity=f"N{i}", target_entity=f"N{i+1}", relationship_type=RelationshipType.DEPENDS_ON)
        for i in range(10)
    ]
    snapshot = engine.create_snapshot(edges=edges)

    # Restrict max depth to 2
    traverser_depth = BoundedPropagationTraverser(max_depth=2)
    res_depth = traverser_depth.traverse("N0", snapshot)
    assert max(m.get("depth", 0) for m in res_depth.visited_nodes.values()) == 2

    # Restrict max nodes to 3
    traverser_nodes = BoundedPropagationTraverser(max_depth=10, max_nodes=3)
    res_nodes = traverser_nodes.traverse("N0", snapshot)
    assert res_nodes.is_truncated
    assert "PROPAGATION_TRUNCATED" in (res_nodes.truncation_reason or "")


def test_cycle_detection_and_amplifying_feedback_loop():
    """Verify cycle detection without infinite loops and classification of amplifying feedback (Spec 28, 29)."""
    engine = GraphSnapshotEngine()
    edges = [
        PropagationEdge(edge_id="e_1", source_entity="worker", target_entity="queue", relationship_type=RelationshipType.AMPLIFIES),
        PropagationEdge(edge_id="e_2", source_entity="queue", target_entity="database", relationship_type=RelationshipType.AMPLIFIES),
        PropagationEdge(edge_id="e_3", source_entity="database", target_entity="worker", relationship_type=RelationshipType.AMPLIFIES),
    ]
    snapshot = engine.create_snapshot(edges=edges)
    traverser = BoundedPropagationTraverser(max_depth=5)

    result = traverser.traverse("worker", snapshot)

    assert len(result.cycles) >= 1
    cycle_key = "->".join(result.cycles[0])
    assert result.feedback_types.get(cycle_key) == FeedbackType.AMPLIFYING_FEEDBACK
