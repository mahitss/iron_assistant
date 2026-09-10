"""Unit tests for Environmental Topology, Canonical Nodes, and Anti-False Topology (Task 54)."""

import pytest

from app.environment.edges import create_environment_edge
from app.environment.nodes import create_environment_node, generate_canonical_id
from app.environment.safety import (
    FalseTopologyError,
    SecretStorageViolationError,
)
from app.environment.schemas import (
    NodeType,
    RelationshipConfidence,
    RelationshipType,
)
from app.environment.topology import TopologyGraph


def test_canonical_id_generation():
    cid1 = generate_canonical_id(NodeType.SERVICE, "checkout-service", scope_id="production")
    cid2 = generate_canonical_id(NodeType.DATABASE, "postgres-users", scope_id="production")
    cid3 = generate_canonical_id(NodeType.DEVICE, "laptop-01")

    assert cid1 == "service:production:checkout-service"
    assert cid2 == "database:production:postgres-users"
    assert cid3 == "device:laptop-01"


def test_node_creation_and_secret_rejection():
    # Regular node creates cleanly
    node = create_environment_node(
        node_id="svc_api",
        node_type=NodeType.SERVICE,
        canonical_id="service:prod:api",
        display_name="API Gateway",
        metadata={"port": 8080, "protocol": "https"},
    )
    assert node.node_id == "svc_api"
    assert node.metadata["port"] == 8080

    # Secret reference with raw secret value raises SecretStorageViolationError
    with pytest.raises(SecretStorageViolationError):
        create_environment_node(
            node_id="sec_db",
            node_type=NodeType.SECRET_REFERENCE,
            canonical_id="secret:prod:db",
            display_name="DB Secret",
            metadata={"secret_value": "super_secret_password_123"},
        )


def test_anti_false_topology_invariant():
    """Prompt #10, #197: Do not claim dependency merely because two services exist in the same environment."""
    # Co-location in the same environment cannot justify an OBSERVED or VERIFIED dependency
    with pytest.raises(FalseTopologyError):
        create_environment_edge(
            source="svc_auth",
            relationship=RelationshipType.DEPENDS_ON,
            target="svc_analytics",
            confidence=RelationshipConfidence.VERIFIED,
            provenance={"source": "same_environment_heuristic"},
            is_same_environment_only=True,
        )

    # Self-referential external dependency is rejected
    with pytest.raises(FalseTopologyError):
        create_environment_edge(
            source="svc_auth",
            relationship=RelationshipType.DEPENDS_ON,
            target="svc_auth",
            confidence=RelationshipConfidence.OBSERVED,
            provenance={"source": "telemetry"},
        )

    # Legitimate verified edge with verified provenance succeeds
    legit_edge = create_environment_edge(
        source="svc_auth",
        relationship=RelationshipType.CALLS,
        target="svc_db",
        confidence=RelationshipConfidence.VERIFIED,
        provenance={"source": "distributed_trace", "trace_id": "tr_12345"},
        is_same_environment_only=False,
    )
    assert legit_edge.edge_id == "edge:svc_auth::CALLS::svc_db"
    assert legit_edge.status == "ACTIVE"


def test_topology_graph_and_cycle_detection():
    """Prompt #48: Detect dependency cycles in topology."""
    n1 = create_environment_node("s1", NodeType.SERVICE, "s:1", "Service 1")
    n2 = create_environment_node("s2", NodeType.SERVICE, "s:2", "Service 2")
    n3 = create_environment_node("s3", NodeType.SERVICE, "s:3", "Service 3")

    e1 = create_environment_edge("s1", RelationshipType.CALLS, "s2", provenance={"source": "trace"})
    e2 = create_environment_edge("s2", RelationshipType.CALLS, "s3", provenance={"source": "trace"})
    e3 = create_environment_edge("s3", RelationshipType.CALLS, "s1", provenance={"source": "trace"})  # creates cycle s1 -> s2 -> s3 -> s1

    nodes = {n.node_id: n for n in [n1, n2, n3]}
    edges = {e.edge_id: e for e in [e1, e2, e3]}

    graph = TopologyGraph(nodes, edges)
    cycles = graph.find_dependency_cycles()

    assert len(cycles) > 0
    cycle_nodes = set(cycles[0])
    assert "s1" in cycle_nodes and "s2" in cycle_nodes and "s3" in cycle_nodes


def test_single_point_of_failure_and_critical_dependencies():
    """Prompt #49, #50: Identify critical dependencies and SPoFs."""
    db_node = create_environment_node("db_primary", NodeType.DATABASE, "db:primary", "Primary PostgreSQL")
    s1 = create_environment_node("svc_billing", NodeType.SERVICE, "svc:billing", "Billing Service")
    s2 = create_environment_node("svc_orders", NodeType.SERVICE, "svc:orders", "Orders Service")
    s3 = create_environment_node("svc_users", NodeType.SERVICE, "svc:users", "Users Service")

    e1 = create_environment_edge("svc_billing", RelationshipType.READS_FROM, "db_primary", provenance={"source": "telemetry"})
    e2 = create_environment_edge("svc_orders", RelationshipType.READS_FROM, "db_primary", provenance={"source": "telemetry"})
    e3 = create_environment_edge("svc_users", RelationshipType.READS_FROM, "db_primary", provenance={"source": "telemetry"})

    nodes = {n.node_id: n for n in [db_node, s1, s2, s3]}
    edges = {e.edge_id: e for e in [e1, e2, e3]}

    graph = TopologyGraph(nodes, edges)
    critical = graph.identify_critical_dependencies(min_dependents=2)
    assert len(critical) == 1
    assert critical[0]["node_id"] == "db_primary"
    assert critical[0]["dependent_count"] == 3

    spofs = graph.find_single_points_of_failure()
    assert len(spofs) == 1
    assert spofs[0]["node_id"] == "db_primary"


def test_bounded_graph_traversal():
    """Prompt #176-#179: Prevent graph explosion via depth and node count bounds."""
    # Build long chain: n0 -> n1 -> n2 -> ... -> n10
    nodes = {}
    edges = {}
    for i in range(10):
        n = create_environment_node(f"n_{i}", NodeType.SERVICE, f"s:{i}", f"Service {i}")
        nodes[n.node_id] = n
        if i > 0:
            e = create_environment_edge(f"n_{i-1}", RelationshipType.CALLS, f"n_{i}", provenance={"source": "trace"})
            edges[e.edge_id] = e

    graph = TopologyGraph(nodes, edges)

    # Traversal bounded at depth 2
    res = graph.bounded_traversal(start_node_id="n_0", direction="outgoing", max_depth=2, max_nodes=50)
    assert res["total_visited"] <= 3  # n_0, n_1, n_2
    assert "n_0" in res["visited_node_ids"]
    assert "n_1" in res["visited_node_ids"]
    assert "n_2" in res["visited_node_ids"]
    assert "n_5" not in res["visited_node_ids"]
