"""Controlled forgetting, scope-based deletion, index propagation, and privacy audits (INVARIANTS 106-110, 240)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
import uuid

from app.knowledge_graph.graph import KnowledgeGraph


class ForgettingEngine:
    """Manages user-directed forgetting with index cleanup and privacy-preserving audit logs."""

    def __init__(self, graph: KnowledgeGraph) -> None:
        self.graph = graph
        # audit records: deletion_id -> audit record
        self._forget_audit_log: List[Dict[str, Any]] = []

    def forget_entity(
        self,
        node_id: str,
        user_id: str,
        reason: str = "user_request",
    ) -> Dict[str, Any]:
        """INVARIANT 107 & 108: Deletes an entity node and propagates deletion to connected edges and indexes."""
        node = self.graph.nodes.get_node(node_id)
        if not node:
            raise ValueError(f"Entity '{node_id}' not found.")

        # Verify authorization
        if node.user_id != user_id:
            raise PermissionError("Cannot delete an entity belonging to another user.")

        # INVARIANT 109: Forget propagation: remove connected edges
        out_edges = self.graph.edges.get_outgoing_edges(node_id)
        in_edges = self.graph.edges.get_incoming_edges(node_id)
        deleted_edge_count = len(out_edges) + len(in_edges)

        for e in out_edges + in_edges:
            self.graph.edges.delete_edge(e.edge_id)

        # Delete node from graph and alias index
        self.graph.nodes.delete_node(node_id)

        # INVARIANT 110: Record deletion occurred without retaining sensitive content
        record = {
            "deletion_id": str(uuid.uuid4()),
            "action": "FORGET_ENTITY",
            "target_node_id": node_id,
            "target_type": node.node_type.value,
            "deleted_edges_count": deleted_edge_count,
            "reason": reason,
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
        }
        self._forget_audit_log.append(record)

        return record

    def forget_project_memory(self, project_id: str, user_id: str) -> Dict[str, Any]:
        """Deletes all nodes and edges scoped to a given project."""
        nodes_to_delete = [
            n.node_id for n in self.graph.nodes.list_nodes(project_id=project_id, user_id=user_id)
        ]
        for nid in nodes_to_delete:
            self.forget_entity(nid, user_id=user_id, reason="project_purge")

        return {
            "action": "FORGET_PROJECT_MEMORY",
            "project_id": project_id,
            "deleted_nodes_count": len(nodes_to_delete),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def get_forget_audit(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if user_id:
            return [r for r in self._forget_audit_log if r.get("user_id") == user_id]
        return list(self._forget_audit_log)
