"""Topology Graph analysis, bounded traversal, cycle detection, and SPoF identification (Task 54)."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from app.environment.schemas import EnvironmentEdge, EnvironmentNode


class TopologyGraph:
    """In-memory graph representation of digital twin topology with analytical capabilities."""

    def __init__(self, nodes: dict[str, EnvironmentNode], edges: dict[str, EnvironmentEdge]) -> None:
        self.nodes = nodes
        self.edges = edges
        self.adj_out: dict[str, list[str]] = defaultdict(list)
        self.adj_in: dict[str, list[str]] = defaultdict(list)
        self._build_index()

    def _build_index(self) -> None:
        for edge in self.edges.values():
            if edge.status == "ACTIVE":
                self.adj_out[edge.source].append(edge.target)
                self.adj_in[edge.target].append(edge.source)

    def get_upstream_dependencies(self, node_id: str) -> list[str]:
        """Prompt #156: 'What does service X depend on?' (Outgoing target nodes)."""
        return list(set(self.adj_out.get(node_id, [])))

    def get_downstream_dependents(self, node_id: str) -> list[str]:
        """Prompt #155: 'What depends on service X?' (Incoming source nodes)."""
        return list(set(self.adj_in.get(node_id, [])))

    def bounded_traversal(
        self,
        start_node_id: str,
        direction: str = "both",  # "outgoing", "incoming", or "both"
        max_depth: int = 3,
        max_nodes: int = 50,
    ) -> dict[str, Any]:
        """Performs bounded BFS to prevent graph explosion (Prompt #176-#179)."""
        visited: set[str] = {start_node_id}
        traversed_edges: list[dict[str, str]] = []
        queue: deque[tuple[str, int]] = deque([(start_node_id, 0)])

        while queue and len(visited) < max_nodes:
            curr, depth = queue.popleft()
            if depth >= max_depth:
                continue

            neighbors = []
            if direction in ("outgoing", "both"):
                for tgt in self.adj_out.get(curr, []):
                    neighbors.append((tgt, curr, tgt))
            if direction in ("incoming", "both"):
                for src in self.adj_in.get(curr, []):
                    neighbors.append((src, src, curr))

            for nxt, s, t in neighbors:
                if len(visited) >= max_nodes:
                    break
                traversed_edges.append({"source": s, "target": t})
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append((nxt, depth + 1))

        return {
            "root": start_node_id,
            "total_visited": len(visited),
            "visited_node_ids": list(visited),
            "traversed_edges": traversed_edges,
            "truncated": len(visited) >= max_nodes,
        }

    def find_dependency_cycles(self) -> list[list[str]]:
        """Prompt #48: Detects circular dependencies in the topology."""
        cycles = []
        visited = set()
        rec_stack = set()
        path = []

        def dfs(u: str) -> None:
            visited.add(u)
            rec_stack.add(u)
            path.append(u)

            for v in self.adj_out.get(u, []):
                if v not in visited:
                    dfs(v)
                elif v in rec_stack:
                    idx = path.index(v)
                    cycle = path[idx:] + [v]
                    cycles.append(cycle)

            rec_stack.remove(u)
            path.pop()

        for node_id in self.nodes:
            if node_id not in visited:
                dfs(node_id)

        return cycles

    def identify_critical_dependencies(self, min_dependents: int = 2) -> list[dict[str, Any]]:
        """Prompt #49: High-impact dependencies with numerous inbound dependents."""
        critical = []
        for node_id, inbound in self.adj_in.items():
            if len(inbound) >= min_dependents:
                node = self.nodes.get(node_id)
                critical.append({
                    "node_id": node_id,
                    "display_name": node.display_name if node else node_id,
                    "dependent_count": len(inbound),
                    "dependents": inbound,
                })
        critical.sort(key=lambda x: x["dependent_count"], reverse=True)
        return critical

    def find_single_points_of_failure(self) -> list[dict[str, Any]]:
        """Prompt #50: Detects potential SPoFs where nodes lack redundant paths."""
        spofs = []
        critical = self.identify_critical_dependencies(min_dependents=2)
        for item in critical:
            node_id = item["node_id"]
            # A node is a SPoF if multiple services depend on it directly and it is not a load balancer or cluster
            node = self.nodes.get(node_id)
            node_type = node.node_type.value if node else "UNKNOWN"
            if node_type not in ("LOAD_BALANCER", "CLUSTER"):
                spofs.append({
                    "node_id": node_id,
                    "node_type": node_type,
                    "display_name": item["display_name"],
                    "risk_reason": f"Single non-redundant dependency for {item['dependent_count']} downstream services.",
                    "dependents": item["dependents"],
                })
        return spofs
