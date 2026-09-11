"""Unit tests for cascade pattern detection, fingerprinting, bottlenecks, and SPoFs (Task 75)."""

import pytest

from app.propagation.bottlenecks import BottleneckAnalyzer
from app.propagation.cascade import CascadeDetector, compute_cascade_fingerprint
from app.propagation.schemas import (
    CascadeStatus,
    CascadeType,
    CriticalityLevel,
    PropagationEdge,
    RedundancyState,
    RelationshipType,
    TriggerType,
)
from app.propagation.snapshots import GraphSnapshotEngine
from app.propagation.traversal import BoundedPropagationTraverser


def test_cascade_detection_and_classification():
    """Verify cascade chain extraction and classification across 9 types (Spec 11, 12)."""
    engine = GraphSnapshotEngine()
    edges = [
        PropagationEdge(edge_id="e1", source_entity="auth_service", target_entity="cache", relationship_type=RelationshipType.DEPENDS_ON),
        PropagationEdge(edge_id="e2", source_entity="cache", target_entity="session_store", relationship_type=RelationshipType.SHARES_RESOURCE),
    ]
    snapshot = engine.create_snapshot(edges=edges)
    traverser = BoundedPropagationTraverser()
    detector = CascadeDetector()

    result = traverser.traverse("auth_service", snapshot)
    cascades = detector.detect_cascades(result, trigger_type=TriggerType.STATE_CHANGE)

    assert len(cascades) >= 1
    # Because e2 is SHARES_RESOURCE, classified as RESOURCE_CASCADE
    assert any(c.cascade_type == CascadeType.RESOURCE_CASCADE for c in cascades)
    assert cascades[0].status == CascadeStatus.PROJECTED
    assert cascades[0].fingerprint != ""


def test_cascade_fingerprinting_stability():
    """Verify deterministic cascade fingerprints for deduplication (Spec 56, 57)."""
    fp1 = compute_cascade_fingerprint("db_master", "FAILURE", ["db_master", "read_replica", "api_gateway"], "FAILURE_CASCADE")
    fp2 = compute_cascade_fingerprint("db_master", "FAILURE", ["db_master", "read_replica", "api_gateway"], "FAILURE_CASCADE")
    fp3 = compute_cascade_fingerprint("db_master", "STATE_CHANGE", ["db_master", "read_replica", "api_gateway"], "FAILURE_CASCADE")

    assert fp1 == fp2
    assert fp1 != fp3


def test_bottleneck_centrality_and_spof_criticality():
    """Verify bottleneck identification, reach ranking, and Single Point of Failure categorization (Spec 13, 14)."""
    engine = GraphSnapshotEngine()
    # Hub-and-spoke: Hub depends on Nothing, 6 nodes depend on Hub
    edges = [
        PropagationEdge(
            edge_id=f"e_hub_{i}",
            source_entity="central_database",
            target_entity=f"service_{i}",
            relationship_type=RelationshipType.DEPENDS_ON,
            redundancy_state=RedundancyState.NONE,
        )
        for i in range(6)
    ]
    snapshot = engine.create_snapshot(edges=edges)
    analyzer = BottleneckAnalyzer()

    bottlenecks, spofs = analyzer.analyze(snapshot, critical_path_entities={"central_database"})

    assert len(bottlenecks) >= 1
    top_bottleneck = bottlenecks[0]
    assert top_bottleneck.entity_id == "central_database"
    assert top_bottleneck.downstream_reach == 6
    assert top_bottleneck.critical_path_participant is True

    assert len(spofs) >= 1
    top_spof = spofs[0]
    assert top_spof.entity_id == "central_database"
    assert top_spof.criticality == CriticalityLevel.CRITICAL
    assert top_spof.dependent_count == 6


def test_redundancy_damping_mitigates_severity():
    """Verify that verified full redundancy reduces downstream cascade severity (Spec 15)."""
    engine = GraphSnapshotEngine()

    # Case A: Zero redundancy
    edges_no_redundancy = [
        PropagationEdge(
            edge_id="e_non_red",
            source_entity="primary",
            target_entity="downstream",
            relationship_type=RelationshipType.DEPENDS_ON,
            redundancy_state=RedundancyState.NONE,
        )
    ]
    snap_no_red = engine.create_snapshot(edges=edges_no_redundancy)

    # Case B: Full redundancy
    edges_full_redundancy = [
        PropagationEdge(
            edge_id="e_red",
            source_entity="primary",
            target_entity="downstream",
            relationship_type=RelationshipType.DEPENDS_ON,
            redundancy_state=RedundancyState.FULL,
            redundancy_alternatives=["primary_standby"],
        )
    ]
    snap_full_red = engine.create_snapshot(edges=edges_full_redundancy)

    traverser = BoundedPropagationTraverser()
    res_no_red = traverser.traverse("primary", snap_no_red)
    res_full_red = traverser.traverse("primary", snap_full_red)

    impact_no_red = res_no_red.direct_effects[0].impact.operational_impact
    impact_full_red = res_full_red.direct_effects[0].impact.operational_impact

    # Full redundancy must significantly dampen downstream impact
    assert impact_full_red < impact_no_red
