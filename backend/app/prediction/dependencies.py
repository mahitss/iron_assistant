"""Dependency Graph Integration, Failure Propagation, and Cascade Risk Modeling (Task 47)."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("kairo.prediction.dependencies")


@dataclass
class CascadeRiskScenario:
    """Estimated downstream propagation of an upstream failure (Spec 72-75).
    
    CRITICAL INVARIANT: Cascade != Certainty! (Spec 75)
    Represent downstream impact as probabilistic scenario, never certainty.
    """

    root_cause_component: str
    impacted_downstream: List[str]
    propagation_depth: int
    cascade_likelihood: float
    evidence: Dict[str, Any] = field(default_factory=dict)
    root_service: str = ""
    affected_services: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.root_service:
            self.root_service = self.root_cause_component
        if not self.affected_services:
            self.affected_services = list(self.impacted_downstream)


class DependencyCascadeModel:
    """Models failure propagation along established World Model relationships (Spec 72-75)."""

    def __init__(self) -> None:
        # component -> set of dependent components (e.g. database -> [auth_service, payment_service])
        self._downstream_graph: Dict[str, Set[str]] = {}

    def register_dependency(self, upstream: str, downstream: str) -> None:
        self._downstream_graph.setdefault(upstream, set()).add(downstream)

    def estimate_cascade_risk(
        self,
        failing_component: str,
        initial_confidence: float = 0.8,
        downstream_services: Optional[List[str]] = None,
    ) -> CascadeRiskScenario:
        """Enforce Spec 73-75: Downstream effects estimated only with structural relationship evidence."""
        if downstream_services:
            for s in downstream_services:
                self.register_dependency(failing_component, s)

        visited: Set[str] = set()
        queue: List[tuple[str, int, float]] = [(failing_component, 0, initial_confidence)]
        impacted: List[str] = []
        max_depth = 0

        while queue:
            curr, depth, cur_prob = queue.pop(0)
            if curr != failing_component and curr not in visited:
                visited.add(curr)
                impacted.append(curr)
                max_depth = max(max_depth, depth)

            for child in self._downstream_graph.get(curr, set()):
                if child not in visited:
                    # Probabilistic decay down the dependency chain
                    child_prob = cur_prob * 0.85
                    queue.append((child, depth + 1, child_prob))

        scenario = CascadeRiskScenario(
            root_cause_component=failing_component,
            impacted_downstream=impacted,
            propagation_depth=max_depth,
            cascade_likelihood=round(initial_confidence * (0.85 ** max(1, max_depth)), 3),
            evidence={"graph_topology_source": "world_model_dependencies", "root": failing_component},
            root_service=failing_component,
            affected_services=impacted,
        )
        logger.info("Estimated cascade risk from %s: %d downstream components impacted", failing_component, len(impacted))
        return scenario
