"""Dependency integration with Digital Twin and Knowledge Graph topologies (Task 55)."""

from __future__ import annotations

from typing import Any

from app.causal.schemas import CausalRelationshipType


class CausalDependencyIntegrator:
    """Bridges Digital Twin and Knowledge Graph dependencies without conflating dependency with causation."""

    @staticmethod
    def map_dependency_to_candidate_edge(
        source_service: str,
        target_service: str,
        has_empirical_mechanism: bool = False,
    ) -> tuple[str, str, CausalRelationshipType, str]:
        """Prompt #9, #10, #62: Dependency alone does not establish direct causation.

        If no empirical mechanism is observed, relation remains DEPENDS_ON, not CAUSES.
        """
        if has_empirical_mechanism:
            rel = CausalRelationshipType.CONTRIBUTES_TO
            rationale = "Empirical mechanism observed alongside architectural dependency."
        else:
            rel = CausalRelationshipType.DEPENDS_ON
            rationale = "Architectural dependency detected in topology; direct causation unproven without evidence."

        return source_service, target_service, rel, rationale

    @staticmethod
    def extract_candidates_from_digital_twin(
        service_graph: dict[str, list[str]],
        active_incident_service: str,
    ) -> list[dict[str, Any]]:
        """Extract upstream and downstream candidates for an active incident."""
        candidates = []
        # Upstream dependencies (services the incident service calls)
        upstream = service_graph.get(active_incident_service, [])
        for up in upstream:
            candidates.append({
                "candidate": up,
                "direction": "upstream",
                "relationship": CausalRelationshipType.DEPENDS_ON.value,
                "is_causal_hypothesis": True,
                "rationale": f"Service '{active_incident_service}' depends on '{up}' according to Digital Twin topology.",
            })

        # Downstream callers (services calling the incident service)
        for caller, callee_list in service_graph.items():
            if active_incident_service in callee_list:
                candidates.append({
                    "candidate": caller,
                    "direction": "downstream",
                    "relationship": CausalRelationshipType.DEPENDS_ON.value,
                    "is_causal_hypothesis": False,
                    "rationale": f"Service '{caller}' depends downstream on '{active_incident_service}'.",
                })

        return candidates
