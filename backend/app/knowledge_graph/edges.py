"""Edge management, relationship semantics, referential integrity, and temporal validity checks."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
import uuid

from app.knowledge_graph.nodes import NodeManager
from app.knowledge_graph.schemas import (
    KnowledgeEdgeSchema,
    RelationshipType,
    ScopeType,
)


class EdgeIntegrityError(Exception):
    """Raised when an edge violates referential, temporal, or scope integrity."""
    pass


class EdgeManager:
    """Manages knowledge graph edges with strict referential, scope, and temporal integrity."""

    def __init__(self, node_manager: NodeManager) -> None:
        self.node_manager = node_manager
        # edge_id -> KnowledgeEdgeSchema
        self._edges: Dict[str, KnowledgeEdgeSchema] = {}
        # source_node_id -> set of edge_ids
        self._out_edges: Dict[str, set[str]] = {}
        # target_node_id -> set of edge_ids
        self._in_edges: Dict[str, set[str]] = {}

    def create_edge(
        self,
        source_node_id: str,
        relationship: RelationshipType,
        target_node_id: str,
        confidence: float = 1.0,
        provenance: Optional[Dict[str, Any]] = None,
        valid_from: Optional[datetime] = None,
        valid_until: Optional[datetime] = None,
        scope: ScopeType = ScopeType.PRIVATE,
        user_id: str = "default_user",
        project_id: Optional[str] = None,
        edge_id: Optional[str] = None,
    ) -> KnowledgeEdgeSchema:
        # 1. INVARIANT 248: Referenced nodes must exist
        src = self.node_manager.get_node(source_node_id)
        if not src:
            raise EdgeIntegrityError(f"Source node '{source_node_id}' does not exist.")

        tgt = self.node_manager.get_node(target_node_id)
        if not tgt:
            raise EdgeIntegrityError(f"Target node '{target_node_id}' does not exist.")

        # 2. INVARIANT 247: Temporal integrity: valid_until >= valid_from
        if valid_from and valid_until and valid_until < valid_from:
            raise EdgeIntegrityError(
                f"Temporal integrity violation: valid_until ({valid_until}) cannot precede valid_from ({valid_from})."
            )

        # 3. INVARIANT 249: Scope integrity: edge scope cannot exceed source/target authorization
        # E.g. a GLOBAL edge cannot connect purely PRIVATE nodes of different owners
        if src.user_id != user_id and scope == ScopeType.PRIVATE:
            raise EdgeIntegrityError("Cannot create private edge for a node owned by another user.")

        e_id = edge_id or str(uuid.uuid4())
        edge = KnowledgeEdgeSchema(
            edge_id=e_id,
            source_node_id=source_node_id,
            relationship=relationship,
            target_node_id=target_node_id,
            confidence=min(max(confidence, 0.0), 1.0),
            provenance=provenance or {"source": "direct_assertion"},
            valid_from=valid_from or datetime.now(UTC),
            valid_until=valid_until,
            scope=scope,
            status="ACTIVE",
            user_id=user_id,
            project_id=project_id or src.project_id or tgt.project_id,
        )

        self._edges[e_id] = edge
        self._out_edges.setdefault(source_node_id, set()).add(e_id)
        self._in_edges.setdefault(target_node_id, set()).add(e_id)

        return edge

    def get_edge(self, edge_id: str) -> Optional[KnowledgeEdgeSchema]:
        return self._edges.get(edge_id)

    def get_outgoing_edges(self, node_id: str) -> List[KnowledgeEdgeSchema]:
        e_ids = self._out_edges.get(node_id, set())
        return [self._edges[eid] for eid in e_ids if eid in self._edges and self._edges[eid].status == "ACTIVE"]

    def get_incoming_edges(self, node_id: str) -> List[KnowledgeEdgeSchema]:
        e_ids = self._in_edges.get(node_id, set())
        return [self._edges[eid] for eid in e_ids if eid in self._edges and self._edges[eid].status == "ACTIVE"]

    def delete_edge(self, edge_id: str) -> bool:
        edge = self._edges.pop(edge_id, None)
        if edge:
            if edge.source_node_id in self._out_edges:
                self._out_edges[edge.source_node_id].discard(edge_id)
            if edge.target_node_id in self._in_edges:
                self._in_edges[edge.target_node_id].discard(edge_id)
            return True
        return False
