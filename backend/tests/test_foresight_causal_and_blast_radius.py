"""Tests for Foresight Causal Graphs, Blast Radius, and Degradation Paths (Task 65)."""

import pytest

from app.foresight.causal_propagation import CausalPropagationEngine
from app.foresight.relationships import ForesightRelationshipManager
from app.foresight.safety import ForesightSafetyError
from app.foresight.schemas import (
    ForesightRelationship,
    RelationshipType,
)


def test_correlation_not_causation_invariant():
    """Verify CORRELATION != CAUSATION invariant (Spec 11).

    A CAUSES relationship requires explicit empirical evidence or intervention backing.
    """
    rel_mgr = ForesightRelationshipManager()

    # Attempting to add a CAUSES edge without empirical evidence raises ForesightSafetyError
    with pytest.raises(ForesightSafetyError) as exc_info:
        rel_mgr.add_relationship(
            source_entity_id="node-a",
            target_entity_id="node-b",
            relationship_type=RelationshipType.CAUSES,
            causal_strength=0.95,
            evidence=[],  # No empirical evidence provided
        )
    assert "Causal Invariant Violation" in str(exc_info.value)

    # Adding with empirical evidence succeeds
    rel = rel_mgr.add_relationship(
        source_entity_id="node-a",
        target_entity_id="node-b",
        relationship_type=RelationshipType.CAUSES,
        causal_strength=0.95,
        evidence=["Chaos engineering failure injection test #402"],
    )
    assert rel.causal_strength == 0.95


def test_causal_blast_radius_computation():
    """Verify transitive blast radius calculation across dependency graphs (Spec 20)."""
    engine = CausalPropagationEngine()

    # Graph: node-a affects node-b, node-b depends on node-c, node-b affects node-d
    rels = [
        ForesightRelationship(
            rel_id="r1",
            source_entity_id="node-a",
            target_entity_id="node-b",
            relationship_type=RelationshipType.AFFECTS,
        ),
        ForesightRelationship(
            rel_id="r2",
            source_entity_id="node-b",
            target_entity_id="node-c",
            relationship_type=RelationshipType.AFFECTS,
        ),
        ForesightRelationship(
            rel_id="r3",
            source_entity_id="node-c",
            target_entity_id="node-d",
            relationship_type=RelationshipType.AFFECTS,
        ),
    ]

    blast = engine.compute_blast_radius("node-a", rels)
    # Downstream dependents of node-a should include b, c, d
    assert "node-b" in blast
    assert "node-c" in blast
    assert "node-d" in blast


def test_cascading_degradation_paths():
    """Verify multi-hop cascading impact path tracing (Spec 21)."""
    engine = CausalPropagationEngine()

    rels = [
        ForesightRelationship(
            rel_id="r1",
            source_entity_id="db_primary",
            target_entity_id="svc_orders",
            relationship_type=RelationshipType.CAUSES,
            causal_strength=0.9,
            evidence=["Load test simulation"],
        ),
        ForesightRelationship(
            rel_id="r2",
            source_entity_id="svc_orders",
            target_entity_id="svc_checkout",
            relationship_type=RelationshipType.AFFECTS,
            causal_strength=0.85,
        ),
    ]

    steps = engine.propagate_cascading_impact(
        failing_entity_id="db_primary",
        entities={},
        relationships=rels,
        initial_impact=0.9,
    )
    assert len(steps) >= 1
    affected_ids = [s["affected_entity_id"] for s in steps]
    assert "svc_orders" in affected_ids


def test_single_point_of_failure_detection():
    """Verify identification of high-centrality critical bottlenecks (Spec 22)."""
    engine = CausalPropagationEngine()

    # Multiple services depend on auth_service
    rels = [
        ForesightRelationship(
            rel_id="r1",
            source_entity_id="client_web",
            target_entity_id="auth_service",
            relationship_type=RelationshipType.DEPENDS_ON,
        ),
        ForesightRelationship(
            rel_id="r2",
            source_entity_id="client_mobile",
            target_entity_id="auth_service",
            relationship_type=RelationshipType.DEPENDS_ON,
        ),
        ForesightRelationship(
            rel_id="r3",
            source_entity_id="internal_api",
            target_entity_id="auth_service",
            relationship_type=RelationshipType.DEPENDS_ON,
        ),
    ]

    spofs = engine.identify_single_points_of_failure(entities=[], relationships=rels, critical_threshold=2)
    assert "auth_service" in spofs
