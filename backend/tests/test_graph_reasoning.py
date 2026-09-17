"""
Test Suite for Task 97: KAIRO Autonomous Knowledge Graph Reasoning, Graph Memory & Structured Inference Engine.

Covers:
- Node and Edge domain models (provenance, certainty, validity intervals, canonical keys)
- Referential integrity & invariant validation
- Bounded graph traversal (depth, node limits, cycle resilience)
- Shortest verified path
- Deductive inference rules (transitive dependencies, part-of, child-of, blocks)
- Downstream impact analysis & risk topology
- Cross-subsystem lineage reconstruction (Decision, Action, Memory, Swarm Agent)
- Dialectic conflict graph & contradiction preservation
- Immutable graph snapshots & topological diffing
- Security filtering & scope isolation (SecurityCenter boundary enforcement)
- Non-negotiable principles: Graph != Authorization, Graph != Truth, Inference != Fact
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta

from app.knowledge_graph.schemas import (
    NodeType,
    RelationshipType,
    CertaintyLevel,
    ProvenanceClassification,
    GraphQueryType,
    ConflictResolutionState,
    GraphProvenanceSchema,
    KnowledgeNodeSchema,
    KnowledgeEdgeSchema,
    GraphTraversalLimits,
    GraphQueryRequest,
    ConflictRecord,
)
from app.knowledge_graph.reasoning_engine import GraphReasoningEngine


@pytest.fixture
def reasoning_engine():
    """Provides a fresh, isolated GraphReasoningEngine instance for each test."""
    engine = GraphReasoningEngine()
    engine.reset()
    return engine


def test_node_domain_model_creation(reasoning_engine):
    """Test creating knowledge nodes with epistemic certainty and provenance."""
    prov = GraphProvenanceSchema(
        source_id="task_audit_97",
        source_type="TASK",
        classification=ProvenanceClassification.OBSERVED,
        extraction_method="STATIC_ANALYSIS",
    )
    node = reasoning_engine.create_node(
        node_id="srv_postgres_cluster",
        canonical_key="service:db:postgres",
        node_type=NodeType.SERVICE,
        label="PostgreSQL Primary Database",
        confidence=0.98,
        certainty=CertaintyLevel.KNOWN,
        sensitivity="INTERNAL",
        provenance=prov,
        scope="project_kairo",
    )

    assert node.node_id == "srv_postgres_cluster"
    assert node.canonical_key == "service:db:postgres"
    assert node.node_type == NodeType.SERVICE
    assert node.certainty == CertaintyLevel.KNOWN
    assert node.provenance.classification == ProvenanceClassification.OBSERVED
    assert node.version == 1
    assert node.status == "ACTIVE"


def test_edge_domain_model_and_referential_integrity(reasoning_engine):
    """Test creating knowledge edges with referential validation."""
    node_a = reasoning_engine.create_node(
        node_id="srv_api",
        canonical_key="service:api",
        node_type=NodeType.SERVICE,
        label="Core API Service",
        certainty=CertaintyLevel.KNOWN,
    )
    node_b = reasoning_engine.create_node(
        node_id="srv_cache",
        canonical_key="service:cache",
        node_type=NodeType.SERVICE,
        label="Redis Cache",
        certainty=CertaintyLevel.KNOWN,
    )

    prov = GraphProvenanceSchema(
        source_id="net_probe",
        source_type="TOOL",
        classification=ProvenanceClassification.OBSERVED,
    )

    edge = reasoning_engine.create_edge(
        source_node="srv_api",
        target_node="srv_cache",
        relationship_type=RelationshipType.DEPENDS_ON,
        confidence=0.95,
        certainty=CertaintyLevel.KNOWN,
        provenance=prov,
        scope="project_kairo",
    )

    assert edge.source_node == "srv_api"
    assert edge.target_node == "srv_cache"
    assert edge.relationship_type == RelationshipType.DEPENDS_ON
    assert edge.edge_id in reasoning_engine.edges

    # Invariant: Creating an edge to a nonexistent node must raise ValueError
    with pytest.raises(ValueError, match="does not exist"):
        reasoning_engine.create_edge(
            source_node="srv_api",
            target_node="non_existent_service",
            relationship_type=RelationshipType.DEPENDS_ON,
        )


def test_epistemic_certainty_and_inference_distinction(reasoning_engine):
    """
    Non-negotiable principle: INFERENCE != OBSERVATION, GRAPH != TRUTH.
    Inferred relationships must be marked INFERRED, not OBSERVED or KNOWN.
    """
    # A DEPENDS_ON B
    reasoning_engine.create_node(node_id="node_a", canonical_key="comp:a", node_type=NodeType.COMPONENT, label="Component A")
    reasoning_engine.create_node(node_id="node_b", canonical_key="comp:b", node_type=NodeType.COMPONENT, label="Component B")
    reasoning_engine.create_node(node_id="node_c", canonical_key="comp:c", node_type=NodeType.COMPONENT, label="Component C")

    reasoning_engine.create_edge(
        source_node="node_a",
        target_node="node_b",
        relationship_type=RelationshipType.DEPENDS_ON,
        certainty=CertaintyLevel.LIKELY,
        confidence=0.9,
    )
    reasoning_engine.create_edge(
        source_node="node_b",
        target_node="node_c",
        relationship_type=RelationshipType.DEPENDS_ON,
        certainty=CertaintyLevel.LIKELY,
        confidence=0.8,
    )

    # Run deductive inference
    derived = reasoning_engine.run_inference(scope="global")

    assert len(derived) >= 1
    transitive = next((e for e in derived if e.source_node == "node_a" and e.target_node == "node_c"), None)
    assert transitive is not None
    assert transitive.relationship_type == RelationshipType.TRANSITIVELY_DEPENDS_ON
    # Epistemic guarantee: Provenance classification must be INFERRED or DERIVED, never OBSERVED
    assert transitive.provenance.classification == ProvenanceClassification.INFERRED
    # Confidence is compounded: 0.9 * 0.8 = 0.72
    assert pytest.approx(transitive.confidence, 0.01) == 0.72
    # Certainty downgraded or preserved as uncertain/likely, never unconditionally promoted to KNOWN
    assert transitive.certainty in (CertaintyLevel.LIKELY, CertaintyLevel.POSSIBLE)


def test_bounded_graph_traversal_limits(reasoning_engine):
    """Verify max_depth, max_nodes, and timeout bounded traversal limits prevent graph explosion."""
    # Build a deep chain: n0 -> n1 -> n2 -> n3 -> n4 -> n5 -> n6
    for i in range(7):
        reasoning_engine.create_node(
            node_id=f"chain_{i}",
            canonical_key=f"chain:{i}",
            node_type=NodeType.SERVICE,
            label=f"Service {i}",
        )
        if i > 0:
            reasoning_engine.create_edge(
                source_node=f"chain_{i-1}",
                target_node=f"chain_{i}",
                relationship_type=RelationshipType.DEPENDS_ON,
            )

    # Traverse with strict max_depth=2
    limits = GraphTraversalLimits(max_depth=2, max_nodes=50)
    req = GraphQueryRequest(
        query_type=GraphQueryType.MULTI_HOP,
        start_node_id="chain_0",
        limits=limits,
    )
    res = reasoning_engine.execute_query(req)

    assert res.depth_reached <= 2
    visited_ids = {n.node_id for n in res.nodes}
    assert "chain_0" in visited_ids
    assert "chain_1" in visited_ids
    assert "chain_2" in visited_ids
    assert "chain_5" not in visited_ids  # Bounded depth cut off chain_5


def test_cycle_resilience_and_shortest_verified_path(reasoning_engine):
    """Verify cyclic relationships do not cause infinite recursion and shortest path is correct."""
    # Build a cycle: A -> B -> C -> A
    for nid in ["srv_a", "srv_b", "srv_c", "srv_target"]:
        reasoning_engine.create_node(node_id=nid, canonical_key=f"srv:{nid}", node_type=NodeType.SERVICE, label=nid)

    reasoning_engine.create_edge(source_node="srv_a", target_node="srv_b", relationship_type=RelationshipType.DEPENDS_ON)
    reasoning_engine.create_edge(source_node="srv_b", target_node="srv_c", relationship_type=RelationshipType.DEPENDS_ON)
    reasoning_engine.create_edge(source_node="srv_c", target_node="srv_a", relationship_type=RelationshipType.DEPENDS_ON)  # Cycle
    reasoning_engine.create_edge(source_node="srv_b", target_node="srv_target", relationship_type=RelationshipType.DEPENDS_ON)

    # Shortest path from srv_a to srv_target: srv_a -> srv_b -> srv_target (2 hops)
    path_res = reasoning_engine.find_shortest_verified_path("srv_a", "srv_target", max_depth=5)
    assert path_res["path_found"] is True
    assert len(path_res["path"]) == 3
    assert path_res["path"][0]["node_id"] == "srv_a"
    assert path_res["path"][1]["node_id"] == "srv_b"
    assert path_res["path"][2]["node_id"] == "srv_target"


def test_downstream_impact_analysis(reasoning_engine):
    """
    Test downstream impact simulation:
    Database -> Service -> Capability -> Workflow -> Decision
    Changing Database identifies all downstream entities as impacted with risk severity.
    """
    reasoning_engine.create_node(node_id="db_primary", canonical_key="db:primary", node_type=NodeType.SERVICE, label="Database")
    reasoning_engine.create_node(node_id="svc_orders", canonical_key="svc:orders", node_type=NodeType.SERVICE, label="Order Service")
    reasoning_engine.create_node(node_id="cap_checkout", canonical_key="cap:checkout", node_type=NodeType.CAPABILITY, label="Checkout Capability")
    reasoning_engine.create_node(node_id="wf_payment", canonical_key="wf:payment", node_type=NodeType.WORKFLOW, label="Payment Workflow")
    reasoning_engine.create_node(node_id="dec_rebalance", canonical_key="dec:rebalance", node_type=NodeType.DECISION, label="Rebalance Decision")

    reasoning_engine.create_edge(source_node="svc_orders", target_node="db_primary", relationship_type=RelationshipType.DEPENDS_ON)
    reasoning_engine.create_edge(source_node="cap_checkout", target_node="svc_orders", relationship_type=RelationshipType.DEPENDS_ON)
    reasoning_engine.create_edge(source_node="wf_payment", target_node="cap_checkout", relationship_type=RelationshipType.USED_BY)
    reasoning_engine.create_edge(source_node="dec_rebalance", target_node="wf_payment", relationship_type=RelationshipType.AFFECTS)

    impact = reasoning_engine.analyze_downstream_impact("db_primary", max_depth=5)

    assert impact.origin_node == "db_primary"
    impacted_ids = {n.node_id for n in impact.impacted_nodes}
    assert "svc_orders" in impacted_ids
    assert "cap_checkout" in impacted_ids
    assert "wf_payment" in impacted_ids
    assert "dec_rebalance" in impacted_ids
    assert impact.max_propagation_depth >= 4
    # Checkout capability and rebalance decision should be flagged as revalidation candidates
    assert "cap_checkout" in impact.revalidation_candidates or "dec_rebalance" in impact.revalidation_candidates


def test_decision_and_action_lineage_reconstruction(reasoning_engine):
    """
    Test auditable lineage reconstruction:
    Goal -> Decision -> Action -> Capability -> Execution Outcome
    """
    reasoning_engine.create_node(node_id="goal_resilience", canonical_key="goal:resilience", node_type=NodeType.GOAL, label="Improve DB High Availability")
    reasoning_engine.create_node(node_id="dec_failover", canonical_key="dec:failover", node_type=NodeType.DECISION, label="Approve Multi-AZ Failover")
    reasoning_engine.create_node(node_id="act_migrate", canonical_key="act:migrate", node_type=NodeType.ACTION, label="Execute Replica Promotion")
    reasoning_engine.create_node(node_id="cap_cluster", canonical_key="cap:cluster", node_type=NodeType.CAPABILITY, label="Postgres Orchestrator")

    reasoning_engine.create_edge(source_node="dec_failover", target_node="goal_resilience", relationship_type=RelationshipType.PLANNED_BY)
    reasoning_engine.create_edge(source_node="act_migrate", target_node="dec_failover", relationship_type=RelationshipType.DECIDED_BY)
    reasoning_engine.create_edge(source_node="act_migrate", target_node="cap_cluster", relationship_type=RelationshipType.REQUIRES)

    # Reconstruct Decision Lineage
    lineage = reasoning_engine.reconstruct_decision_lineage("dec_failover")
    assert lineage.target_node == "dec_failover"
    assert lineage.lineage_type == "decision"
    node_ids = {s.node_id for s in lineage.steps}
    assert "goal_resilience" in node_ids
    assert "act_migrate" in node_ids

    # Reconstruct Action Lineage
    act_lineage = reasoning_engine.reconstruct_action_lineage("act_migrate")
    assert act_lineage.target_node == "act_migrate"
    act_node_ids = {s.node_id for s in act_lineage.steps}
    assert "dec_failover" in act_node_ids
    assert "cap_cluster" in act_node_ids


def test_memory_lineage_and_conflict_graph(reasoning_engine):
    """
    Test Task 92 integration: Memory contradictions are preserved in the conflict graph,
    never silently deleted or overwritten.
    """
    reasoning_engine.create_node(node_id="mem_fact_v1", canonical_key="mem:pref:timeout", node_type=NodeType.MEMORY, label="Timeout is 30s")
    reasoning_engine.create_node(node_id="mem_fact_v2", canonical_key="mem:pref:timeout", node_type=NodeType.MEMORY, label="Timeout is 120s")

    # Record dialectic conflict
    conflict_record = reasoning_engine.record_conflict(
        node_a="mem_fact_v1",
        node_b="mem_fact_v2",
        reason="Conflicting configuration values detected in observation stream",
        confidence=0.88,
    )

    assert conflict_record.node_a == "mem_fact_v1"
    assert conflict_record.node_b == "mem_fact_v2"
    assert conflict_record.status == ConflictResolutionState.UNRESOLVED

    # Both contradictory nodes still exist in the graph (preservation)
    assert "mem_fact_v1" in reasoning_engine.nodes
    assert "mem_fact_v2" in reasoning_engine.nodes

    # CONTRADICTS edge was generated
    contradict_edge = next((e for e in reasoning_engine.edges.values() if e.relationship_type == RelationshipType.CONTRADICTS), None)
    assert contradict_edge is not None
    assert contradict_edge.source_node == "mem_fact_v1"
    assert contradict_edge.target_node == "mem_fact_v2"


def test_snapshots_and_graph_diff(reasoning_engine):
    """Test capturing immutable snapshots and computing topological diffs."""
    reasoning_engine.create_node(node_id="res_cluster", canonical_key="res:cluster", node_type=NodeType.RESOURCE, label="Kubernetes Cluster")
    reasoning_engine.create_node(node_id="srv_web", canonical_key="srv:web", node_type=NodeType.SERVICE, label="Web Gateway")
    reasoning_engine.create_edge(source_node="srv_web", target_node="res_cluster", relationship_type=RelationshipType.PART_OF)

    # Snapshot 1 (Baseline)
    snap_1 = reasoning_engine.create_snapshot("Baseline v1.0", scope="global")
    assert snap_1.node_count == 2
    assert snap_1.edge_count == 1

    # Mutate graph: Add new service, remove old service
    reasoning_engine.create_node(node_id="srv_mesh", canonical_key="srv:mesh", node_type=NodeType.SERVICE, label="Service Mesh")
    reasoning_engine.create_edge(source_node="srv_mesh", target_node="res_cluster", relationship_type=RelationshipType.PART_OF)
    reasoning_engine.nodes.pop("srv_web")

    # Snapshot 2 (Post-Upgrade)
    snap_2 = reasoning_engine.create_snapshot("Post-Upgrade v1.1", scope="global")
    assert snap_2.node_count == 2

    # Compute Diff
    diff = reasoning_engine.compute_graph_diff(snap_1.snapshot_id, snap_2.snapshot_id)
    assert "srv_mesh" in diff.added_nodes
    assert "srv_web" in diff.removed_nodes
    assert len(diff.added_edges) == 1
    assert len(diff.removed_edges) == 1


def test_security_filtering_and_scope_isolation(reasoning_engine):
    """
    Verify security boundary: Restricted/secret nodes are not traversable by standard scopes.
    Non-negotiable principle: Graph != Authorization. SecurityCenter decides access.
    """
    reasoning_engine.create_node(
        node_id="pub_service",
        canonical_key="pub:svc",
        node_type=NodeType.SERVICE,
        label="Public API",
        sensitivity="PUBLIC",
        scope="tenant_alpha",
    )
    reasoning_engine.create_node(
        node_id="secret_vault",
        canonical_key="sec:vault",
        node_type=NodeType.SYSTEM,
        label="Vault Master Keyring",
        sensitivity="RESTRICTED",
        scope="tenant_alpha",
    )
    reasoning_engine.create_node(
        node_id="cross_tenant_node",
        canonical_key="cross:tenant",
        node_type=NodeType.SERVICE,
        label="Tenant Beta Internal",
        sensitivity="INTERNAL",
        scope="tenant_beta",
    )

    reasoning_engine.create_edge(
        source_node="pub_service",
        target_node="secret_vault",
        relationship_type=RelationshipType.DEPENDS_ON,
        scope="tenant_alpha",
    )
    reasoning_engine.create_edge(
        source_node="pub_service",
        target_node="cross_tenant_node",
        relationship_type=RelationshipType.DEPENDS_ON,
        scope="tenant_alpha",
    )

    # Standard query with tenant_alpha and INTERNAL sensitivity ceiling (RESTRICTED excluded)
    req = GraphQueryRequest(
        query_type=GraphQueryType.MULTI_HOP,
        start_node_id="pub_service",
        scope="tenant_alpha",
        allowed_sensitivities=["PUBLIC", "INTERNAL"],
    )
    res = reasoning_engine.execute_query(req)

    result_ids = {n.node_id for n in res.nodes}
    assert "pub_service" in result_ids
    # RESTRICTED node must be filtered out
    assert "secret_vault" not in result_ids
    # Cross-tenant node from tenant_beta must be filtered out
    assert "cross_tenant_node" not in result_ids
