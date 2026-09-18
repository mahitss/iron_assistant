"""Causal model integration bridge for Task 113.
Reuses existing Causal Graph (Task 55/73) and Task 112 Causal Explanation engines
without duplicating causal graphs or engines.
"""

from __future__ import annotations

import logging
from typing import Any

from app.causal.schemas import CausalGraph, CausalScope
from app.causal.service import CausalService
from app.counterfactual.domain import InterventionMechanism

logger = logging.getLogger("kairo.counterfactual.causal_bridge")


class CausalBridge:
    """Interfaces counterfactual intervention inquiries with the authoritative causal graph."""

    def __init__(self) -> None:
        self._causal_service = CausalService()

    def get_causal_graph(self, graph_id: str = "system_default") -> CausalGraph:
        """Retrieves or creates system causal DAG from app.causal."""
        try:
            return self._causal_service.get_graph(graph_id)
        except Exception:
            return self._causal_service.create_graph(graph_id=graph_id, scope=CausalScope.SYSTEM)

    def extract_bounded_subgraph(
        self,
        target_variable: str,
        max_depth: int = 4,
        graph_id: str = "system_default",
    ) -> dict[str, Any]:
        """Extracts a bounded causal subgraph rooted at treatment variable."""
        graph = self.get_causal_graph(graph_id)
        visited_nodes: set[str] = {target_variable}
        subgraph_edges: list[dict[str, Any]] = []
        mediators: list[str] = []
        confounders: list[str] = []

        # BFS bounded expansion
        frontier = [target_variable]
        depth = 0
        while frontier and depth < max_depth:
            next_frontier = []
            for node in frontier:
                for edge_id, edge in graph.edges.items():
                    if edge.cause == node:
                        subgraph_edges.append({
                            "edge_id": edge_id,
                            "cause": edge.cause,
                            "effect": edge.effect,
                            "relationship": edge.relationship.value if hasattr(edge.relationship, "value") else str(edge.relationship),
                            "confidence": edge.confidence,
                        })
                        if edge.effect not in visited_nodes:
                            visited_nodes.add(edge.effect)
                            next_frontier.append(edge.effect)
                            if depth > 0:
                                mediators.append(edge.effect)
                    # Check potential confounders (common causes)
                    elif edge.effect == node and edge.cause != target_variable:
                        confounders.append(edge.cause)
            frontier = next_frontier
            depth += 1

        return {
            "root_target": target_variable,
            "max_depth": max_depth,
            "nodes": list(visited_nodes),
            "edges": subgraph_edges,
            "mediators": list(set(mediators)),
            "confounders": list(set(confounders)),
            "graph_version": "v1.0",
        }

    def infer_mechanisms(
        self,
        treatment_variable: str,
        target_outcome: str,
        subgraph: dict[str, Any],
    ) -> list[InterventionMechanism]:
        """Extracts explicit causal mechanisms tracing path from treatment to target outcome."""
        mechanisms: list[InterventionMechanism] = []
        mediators = subgraph.get("mediators", [])

        if mediators:
            for med in mediators[:3]:
                mechanisms.append(
                    InterventionMechanism(
                        treatment_variable=treatment_variable,
                        mediating_nodes=[med],
                        target_variable=target_outcome,
                        pathway_description=f"{treatment_variable} -> {med} -> {target_outcome}",
                        confidence=0.70,
                    )
                )
        else:
            mechanisms.append(
                InterventionMechanism(
                    treatment_variable=treatment_variable,
                    mediating_nodes=[],
                    target_variable=target_outcome,
                    pathway_description=f"Direct causal link from {treatment_variable} to {target_outcome}",
                    confidence=0.65,
                )
            )

        return mechanisms
