"""Temporal memory, validity windows, point-in-time as-of querying, and temporal diffs."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from app.knowledge_graph.edges import EdgeManager
from app.knowledge_graph.nodes import NodeManager
from app.knowledge_graph.schemas import (
    KnowledgeEdgeSchema,
    KnowledgeNodeSchema,
    TemporalState,
)


class TemporalMemoryEngine:
    """Provides point-in-time as-of state reconstruction and temporal diff queries."""

    def __init__(self, node_manager: NodeManager, edge_manager: EdgeManager) -> None:
        self.node_manager = node_manager
        self.edge_manager = edge_manager

    def query_as_of(
        self,
        as_of_timestamp: datetime,
        node_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """INVARIANT 23 & 25: Returns knowledge state at timestamp T.

        Historical edges and nodes valid at as_of_timestamp are retrieved.
        """
        all_nodes = self.node_manager.list_nodes(user_id=user_id)
        valid_nodes: List[KnowledgeNodeSchema] = []

        for node in all_nodes:
            # Node must have been created before or at as_of_timestamp
            if node.created_at <= as_of_timestamp:
                valid_nodes.append(node)

        valid_edges: List[KnowledgeEdgeSchema] = []
        for edge in self.edge_manager._edges.values():
            if user_id and edge.user_id != user_id and edge.scope.value == "PRIVATE":
                continue
            if node_id and edge.source_node_id != node_id and edge.target_node_id != node_id:
                continue

            # Check validity window
            v_from = edge.valid_from or edge.created_at
            v_until = edge.valid_until

            if v_from <= as_of_timestamp and (v_until is None or v_until >= as_of_timestamp):
                valid_edges.append(edge)

        return {
            "as_of": as_of_timestamp.isoformat(),
            "nodes_count": len(valid_nodes),
            "edges_count": len(valid_edges),
            "nodes": [n.model_dump() for n in valid_nodes],
            "edges": [e.model_dump() for e in valid_edges],
        }

    def compute_temporal_diff(
        self,
        project_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> Dict[str, Any]:
        """INVARIANT 24 & 172: What changed about this project between start_time and end_time?"""
        added_edges: List[Dict[str, Any]] = []
        expired_edges: List[Dict[str, Any]] = []

        for edge in self.edge_manager._edges.values():
            if edge.project_id == project_id:
                # Added in window
                v_from = edge.valid_from or edge.created_at
                if start_time <= v_from <= end_time:
                    added_edges.append(edge.model_dump())
                # Expired in window
                if edge.valid_until and start_time <= edge.valid_until <= end_time:
                    expired_edges.append(edge.model_dump())

        return {
            "project_id": project_id,
            "window_start": start_time.isoformat(),
            "window_end": end_time.isoformat(),
            "added_relationships": added_edges,
            "expired_relationships": expired_edges,
        }

    def determine_temporal_state(self, edge: KnowledgeEdgeSchema, now: Optional[datetime] = None) -> TemporalState:
        """INVARIANT 167: Clearly labels CURRENT, HISTORICAL, INFERRED, UNKNOWN."""
        check_time = now or datetime.now(UTC)
        if edge.confidence < 0.7:
            return TemporalState.INFERRED
        if edge.valid_until and edge.valid_until < check_time:
            return TemporalState.HISTORICAL
        if (edge.valid_from is None or edge.valid_from <= check_time) and (edge.valid_until is None or edge.valid_until >= check_time):
            return TemporalState.CURRENT
        return TemporalState.UNKNOWN
