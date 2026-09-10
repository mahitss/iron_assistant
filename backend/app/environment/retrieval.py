"""Selective Context Retrieval and Prompt Token Budgeting (Task 54, Prompts #175-#180)."""

from __future__ import annotations

from typing import Any

from app.environment.schemas import DigitalTwin
from app.environment.topology import TopologyGraph


class ContextRetrievalManager:
    """Selectively extracts task-relevant digital twin subgraphs for LLM prompt context."""

    @staticmethod
    def extract_relevant_context(
        twin: DigitalTwin,
        task_query: str,
        focus_node_ids: list[str] | None = None,
        max_nodes: int = 15,
        max_hops: int = 2,
    ) -> dict[str, Any]:
        """Prompt #175, #176, #180: Extracts ranked, bounded topology slice without flooding context."""
        topology = TopologyGraph(twin.nodes, twin.edges)
        relevant_node_ids: set[str] = set()

        if focus_node_ids:
            for fid in focus_node_ids:
                if fid in twin.nodes:
                    trav = topology.bounded_traversal(
                        start_node_id=fid,
                        direction="both",
                        max_depth=max_hops,
                        max_nodes=max_nodes,
                    )
                    relevant_node_ids.update(trav["visited_node_ids"])

        # If no explicit focus nodes, rank by keyword match with task_query
        if not relevant_node_ids:
            keywords = [k.lower() for k in task_query.split() if len(k) > 2]
            scored_nodes = []
            for n in twin.nodes.values():
                score = 0
                searchable = f"{n.display_name} {n.canonical_id} {n.node_type.value}".lower()
                for kw in keywords:
                    if kw in searchable:
                        score += 1
                if score > 0:
                    scored_nodes.append((score, n.node_id))
            scored_nodes.sort(key=lambda x: x[0], reverse=True)
            for _, nid in scored_nodes[:max_nodes]:
                relevant_node_ids.add(nid)

        selected_nodes = [twin.nodes[nid].model_dump() for nid in relevant_node_ids if nid in twin.nodes]
        selected_edges = [
            e.model_dump() for e in twin.edges.values()
            if e.source in relevant_node_ids and e.target in relevant_node_ids
        ]

        return {
            "query": task_query,
            "total_nodes_in_twin": len(twin.nodes),
            "selected_node_count": len(selected_nodes),
            "nodes": selected_nodes,
            "edges": selected_edges,
            "context_budget_applied": True,
        }
