"""Causal Graph analytical engine, path traversal, and confounder/collider detection (Task 55, Prompts #2, #49-#57)."""

from __future__ import annotations

import uuid
from collections import defaultdict, deque
from typing import Any

from app.causal.relationships import compose_path_confidence
from app.causal.schemas import (
    CausalEdge,
    CausalEdgeStatus,
    CausalGraph,
    CausalNode,
    CausalScope,
)
from app.causal.temporal import utc_now


class CausalGraphEngine:
    """Manages the in-memory causal graph, versioning, path traversal, and confounding detection."""

    @staticmethod
    def create_graph(
        scope: CausalScope = CausalScope.SYSTEM,
        scope_id: str | None = None,
        graph_id: str | None = None,
    ) -> CausalGraph:
        now = utc_now()
        gid = graph_id or f"cgr_{scope.value.lower()}_{uuid.uuid4().hex[:8]}"
        return CausalGraph(
            graph_id=gid,
            scope=scope,
            scope_id=scope_id,
            version=1,
            timestamp=now,
            nodes={},
            edges={},
            confidence=1.0,
            provenance={"initialized_at": now.isoformat(), "scope": scope.value},
        )

    @staticmethod
    def upsert_node(graph: CausalGraph, node: CausalNode) -> CausalGraph:
        graph.nodes[node.node_id] = node
        graph.version += 1
        graph.timestamp = utc_now()
        return graph

    @staticmethod
    def upsert_edge(graph: CausalGraph, edge: CausalEdge) -> CausalGraph:
        graph.edges[edge.edge_id] = edge
        graph.version += 1
        graph.timestamp = utc_now()
        return graph

    @staticmethod
    def build_adjacency(graph: CausalGraph) -> tuple[dict[str, list[CausalEdge]], dict[str, list[CausalEdge]]]:
        """Returns (outbound_edges_by_cause, inbound_edges_by_effect)."""
        adj_out: dict[str, list[CausalEdge]] = defaultdict(list)
        adj_in: dict[str, list[CausalEdge]] = defaultdict(list)
        for edge in graph.edges.values():
            if edge.status == CausalEdgeStatus.ACTIVE:
                adj_out[edge.cause].append(edge)
                adj_in[edge.effect].append(edge)
        return adj_out, adj_in

    @staticmethod
    def find_causal_paths(
        graph: CausalGraph,
        cause_id: str,
        effect_id: str,
        max_depth: int = 4,
    ) -> list[dict[str, Any]]:
        """Prompt #55, #56, #57: Traverses causal paths between cause and effect, calculating weakest-link confidence."""
        adj_out, _ = CausalGraphEngine.build_adjacency(graph)
        paths: list[dict[str, Any]] = []

        # Queue contains: (current_node, [edges_taken], visited_set)
        queue: deque[tuple[str, list[CausalEdge], set[str]]] = deque([(cause_id, [], {cause_id})])

        while queue:
            curr, edge_path, visited = queue.popleft()
            if curr == effect_id and edge_path:
                confidences = [e.confidence for e in edge_path]
                combined_conf = compose_path_confidence(confidences)
                paths.append({
                    "path_nodes": [cause_id] + [e.effect for e in edge_path],
                    "nodes": [cause_id] + [e.effect for e in edge_path],
                    "edges": [e.edge_id for e in edge_path],
                    "combined_confidence": combined_conf,
                    "confidence": combined_conf,
                    "length": len(edge_path),
                })
                continue

            if len(edge_path) >= max_depth:
                continue

            for nxt_edge in adj_out.get(curr, []):
                nxt_node = nxt_edge.effect
                if nxt_node not in visited:
                    queue.append((nxt_node, edge_path + [nxt_edge], visited | {nxt_node}))

        paths.sort(key=lambda p: p["combined_confidence"], reverse=True)
        return paths

    @staticmethod
    def find_common_ancestors(graph: CausalGraph, node_a: str, node_b: str, max_depth: int = 3) -> list[str]:
        """Prompt #49, #50, #51: Detects common upstream causes (confounders)."""
        _, adj_in = CausalGraphEngine.build_adjacency(graph)

        def get_ancestors(start: str) -> set[str]:
            ancestors = set()
            q = deque([(start, 0)])
            while q:
                curr, depth = q.popleft()
                if depth >= max_depth:
                    continue
                for e in adj_in.get(curr, []):
                    if e.cause not in ancestors:
                        ancestors.add(e.cause)
                        q.append((e.cause, depth + 1))
            return ancestors

        anc_a = get_ancestors(node_a)
        anc_b = get_ancestors(node_b)
        return list(anc_a.intersection(anc_b))

    @staticmethod
    def find_common_descendants(graph: CausalGraph, node_a: str, node_b: str, max_depth: int = 3) -> list[str]:
        """Prompt #52: Detects colliders (common effects) to prevent collider bias conditioning."""
        adj_out, _ = CausalGraphEngine.build_adjacency(graph)

        def get_descendants(start: str) -> set[str]:
            desc = set()
            q = deque([(start, 0)])
            while q:
                curr, depth = q.popleft()
                if depth >= max_depth:
                    continue
                for e in adj_out.get(curr, []):
                    if e.effect not in desc:
                        desc.add(e.effect)
                        q.append((e.effect, depth + 1))
            return desc

        desc_a = get_descendants(node_a)
        desc_b = get_descendants(node_b)
        return list(desc_a.intersection(desc_b))

    find_paths = find_causal_paths
    detect_confounders = find_common_ancestors
    detect_colliders = find_common_descendants

