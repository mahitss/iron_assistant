"""What-If Hypothetical Simulation and Blast Radius Exploration (Task 54, Prompts #210-#217)."""

from __future__ import annotations

import uuid

from app.environment.schemas import ImpactLevel, WhatIfSimulationResult
from app.environment.temporal import utc_now
from app.environment.topology import TopologyGraph


class WhatIfSimulator:
    """Executes non-destructive hypothetical simulations over the Digital Twin topology."""

    @staticmethod
    def simulate_node_failure(
        target_node_id: str,
        topology: TopologyGraph,
        hypothetical_event: str = "service_outage",
    ) -> WhatIfSimulationResult:
        """Prompt #212, #213, #215: 'What happens if service X goes down?' Clearly labeled hypothetical."""
        downstream = topology.bounded_traversal(
            start_node_id=target_node_id,
            direction="incoming",  # downstream callers/dependents
            max_depth=4,
            max_nodes=50,
        )

        affected = [nid for nid in downstream["visited_node_ids"] if nid != target_node_id]
        uncertainties = []

        if downstream["truncated"]:
            uncertainties.append("Graph traversal truncated at limit (50 nodes). Incomplete blast radius.")

        # Check if target has unmapped dependencies
        target_node = topology.nodes.get(target_node_id)
        if not target_node or not target_node.metadata.get("endpoints"):
            uncertainties.append("Target service has missing or unverified endpoint telemetry.")

        blast_score = round(min(1.0, len(affected) / 10.0), 2)
        if len(affected) >= 5 or blast_score >= 0.5:
            impact = ImpactLevel.HIGH
        elif len(affected) >= 1 or blast_score >= 0.1:
            impact = ImpactLevel.MEDIUM
        else:
            impact = ImpactLevel.LOW

        sim_id = f"sim_{uuid.uuid4().hex[:10]}"
        return WhatIfSimulationResult(
            simulation_id=sim_id,
            target_node=target_node_id,
            hypothetical_event=hypothetical_event,
            affected_nodes=affected,
            blast_radius_score=blast_score,
            potential_impact=impact,
            uncertainties=uncertainties,
            is_hypothetical=True,  # Prompt #213: clearly labeled hypothetical
            simulated_at=utc_now(),
        )
