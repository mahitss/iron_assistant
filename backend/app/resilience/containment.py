"""Autonomous Containment Engine (Task 76).

Explicitly distinguishes:
CONTAINMENT: Stopping the problem from spreading.
RECOVERY: Restoring healthy operation.

Given a potential cascade A -> B -> C -> D, identifies and evaluates
all candidate containment barriers, scoring containment strength, collateral impact,
reversibility, and required permissions. Note: the optimal containment point is
NOT necessarily the earliest node (e.g. earliest node might cause massive collateral
outage whereas an intermediate bulkhead protects downstream without breaking critical upstream).
"""

from typing import Any

from app.resilience.defense_schemas import (
    ContainmentPoint,
    generate_defense_id,
)


class ContainmentEngine:
    """Evaluates, ranks, and coordinates containment interventions along cascade trajectories."""

    def __init__(self) -> None:
        pass

    def evaluate_containment_points(
        self,
        cascade_path: list[str],
        topology: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> list[ContainmentPoint]:
        """Evaluates every node along the cascade trajectory as a candidate containment barrier."""
        context = context or {}
        nodes = topology.get("nodes", {})
        edges = topology.get("edges", [])
        containment_points: list[ContainmentPoint] = []

        path_length = len(cascade_path)
        if path_length == 0:
            return containment_points

        for idx, entity_id in enumerate(cascade_path):
            node_meta = nodes.get(entity_id, {})
            criticality = node_meta.get("criticality", 0.5)
            supports_isolation = node_meta.get("isolation_supported", True)
            has_circuit_breaker = node_meta.get("has_circuit_breaker", True)
            downstream_count = path_length - 1 - idx

            # Collateral impact evaluation:
            # Isolating root/earliest node might shut down everything, causing HIGH collateral impact.
            # Isolating a leaf might have LOW collateral impact but late containment.
            # Intermediate nodes with alternative routes have optimal profile.
            collateral_impact = "LOW"
            if idx == 0 and criticality >= 0.8:
                collateral_impact = "HIGH"
            elif criticality >= 0.6 and downstream_count > 2:
                collateral_impact = "MEDIUM"

            # Expected containment strength:
            # Circuit breaker or explicit isolation mechanism grants 0.85-0.95 strength.
            # Lack of isolation mechanism reduces containment strength.
            base_strength = 0.9 if has_circuit_breaker or supports_isolation else 0.5
            # Decay strength slightly if node has unmonitored lateral connections
            lateral_edges = [
                e for e in edges
                if (e.get("source") == entity_id or e.get("from") == entity_id)
                and (e.get("target") not in cascade_path and e.get("to") not in cascade_path)
            ]
            lateral_penalty = min(0.3, len(lateral_edges) * 0.1)
            containment_strength = max(0.1, min(1.0, base_strength - lateral_penalty))

            # Required permissions
            perms = ["EXECUTE"]
            if collateral_impact in ("MEDIUM", "HIGH") or criticality >= 0.7:
                perms.append("WRITE")
            if idx == 0 and criticality >= 0.9:
                perms.append("DESTRUCTIVE")

            # Determine isolation method
            isolation_method = "CIRCUIT_BREAKER"
            if node_meta.get("queue_supported"):
                isolation_method = "TRAFFIC_SHED"
            elif node_meta.get("rate_limit_supported"):
                isolation_method = "RATE_LIMIT"
            elif supports_isolation:
                isolation_method = "PROCESS_ISOLATION"

            cpt = ContainmentPoint(
                point_id=generate_defense_id("cpt"),
                entity_id=entity_id,
                sequence_idx=idx,
                affected_scope=node_meta.get("scope", "SERVICE"),
                expected_containment_strength=round(containment_strength, 2),
                reversibility=True,
                collateral_impact=collateral_impact,
                required_permissions=perms,
                resource_requirements={"cpu_cores": 0.1, "memory_mb": 64},
                confidence=0.85,
                isolation_method=isolation_method,
            )
            containment_points.append(cpt)

        # Rank containment points:
        # Score = (Containment Strength * 0.45) + (Reversibility * 0.2) + (Low Collateral Bonus * 0.35)
        def score_point(p: ContainmentPoint) -> float:
            collat_score = 1.0 if p.collateral_impact == "LOW" else (0.6 if p.collateral_impact == "MEDIUM" else 0.2)
            return (p.expected_containment_strength * 0.45) + (0.2 if p.reversibility else 0.0) + (collat_score * 0.35)

        sorted_points = sorted(containment_points, key=score_point, reverse=True)
        for rank, p in enumerate(sorted_points, start=1):
            p.recommendation_rank = rank

        return sorted_points

    def simulate_containment_barrier(
        self,
        containment_point: ContainmentPoint,
        cascade_path: list[str],
        topology: dict[str, Any],
    ) -> dict[str, Any]:
        """Simulates what happens when a specific containment barrier is engaged:

        computes prevented downstream impact vs immediate localized disruption.
        """
        idx = containment_point.sequence_idx
        blocked_nodes = cascade_path[idx + 1:] if idx + 1 < len(cascade_path) else []
        isolated_nodes = cascade_path[: idx + 1]

        return {
            "containment_point_id": containment_point.point_id,
            "contained_entity": containment_point.entity_id,
            "isolated_segment": isolated_nodes,
            "prevented_downstream_cascade": blocked_nodes,
            "containment_effective": containment_point.expected_containment_strength >= 0.7,
            "collateral_impact": containment_point.collateral_impact,
            "reversibility": containment_point.reversibility,
            "residual_vulnerability": "Medium" if len(blocked_nodes) > 0 else "None",
        }
