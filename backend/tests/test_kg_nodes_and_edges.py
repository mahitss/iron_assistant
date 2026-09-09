"""Unit tests for knowledge graph nodes, edges, integrity, and scope boundaries."""

from datetime import UTC, datetime, timedelta
import pytest

from app.knowledge_graph.edges import EdgeIntegrityError, EdgeManager
from app.knowledge_graph.nodes import NodeManager, NodeValidationError
from app.knowledge_graph.schemas import (
    NodeType,
    RelationshipType,
    ScopeType,
)


def test_node_creation_and_alias_indexing():
    manager = NodeManager()

    node = manager.create_node(
        canonical_name="AuthService",
        node_type=NodeType.SERVICE,
        aliases=["auth-api", "authentication_service"],
        scope=ScopeType.PROJECT,
        user_id="user_admin",
        project_id="proj_core",
    )

    assert node.canonical_name == "AuthService"
    assert node.node_type == NodeType.SERVICE
    assert "auth-api" in node.aliases

    # Lookup by canonical name
    by_name = manager.find_by_name("authservice")
    assert by_name is not None
    assert by_name.node_id == node.node_id

    # Lookup by alias
    by_alias = manager.find_by_name("auth-api")
    assert by_alias is not None
    assert by_alias.node_id == node.node_id

    # Add dynamic alias
    manager.add_alias(node.node_id, "auth_v1")
    assert manager.find_by_name("auth_v1") is not None

    # Empty name fails
    with pytest.raises(NodeValidationError):
        manager.create_node(canonical_name="   ")


def test_edge_referential_integrity():
    nodes = NodeManager()
    edges = EdgeManager(nodes)

    src = nodes.create_node("ServiceA", NodeType.SERVICE)
    tgt = nodes.create_node("DatabaseB", NodeType.RESOURCE)

    # Valid edge
    edge = edges.create_edge(
        source_node_id=src.node_id,
        relationship=RelationshipType.DEPENDS_ON,
        target_node_id=tgt.node_id,
    )
    assert edge.relationship == RelationshipType.DEPENDS_ON
    assert len(edges.get_outgoing_edges(src.node_id)) == 1
    assert len(edges.get_incoming_edges(tgt.node_id)) == 1

    # INVARIANT 248: Referenced nodes must exist
    with pytest.raises(EdgeIntegrityError, match="Source node 'fake_src' does not exist"):
        edges.create_edge("fake_src", RelationshipType.DEPENDS_ON, tgt.node_id)

    with pytest.raises(EdgeIntegrityError, match="Target node 'fake_tgt' does not exist"):
        edges.create_edge(src.node_id, RelationshipType.DEPENDS_ON, "fake_tgt")


def test_edge_temporal_integrity():
    nodes = NodeManager()
    edges = EdgeManager(nodes)

    src = nodes.create_node("Node1", NodeType.PROJECT)
    tgt = nodes.create_node("Node2", NodeType.REPOSITORY)

    now = datetime.now(UTC)
    past = now - timedelta(days=5)

    # INVARIANT 247: valid_until cannot precede valid_from
    with pytest.raises(EdgeIntegrityError, match="valid_until .* cannot precede valid_from"):
        edges.create_edge(
            source_node_id=src.node_id,
            relationship=RelationshipType.OWNS,
            target_node_id=tgt.node_id,
            valid_from=now,
            valid_until=past,
        )
