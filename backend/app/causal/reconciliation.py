"""Causal graph reconciliation, versioning, graph diffing, and drift detection (Task 55)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.causal.schemas import (
    CausalEdgeStatus,
    CausalEvidence,
    CausalGraph,
)


class CausalReconciliationEngine:
    """Handles causal graph versioning, diffing between states, contradiction reconciliation, and drift detection."""

    @staticmethod
    def diff_graphs(graph_a: CausalGraph, graph_b: CausalGraph) -> dict[str, Any]:
        """Prompt #196, #197: Compute structural and confidence differences between two causal graphs."""
        nodes_a = set(graph_a.nodes.keys())
        nodes_b = set(graph_b.nodes.keys())

        edges_a = set(graph_a.edges.keys())
        edges_b = set(graph_b.edges.keys())

        added_nodes = list(nodes_b - nodes_a)
        removed_nodes = list(nodes_a - nodes_b)

        added_edges = list(edges_b - edges_a)
        removed_edges = list(edges_a - edges_b)

        modified_edges = []
        for eid in edges_a.intersection(edges_b):
            edge1 = graph_a.edges[eid]
            edge2 = graph_b.edges[eid]
            if edge1.status != edge2.status or abs(edge1.confidence - edge2.confidence) > 0.01:
                modified_edges.append({
                    "edge_id": eid,
                    "status_before": edge1.status.value,
                    "status_after": edge2.status.value,
                    "confidence_before": edge1.confidence,
                    "confidence_after": edge2.confidence,
                })

        return {
            "graph_a_id": graph_a.graph_id,
            "graph_b_id": graph_b.graph_id,
            "version_a": graph_a.version,
            "version_b": graph_b.version,
            "added_nodes": added_nodes,
            "removed_nodes": removed_nodes,
            "added_edges": added_edges,
            "removed_edges": removed_edges,
            "modified_edges": modified_edges,
        }

    @staticmethod
    def reconcile_edge_with_evidence(
        graph: CausalGraph,
        edge_id: str,
        evidence: CausalEvidence,
        contradicts: bool = False,
    ) -> CausalGraph:
        """Prompt #97, #98, #198, #199: Update edge status and confidence based on new evidence.

        Conflicting evidence is preserved in graph provenance so it remains visible.
        """
        if edge_id not in graph.edges:
            return graph

        edge = graph.edges[edge_id]
        edge.evidence_refs.append(evidence.evidence_id)

        if contradicts:
            # Weaken or reject edge
            edge.confidence = max(0.0, round(edge.confidence - 0.35, 3))
            if edge.confidence <= 0.2:
                edge.status = CausalEdgeStatus.REJECTED
            else:
                edge.status = CausalEdgeStatus.WEAKENED

            # Prompt #199: Record visible conflict
            conflicts = graph.provenance.setdefault("conflicts", [])
            conflicts.append({
                "edge_id": edge_id,
                "contradictory_evidence_id": evidence.evidence_id,
                "reason": "New empirical observation contradicts expected causal correlation.",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            })
        else:
            edge.confidence = min(1.0, round(edge.confidence + 0.15, 3))
            if edge.status == CausalEdgeStatus.CANDIDATE and edge.confidence >= 0.7:
                edge.status = CausalEdgeStatus.ACTIVE

        graph.version += 1
        graph.timestamp = datetime.now(timezone.utc)
        return graph

    @staticmethod
    def detect_causal_drift(
        graph: CausalGraph,
        recent_events: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Prompt #93, #200: Detect when a historical causal relationship stops predicting outcomes."""
        drift_alerts = []
        for edge in graph.edges.values():
            if edge.status == CausalEdgeStatus.ACTIVE:
                # Check if cause happened without effect in recent events
                cause_occurred = any(e.get("node") == edge.cause for e in recent_events)
                effect_occurred = any(e.get("node") == edge.effect for e in recent_events)

                if cause_occurred and not effect_occurred:
                    drift_alerts.append({
                        "edge_id": edge.edge_id,
                        "cause": edge.cause,
                        "effect": edge.effect,
                        "drift_type": "DISSOCIATION",
                        "description": (
                            f"Cause '{edge.cause}' observed in recent timeline without expected "
                            f"effect '{edge.effect}', suggesting causal drift or changed mechanism."
                        ),
                    })

        return drift_alerts
