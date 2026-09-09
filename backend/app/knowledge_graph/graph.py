"""Graph representation, bounded traversal, cycle handling, and as-of time slicing."""

from __future__ import annotations

from collections import deque
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from app.knowledge_graph.edges import EdgeManager
from app.knowledge_graph.nodes import NodeManager
from app.knowledge_graph.schemas import (
    GraphQueryResultSchema,
    KnowledgeEdgeSchema,
    KnowledgeNodeSchema,
    ScopeType,
)


class KnowledgeGraph:
    """Core in-memory and indexed graph managing nodes, edges, bounded traversals, and path queries."""

    def __init__(self, node_manager: Optional[NodeManager] = None, edge_manager: Optional[EdgeManager] = None) -> None:
        self.nodes = node_manager or NodeManager()
        self.edges = edge_manager or EdgeManager(self.nodes)

    def traverse(
        self,
        start_node_id: str,
        max_depth: int = 2,
        max_nodes: int = 100,
        user_id: Optional[str] = None,
        as_of: Optional[datetime] = None,
    ) -> GraphQueryResultSchema:
        """Performs bounded N-hop traversal with cycle protection (INVARIANTS 88, 89, 176, 177)."""
        start_node = self.nodes.get_node(start_node_id)
        if not start_node or start_node.status != "ACTIVE":
            return GraphQueryResultSchema(total_nodes_visited=0)

        visited_nodes: Set[str] = {start_node_id}
        collected_nodes: List[KnowledgeNodeSchema] = [start_node]
        collected_edges: List[KnowledgeEdgeSchema] = []
        visited_edges: Set[str] = set()

        # Queue contains (node_id, current_depth)
        queue: deque[Tuple[str, int]] = deque([(start_node_id, 0)])

        while queue and len(visited_nodes) < max_nodes:
            current_id, depth = queue.popleft()
            if depth >= max_depth:
                continue

            # Look up outgoing and incoming edges
            outgoing = self.edges.get_outgoing_edges(current_id)
            incoming = self.edges.get_incoming_edges(current_id)

            for edge in outgoing + incoming:
                # 1. Temporal validation at as_of time
                if as_of:
                    if edge.valid_from and edge.valid_from > as_of:
                        continue
                    if edge.valid_until and edge.valid_until < as_of:
                        continue

                # 2. User boundary check
                if user_id and edge.user_id != user_id and edge.scope == ScopeType.PRIVATE:
                    continue

                if edge.edge_id not in visited_edges:
                    visited_edges.add(edge.edge_id)
                    collected_edges.append(edge)

                next_node_id = edge.target_node_id if edge.source_node_id == current_id else edge.source_node_id
                if next_node_id not in visited_nodes:
                    visited_nodes.add(next_node_id)
                    next_node = self.nodes.get_node(next_node_id)
                    if next_node and next_node.status == "ACTIVE":
                        collected_nodes.append(next_node)
                        queue.append((next_node_id, depth + 1))

        return GraphQueryResultSchema(
            nodes=collected_nodes,
            edges=collected_edges,
            traversal_depth=max_depth,
            total_nodes_visited=len(visited_nodes),
            path_confidence=1.0,
        )

    def find_path(
        self,
        source_node_id: str,
        target_node_id: str,
        max_depth: int = 4,
        max_nodes: int = 150,
    ) -> Optional[GraphQueryResultSchema]:
        """Finds relationship path between two nodes (INVARIANT 173 & 174)."""
        if source_node_id == target_node_id:
            src = self.nodes.get_node(source_node_id)
            return GraphQueryResultSchema(nodes=[src] if src else [], edges=[])

        # BFS queue: (current_node_id, path_nodes, path_edges)
        queue: deque[Tuple[str, List[str], List[KnowledgeEdgeSchema]]] = deque([(source_node_id, [source_node_id], [])])
        visited: Set[str] = {source_node_id}

        while queue and len(visited) < max_nodes:
            curr_id, path_node_ids, path_edges = queue.popleft()
            if len(path_node_ids) > max_depth + 1:
                continue

            for edge in self.edges.get_outgoing_edges(curr_id):
                next_id = edge.target_node_id
                if next_id == target_node_id:
                    final_node_ids = path_node_ids + [next_id]
                    final_edges = path_edges + [edge]
                    nodes = [self.nodes.get_node(nid) for nid in final_node_ids if self.nodes.get_node(nid)]
                    explanations = [
                        f"{e.source_node_id} --[{e.relationship.value}]--> {e.target_node_id}"
                        for e in final_edges
                    ]
                    # Calculate aggregate path confidence (product of edge confidences)
                    path_conf = 1.0
                    for e in final_edges:
                        path_conf *= e.confidence
                    return GraphQueryResultSchema(
                        nodes=nodes,
                        edges=final_edges,
                        explanations=explanations,
                        path_confidence=round(path_conf, 3),
                        traversal_depth=len(final_edges),
                        total_nodes_visited=len(visited),
                    )

                if next_id not in visited:
                    visited.add(next_id)
                    queue.append((next_id, path_node_ids + [next_id], path_edges + [edge]))

        return None
