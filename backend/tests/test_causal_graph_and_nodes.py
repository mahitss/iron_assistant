"""Unit tests for Causal Graph, Nodes, Edges, Traversal, and Weakest-Link Confidence (Task 55)."""


from app.causal.edges import create_causal_edge
from app.causal.graph import CausalGraphEngine
from app.causal.nodes import create_causal_node, generate_node_id
from app.causal.relationships import compose_path_confidence, is_direct_causal_relationship
from app.causal.schemas import (
    CausalEdgeStatus,
    CausalRelationshipType,
    CausalScope,
)


def test_node_id_generation_and_normalization():
    """Prompt #3: Canonical entity-variable node generation."""
    nid = generate_node_id(" Database Cluster ", " Connection Pool Saturation ")
    assert nid == "cnode_database_cluster_connection_pool_saturation"

    node = create_causal_node(
        entity="api_gateway",
        variable="latency_p99",
        state=2450.0,
        source="prometheus",
        confidence=0.95,
    )
    assert node.node_id == "cnode_api_gateway_latency_p99"
    assert node.entity == "api_gateway"
    assert node.variable == "latency_p99"
    assert node.state == 2450.0
    assert node.confidence == 0.95


def test_causal_edge_validation_and_status():
    """Prompt #4, #5, #98: CausalEdge creation and relationship semantics."""
    edge = create_causal_edge(
        cause="node_a",
        effect="node_b",
        relationship=CausalRelationshipType.CAUSES,
        confidence=0.85,
        evidence_refs=["ev_123", "ev_456"],
        scope=CausalScope.SERVICE,
    )
    assert "node_a" in edge.edge_id and "node_b" in edge.edge_id
    assert edge.relationship == CausalRelationshipType.CAUSES
    assert edge.confidence == 0.85
    assert edge.status == CausalEdgeStatus.ACTIVE
    assert len(edge.evidence_refs) == 2

    assert is_direct_causal_relationship(CausalRelationshipType.CAUSES) is True
    assert is_direct_causal_relationship(CausalRelationshipType.CONTRIBUTES_TO) is True
    assert is_direct_causal_relationship(CausalRelationshipType.CORRELATES_WITH) is False
    assert is_direct_causal_relationship(CausalRelationshipType.DEPENDS_ON) is False


def test_graph_upsert_and_adjacency():
    """Prompt #2, #55: In-memory graph management and adjacency construction."""
    graph = CausalGraphEngine.create_graph(scope=CausalScope.SYSTEM, graph_id="test_graph")
    assert graph.graph_id == "test_graph"
    assert graph.version == 1

    n1 = create_causal_node("db", "sat", 1.0, "telemetry")
    n2 = create_causal_node("api", "lat", 2000, "telemetry")
    CausalGraphEngine.upsert_node(graph, n1)
    CausalGraphEngine.upsert_node(graph, n2)
    assert graph.version == 3

    edge = create_causal_edge(n1.node_id, n2.node_id, CausalRelationshipType.CAUSES, 0.8)
    CausalGraphEngine.upsert_edge(graph, edge)
    assert graph.version == 4

    adj_out, adj_in = CausalGraphEngine.build_adjacency(graph)
    assert len(adj_out[n1.node_id]) == 1
    assert adj_out[n1.node_id][0].effect == n2.node_id
    assert len(adj_in[n2.node_id]) == 1


def test_weakest_link_path_confidence():
    """Prompt #57: Combined causal confidence must account for weakest links."""
    # Weakest link along a path [0.9, 0.4, 0.85] is bounded by 0.4
    chain_confidences = [0.9, 0.4, 0.85]
    weakest = compose_path_confidence(chain_confidences)
    assert weakest <= 0.4 and weakest >= 0.35

    # Traversal bounded depth
    graph = CausalGraphEngine.create_graph(scope=CausalScope.SYSTEM)
    e1 = create_causal_edge("A", "B", CausalRelationshipType.CAUSES, 0.9)
    e2 = create_causal_edge("B", "C", CausalRelationshipType.CAUSES, 0.6)
    e3 = create_causal_edge("C", "D", CausalRelationshipType.CAUSES, 0.8)
    CausalGraphEngine.upsert_edge(graph, e1)
    CausalGraphEngine.upsert_edge(graph, e2)
    CausalGraphEngine.upsert_edge(graph, e3)

    paths = CausalGraphEngine.find_paths(graph, "A", "D", max_depth=5)
    assert len(paths) == 1
    assert paths[0]["nodes"] == ["A", "B", "C", "D"]
    assert paths[0]["confidence"] <= 0.6 and paths[0]["confidence"] >= 0.5



def test_confounding_and_collider_detection():
    """Prompt #49, #50, #51, #52: Detect common causes (confounders) and common effects (colliders)."""
    graph = CausalGraphEngine.create_graph(scope=CausalScope.SYSTEM)

    # Confounder: Z causes X and Z causes Y
    e_zx = create_causal_edge("Z", "X", CausalRelationshipType.CAUSES, 0.8)
    e_zy = create_causal_edge("Z", "Y", CausalRelationshipType.CAUSES, 0.8)
    CausalGraphEngine.upsert_edge(graph, e_zx)
    CausalGraphEngine.upsert_edge(graph, e_zy)

    confounders = CausalGraphEngine.detect_confounders(graph, "X", "Y")
    assert "Z" in confounders

    # Collider: A causes W and B causes W
    e_aw = create_causal_edge("A", "W", CausalRelationshipType.CAUSES, 0.8)
    e_bw = create_causal_edge("B", "W", CausalRelationshipType.CAUSES, 0.8)
    CausalGraphEngine.upsert_edge(graph, e_aw)
    CausalGraphEngine.upsert_edge(graph, e_bw)

    colliders = CausalGraphEngine.detect_colliders(graph, "A", "B")
    assert "W" in colliders
