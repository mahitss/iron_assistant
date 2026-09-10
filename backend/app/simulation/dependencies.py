"""Digital Twin dependency topology bridge, cascade failure detection, and blast radius estimation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BlastRadiusEstimate(BaseModel):
    """Estimated blast radius of hypothetical intervention with topology completeness metrics."""

    origin_node: str
    affected_nodes: list[str] = Field(default_factory=list)
    impacted_services_count: int = 0
    blast_radius_level: str = "MINIMAL"  # MINIMAL, CONTAINED, MODERATE, EXTENSIVE, CRITICAL
    topology_completeness: float = 1.0  # 0.0 to 1.0; if < 1.0, uncertainty is flagged
    uncertainty_note: str | None = None


class CascadeFailureEstimate(BaseModel):
    """Estimated cascade failure propagation through downstream dependencies."""

    is_cascade_likely: bool = False
    failing_nodes: list[str] = Field(default_factory=list)
    cascade_depth: int = 0
    cascade_evidence: list[str] = Field(default_factory=list)
    disclaimer: str = "Cascade analysis is an estimate based on known topology; unmapped dependencies may alter outcome."


class DependencyBridge:
    """Extracts and analyzes dependency graphs from Digital Twin and World Model states."""

    def extract_topology(self, digital_twin_state: dict[str, Any]) -> dict[str, list[str]]:
        """Extracts directed adjacency list {source: [downstream_dependents]} from twin state."""
        # 1. Check for explicit topology/dependencies in twin state
        if "dependencies" in digital_twin_state and isinstance(digital_twin_state["dependencies"], dict):
            return {str(k): [str(target) for target in v] for k, v in digital_twin_state["dependencies"].items()}

        # 2. Check for graph structure from Causal/Twin models
        if "graph" in digital_twin_state and "edges" in digital_twin_state["graph"]:
            adj: dict[str, list[str]] = {}
            for edge in digital_twin_state["graph"]["edges"]:
                src = str(edge.get("source", ""))
                tgt = str(edge.get("target", ""))
                if src and tgt:
                    adj.setdefault(src, []).append(tgt)
            return adj

        # 3. Fallback to basic services hierarchy if present
        services = digital_twin_state.get("services", {})
        adj = {}
        for svc_name, svc_info in services.items():
            if isinstance(svc_info, dict) and "depends_on" in svc_info:
                # If svc depends_on X, then when X changes, svc is downstream of X
                for upstream in svc_info["depends_on"]:
                    adj.setdefault(str(upstream), []).append(str(svc_name))
        return adj

    def estimate_blast_radius(
        self,
        origin_node: str,
        topology: dict[str, list[str]],
        max_depth: int = 4,
        is_topology_partial: bool = False,
    ) -> BlastRadiusEstimate:
        """Estimates reachable downstream nodes within bounded depth."""
        visited: set[str] = set()
        queue: list[tuple[str, int]] = [(origin_node, 0)]

        while queue:
            curr, depth = queue.pop(0)
            if curr not in visited:
                visited.add(curr)
                if depth < max_depth:
                    for neighbor in topology.get(curr, []):
                        if neighbor not in visited:
                            queue.append((neighbor, depth + 1))

        # Exclude the origin itself from downstream affected list
        downstream = [n for n in visited if n != origin_node]
        count = len(downstream)

        if count == 0:
            level = "MINIMAL"
        elif count <= 2:
            level = "CONTAINED"
        elif count <= 5:
            level = "MODERATE"
        elif count <= 10:
            level = "EXTENSIVE"
        else:
            level = "CRITICAL"

        completeness = 0.7 if is_topology_partial else 1.0
        note = None
        if is_topology_partial or completeness < 1.0:
            note = "Incomplete topology: Blast radius may be understated due to unmapped service dependencies."

        return BlastRadiusEstimate(
            origin_node=origin_node,
            affected_nodes=downstream,
            impacted_services_count=count,
            blast_radius_level=level,
            topology_completeness=completeness,
            uncertainty_note=note,
        )

    def detect_cascades(
        self,
        origin_node: str,
        is_fatal_failure: bool,
        topology: dict[str, list[str]],
        max_depth: int = 4,
    ) -> CascadeFailureEstimate:
        """Determines whether a critical failure in origin node will cascade down the dependency graph."""
        if not is_fatal_failure:
            return CascadeFailureEstimate(is_cascade_likely=False)

        failing = [origin_node]
        evidence = [f"Origin node '{origin_node}' experienced fatal failure."]
        curr_level = [origin_node]
        depth = 0

        while curr_level and depth < max_depth:
            next_level = []
            for node in curr_level:
                dependents = topology.get(node, [])
                for dep in dependents:
                    if dep not in failing:
                        failing.append(dep)
                        next_level.append(dep)
                        evidence.append(f"Downstream service '{dep}' starved of critical upstream '{node}'.")
            curr_level = next_level
            if next_level:
                depth += 1

        is_likely = len(failing) > 1
        return CascadeFailureEstimate(
            is_cascade_likely=is_likely,
            failing_nodes=failing,
            cascade_depth=depth,
            cascade_evidence=evidence,
        )
