"""Unified graph retrieval: structural, semantic, temporal, and path queries (INVARIANTS 85-87, 169-174)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.knowledge_graph.graph import KnowledgeGraph
from app.knowledge_graph.schemas import (
    GraphQueryResultSchema,
    KnowledgeEdgeSchema,
    KnowledgeNodeSchema,
    NodeType,
    RelationshipType,
)


class GraphRetrievalEngine:
    """Executes structural, semantic, temporal, and path queries with bounded context budgets."""

    def __init__(self, graph: KnowledgeGraph) -> None:
        self.graph = graph

    def query_structural(
        self,
        node_id: str,
        relationship: RelationshipType,
        direction: str = "outgoing",  # outgoing, incoming, or both
        user_id: Optional[str] = None,
    ) -> List[KnowledgeNodeSchema]:
        """INVARIANT 170: Structural query e.g. 'Which tasks depend on deployment X?'."""
        matched_node_ids: set[str] = set()

        if direction in ("outgoing", "both"):
            for e in self.graph.edges.get_outgoing_edges(node_id):
                if e.relationship == relationship:
                    matched_node_ids.add(e.target_node_id)

        if direction in ("incoming", "both"):
            for e in self.graph.edges.get_incoming_edges(node_id):
                if e.relationship == relationship:
                    matched_node_ids.add(e.source_node_id)

        nodes: List[KnowledgeNodeSchema] = []
        for nid in matched_node_ids:
            n = self.graph.nodes.get_node(nid)
            if n and n.status == "ACTIVE":
                if user_id and n.user_id != user_id and n.scope.value == "PRIVATE":
                    continue
                nodes.append(n)

        return nodes

    def query_semantic(
        self,
        keyword: str,
        node_type: Optional[NodeType] = None,
        user_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[KnowledgeNodeSchema]:
        """INVARIANT 171: Semantic keyword search over nodes, aliases, and metadata."""
        kw = keyword.lower().strip()
        candidates = self.graph.nodes.list_nodes(node_type=node_type, user_id=user_id)
        matched = []

        for n in candidates:
            in_name = kw in n.canonical_name.lower()
            in_alias = any(kw in a.lower() for a in n.aliases)
            in_meta = any(kw in str(v).lower() for v in n.metadata.values())
            if in_name or in_alias or in_meta:
                matched.append(n)
                if len(matched) >= limit:
                    break

        return matched

    def query_path(
        self,
        source_node_id: str,
        target_node_id: str,
        max_depth: int = 3,
    ) -> Optional[GraphQueryResultSchema]:
        """INVARIANT 173 & 174: Path queries explaining connectivity with bounded depth."""
        return self.graph.find_path(source_node_id, target_node_id, max_depth=max_depth)
