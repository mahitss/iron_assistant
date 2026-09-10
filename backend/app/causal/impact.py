"""Impact and blast-radius analysis distinguishing architectural reachability from verified causal impact (Task 55)."""

from __future__ import annotations

from collections import deque
from typing import Any

from app.causal.schemas import CausalGraph


class CausalImpactEngine:
    """Calculates blast radius and estimated causal effects, strictly separating topological reachability from causation."""

    @staticmethod
    def calculate_blast_radius(
        origin_service: str,
        service_graph: dict[str, list[str]],
        causal_graph: CausalGraph | None = None,
    ) -> dict[str, Any]:
        """Prompt #61, #62: Architectural blast radius != verified causation.

        Reachability in the service graph defines potential impact, but requires causal verification.
        """
        # Breadth-first traversal of downstream callers
        downstream_reachable = set()
        queue = deque([origin_service])
        visited = set()

        while queue:
            curr = queue.popleft()
            if curr in visited:
                continue
            visited.add(curr)

            # Find all services that depend on curr
            for caller, callees in service_graph.items():
                if curr in callees and caller not in visited:
                    downstream_reachable.add(caller)
                    queue.append(caller)

        # Separate verified causal impacts if causal_graph is provided
        verified_effects = []
        if causal_graph:
            for edge in causal_graph.edges.values():
                if edge.cause.startswith(origin_service) and edge.status.value in ("ACTIVE", "VERIFIED"):
                    verified_effects.append(edge.effect)

        return {
            "origin_service": origin_service,
            "architectural_blast_radius": sorted(list(downstream_reachable)),
            "blast_radius_count": len(downstream_reachable),
            "verified_causal_impacts": verified_effects,
            "disclaimer": (
                "Architectural blast radius indicates potential reachability in topology. "
                "It does NOT prove that upstream failure caused downstream symptoms without empirical evidence (Prompt #62)."
            ),
        }

    @staticmethod
    def estimate_effect_size(
        metric_name: str,
        baseline_value: float,
        post_event_value: float,
    ) -> dict[str, Any]:
        """Prompt #180, #181: Estimate causal effect size with uncertainty interval."""
        delta = post_event_value - baseline_value
        pct_change = (delta / baseline_value * 100.0) if baseline_value != 0 else 0.0

        # Heuristic 95% uncertainty interval (+- 10% around delta for uncalibrated models)
        interval = (round(delta * 0.9, 2), round(delta * 1.1, 2)) if delta >= 0 else (round(delta * 1.1, 2), round(delta * 0.9, 2))

        return {
            "metric": metric_name,
            "baseline": baseline_value,
            "post_event": post_event_value,
            "delta": round(delta, 2),
            "percentage_change": round(pct_change, 2),
            "estimated_uncertainty_interval": interval,
            "is_calibrated": False,
        }
