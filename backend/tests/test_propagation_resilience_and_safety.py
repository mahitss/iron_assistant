"""Unit tests for resilience modeling, counterfactuals, containment, and safety boundaries (Task 75)."""

import pytest

from app.propagation.resilience import ResilienceEngine
from app.propagation.schemas import (
    BoundaryType,
    PropagationEdge,
    RedundancyState,
    RelationshipType,
)
from app.propagation.snapshots import GraphSnapshotEngine
from app.propagation.traversal import BoundedPropagationTraverser


def test_resilience_assessment_and_containment_boundaries():
    """Verify multi-factor resilience score and detection of containment barriers (Spec 16, 30)."""
    engine = GraphSnapshotEngine()
    edges = [
        PropagationEdge(
            edge_id="e1",
            source_entity="frontend",
            target_entity="api_gateway",
            relationship_type=RelationshipType.DEPENDS_ON,
            redundancy_state=RedundancyState.FULL,
        ),
        PropagationEdge(
            edge_id="e2",
            source_entity="api_gateway",
            target_entity="payment_service",
            relationship_type=RelationshipType.SUPPRESSES,  # Damping / circuit breaker
            confidence=0.9,
        ),
    ]
    snapshot = engine.create_snapshot(edges=edges)
    traverser = BoundedPropagationTraverser()
    resilience_engine = ResilienceEngine()

    result = traverser.traverse("frontend", snapshot)
    assessment = resilience_engine.assess_resilience(snapshot, result)

    assert 0.0 <= assessment.systemic_resilience_score <= 1.0
    assert assessment.redundancy_ratio > 0.0
    assert len(assessment.containment_boundaries) >= 1
    assert assessment.containment_boundaries[0].boundary_type == BoundaryType.CIRCUIT_BREAKER


def test_counterfactual_simulation_never_confused_with_reality():
    """Verify counterfactual analysis simulates interventions and is marked SIMULATION_RESULT (Spec 32, 67)."""
    engine = GraphSnapshotEngine()
    edges = [
        PropagationEdge(edge_id="e1", source_entity="svc_a", target_entity="svc_b", relationship_type=RelationshipType.DEPENDS_ON),
        PropagationEdge(edge_id="e2", source_entity="svc_b", target_entity="svc_c", relationship_type=RelationshipType.DEPENDS_ON),
    ]
    snapshot = engine.create_snapshot(edges=edges)
    resilience_engine = ResilienceEngine()

    cf_result = resilience_engine.simulate_counterfactual(
        origin_entity="svc_a",
        snapshot=snapshot,
        intervention_type="REMOVE_DEPENDENCY",
        target_entity="svc_b",
    )

    # Invariant: Must strictly be marked as SIMULATION_RESULT, not observed reality
    assert cf_result["epistemic_status"] == "SIMULATION_RESULT"
    assert cf_result["relative_risk_reduction"] > 0.0
    assert cf_result["counterfactual_nodes_affected"] < cf_result["baseline_nodes_affected"]


def test_mitigations_are_strictly_advisory_and_require_approval():
    """Verify recommendations are strictly advisory and require governance approval (Spec 31, 71)."""
    engine = GraphSnapshotEngine()
    edges = [
        PropagationEdge(edge_id="e1", source_entity="alpha", target_entity="beta", relationship_type=RelationshipType.DEPENDS_ON),
    ]
    snapshot = engine.create_snapshot(edges=edges)
    traverser = BoundedPropagationTraverser()
    resilience_engine = ResilienceEngine()

    result = traverser.traverse("alpha", snapshot)
    assessment = resilience_engine.assess_resilience(snapshot, result)
    mitigations = resilience_engine.generate_mitigations(result, assessment)

    assert len(mitigations) >= 1
    for m in mitigations:
        assert m.is_advisory_only is True
        assert m.requires_approval is True


def test_recovery_propagation():
    """Verify downstream progressive recovery modeling (Spec 35)."""
    engine = GraphSnapshotEngine()
    edges = [
        PropagationEdge(edge_id="e1", source_entity="db", target_entity="app", relationship_type=RelationshipType.DEPENDS_ON),
        PropagationEdge(edge_id="e2", source_entity="app", target_entity="ui", relationship_type=RelationshipType.DEPENDS_ON),
    ]
    snapshot = engine.create_snapshot(edges=edges)
    resilience_engine = ResilienceEngine()

    rec_result = resilience_engine.model_recovery_propagation("db", snapshot)
    assert rec_result["origin_recovered"] == "db"
    assert rec_result["total_recovering_nodes"] == 2
    recovery_entities = [r["entity"] for r in rec_result["recovery_order"]]
    assert "app" in recovery_entities
    assert "ui" in recovery_entities
