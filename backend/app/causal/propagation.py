"""Causal propagation engine for downstream effect estimation and path traversal (Task 55)."""

from __future__ import annotations

from collections import deque
from typing import Any

from app.causal.schemas import CausalGraph


class CausalPropagationEngine:
    """Estimates downstream effect propagation across causal edges with bounded depth and weakest-link confidence."""

    @staticmethod
    def propagate_downstream(
        start_node: str,
        causal_graph: CausalGraph,
        max_depth: int = 4,
        is_topology_complete: bool = True,
    ) -> dict[str, Any]:
        """Prompt #55, #56, #57, #58, #60: Traverse downstream paths with bounded depth and weakest-link confidence."""
        visited: dict[str, dict[str, Any]] = {}
        queue: deque[tuple[str, int, float, list[str]]] = deque([(start_node, 0, 1.0, [start_node])])

        while queue:
            curr_node, depth, path_confidence, path = queue.popleft()
            if depth >= max_depth:
                continue

            for edge in causal_graph.edges.values():
                if edge.cause == curr_node and edge.status.value in ("ACTIVE", "CANDIDATE"):
                    next_node = edge.effect
                    # Weakest link rule: confidence is bounded by minimum link confidence along path
                    next_confidence = min(path_confidence, edge.confidence)
                    new_path = path + [next_node]

                    if next_node not in visited or visited[next_node]["confidence"] < next_confidence:
                        visited[next_node] = {
                            "node": next_node,
                            "depth": depth + 1,
                            "confidence": round(next_confidence, 3),
                            "path": new_path,
                            "relationship": edge.relationship.value,
                        }
                        queue.append((next_node, depth + 1, next_confidence, new_path))

        propagation_result = {
            "origin": start_node,
            "max_depth": max_depth,
            "downstream_impact_count": len(visited),
            "propagated_nodes": list(visited.values()),
            "is_topology_complete": is_topology_complete,
            "warning": (
                None
                if is_topology_complete
                else "Incomplete topology: downstream propagation may miss unmonitored dependencies (Prompt #60)."
            ),
        }
        return propagation_result
