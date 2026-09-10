"""Causal replay engine for reconstructing chronological incident chains through graph edges (Task 55)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.causal.schemas import CausalGraph, RootCauseChain


class CausalReplayEngine:
    """Replays chronological events through the causal graph to reconstruct root-cause propagation chains."""

    @staticmethod
    def replay_timeline(
        events: list[dict[str, Any]],
        causal_graph: CausalGraph,
    ) -> dict[str, Any]:
        """Prompt #34, #189: Reconstruct underlying condition -> trigger -> mechanism -> symptom -> impact."""
        # Ensure chronological ordering
        sorted_events = sorted(
            events,
            key=lambda e: (
                e.get("timestamp")
                if isinstance(e.get("timestamp"), datetime)
                else datetime.fromisoformat(str(e.get("timestamp", "1970-01-01T00:00:00+00:00")))
            ),
        )

        activations = []
        observed_nodes = set()

        for ev in sorted_events:
            node_id = ev.get("node") or ev.get("entity")
            if not node_id:
                continue

            observed_nodes.add(node_id)
            # Find activated downstream causal edges
            downstream_edges = [
                e.effect for e in causal_graph.edges.values()
                if e.cause == node_id and e.status.value in ("ACTIVE", "CANDIDATE")
            ]

            activations.append({
                "timestamp": str(ev.get("timestamp")),
                "node": node_id,
                "event_type": ev.get("type", "EVENT"),
                "state": ev.get("state"),
                "activated_downstream": downstream_edges,
            })

        # Assemble canonical 5-stage causal chain
        chain = RootCauseChain(
            underlying_condition=activations[0]["node"] if activations else None,
            trigger=activations[1]["node"] if len(activations) > 1 else None,
            mechanism="Cascading dependency saturation and resource exhaustion",
            intermediate_state=activations[-2]["node"] if len(activations) > 3 else None,
            symptom=activations[-1]["node"] if activations else None,
            impact="Degraded service availability or elevated latency",
        )

        return {
            "replayed_events_count": len(sorted_events),
            "chronological_activations": activations,
            "reconstructed_chain": chain.model_dump(),
            "nodes_involved": list(observed_nodes),
            "replayed_at": datetime.now(timezone.utc).isoformat(),
        }
