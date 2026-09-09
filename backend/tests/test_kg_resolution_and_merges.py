"""Unit tests for entity resolution, collision prevention, merging, and splitting."""

import pytest

from app.knowledge_graph.nodes import NodeManager
from app.knowledge_graph.resolver import EntityCollisionError, EntityResolver
from app.knowledge_graph.schemas import NodeType, ScopeType


def test_entity_resolution_and_aliases():
    nm = NodeManager()
    resolver = EntityResolver(nm)

    node = nm.create_node(
        canonical_name="Kairo Project",
        node_type=NodeType.PROJECT,
        aliases=["kairo-core", "kairo_ai"],
        scope=ScopeType.PROJECT,
        user_id="user_1",
    )

    # Resolution by exact canonical name
    assert resolver.resolve_entity("Kairo Project").node_id == node.node_id
    # Resolution case-insensitive
    assert resolver.resolve_entity("kairo project").node_id == node.node_id
    # Resolution by alias
    assert resolver.resolve_entity("kairo-core").node_id == node.node_id
    assert resolver.resolve_entity("kairo_ai").node_id == node.node_id

    # Filter by type mismatch
    assert resolver.resolve_entity("Kairo Project", expected_type=NodeType.PERSON) is None

    # Unknown entity
    assert resolver.resolve_entity("NonExistentEntity") is None


def test_entity_collision_prevention():
    nm = NodeManager()
    resolver = EntityResolver(nm)

    p1 = nm.create_node("Alice Smith", NodeType.PERSON)
    repo = nm.create_node("Alice Repo", NodeType.REPOSITORY)

    # Invariant 30: Different types cannot be merged
    with pytest.raises(EntityCollisionError, match="Type mismatch"):
        resolver.merge_entities(p1.node_id, repo.node_id, authorized_by="system", confidence=0.99)

    p2 = nm.create_node("Alice Smyth", NodeType.PERSON)
    # Low confidence automated merge rejected without explicit user authorization
    with pytest.raises(EntityCollisionError, match="Automated merge rejected due to low confidence"):
        resolver.merge_entities(p1.node_id, p2.node_id, authorized_by="system", confidence=0.75)


def test_entity_merge_and_split_provenance():
    nm = NodeManager()
    resolver = EntityResolver(nm)

    p1 = nm.create_node("Bob Vance", NodeType.PERSON, aliases=["Bob V"])
    p2 = nm.create_node("Robert Vance", NodeType.PERSON, aliases=["Vance Refrigeration Guy"])

    # Merge p2 into p1
    merged = resolver.merge_entities(p1.node_id, p2.node_id, authorized_by="user", confidence=0.95)
    assert merged.node_id == p1.node_id
    assert "Robert Vance" in merged.aliases or "robert vance" in [a.lower() for a in merged.aliases]
    assert p2.status == "MERGED"

    lineage = resolver.get_lineage(p1.node_id)
    assert len(lineage) == 1
    assert lineage[0]["action"] == "MERGE"
    assert lineage[0]["authorized_by"] == "user"

    # Split incorrect entity
    split_node = resolver.split_entity(
        primary_node_id=p1.node_id,
        split_name="Robert Vance",
        split_aliases=["Vance Refrigeration Guy"],
        authorized_by="user",
    )
    assert split_node.canonical_name == "Robert Vance"
    assert "Robert Vance" not in p1.aliases

    split_lineage = resolver.get_lineage(p1.node_id)
    assert len(split_lineage) == 2
    assert split_lineage[1]["action"] == "SPLIT"
