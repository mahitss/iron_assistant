"""Epistemic Dependency Propagation Engine for Task 107.

Tracks DAG of belief dependencies and propagates uncertainty downstream
when an upstream foundation is contradicted, contested, or invalidated.

Strict Invariants:
- Bounded depth limits (depth <= 4) to prevent infinite loops.
- Do not silently maintain confident status when upstream foundation has collapsed.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Set, Tuple

from app.belief.domain import (
    Belief,
    BeliefDependency,
    BeliefStatus,
    UncertaintyType,
    generate_uuid,
    utc_now,
)

logger = logging.getLogger("kairo.belief.dependencies")


class DependencyPropagationEngine:
    """Manages belief dependency DAG and uncertainty cascades."""

    def __init__(self, max_depth: int = 4) -> None:
        self.max_depth = max_depth
        self._dependencies: Dict[str, List[BeliefDependency]] = {}  # parent_id -> list of dependencies

    def register_dependency(
        self,
        parent_belief_id: str,
        child_belief_id: str,
        dependency_strength: float = 1.0,
        is_hard_prerequisite: bool = True,
        notes: str = "",
    ) -> BeliefDependency:
        """Record that child belief epistemic validity depends on parent belief."""
        dep = BeliefDependency(
            dependency_id=generate_uuid("bdep"),
            parent_belief_id=parent_belief_id,
            child_belief_id=child_belief_id,
            dependency_strength=dependency_strength,
            is_hard_prerequisite=is_hard_prerequisite,
            notes=notes,
            created_at=utc_now(),
        )
        if parent_belief_id not in self._dependencies:
            self._dependencies[parent_belief_id] = []
        self._dependencies[parent_belief_id].append(dep)
        logger.info(
            "DEPENDENCY_REGISTERED: Belief %s depends on %s (hard=%s, strength=%.2f)",
            child_belief_id,
            parent_belief_id,
            is_hard_prerequisite,
            dependency_strength,
        )
        return dep

    def get_dependencies_for_parent(self, parent_belief_id: str) -> List[BeliefDependency]:
        return self._dependencies.get(parent_belief_id, [])

    def propagate_upstream_change(
        self,
        parent_belief: Belief,
        beliefs_map: Dict[str, Belief],
    ) -> List[Tuple[str, BeliefStatus, str]]:
        """Propagate uncertainty or contradiction downstream to all dependent beliefs.
        
        Returns:
            List of (child_belief_id, new_status, reason)
        """
        impacted: List[Tuple[str, BeliefStatus, str]] = []
        visited: Set[str] = set()

        def _traverse(curr_parent_id: str, depth: int) -> None:
            if depth > self.max_depth:
                return
            deps = self._dependencies.get(curr_parent_id, [])
            for dep in deps:
                child_id = dep.child_belief_id
                if child_id in visited:
                    continue
                visited.add(child_id)

                child_belief = beliefs_map.get(child_id)
                if not child_belief:
                    continue

                # Determine child impact based on parent status
                if parent_belief.status in {BeliefStatus.CONTRADICTED, BeliefStatus.REJECTED}:
                    if dep.is_hard_prerequisite:
                        new_status = BeliefStatus.REVALIDATION_REQUIRED
                        reason = f"Hard prerequisite belief '{parent_belief.belief_id}' was {parent_belief.status.value}."
                        child_belief.status = new_status
                        child_belief.confidence = max(0.1, round(child_belief.confidence * 0.5, 3))
                        child_belief.uncertainty = round(1.0 - child_belief.confidence, 3)
                        child_belief.uncertainty_type = UncertaintyType.CONFLICTED
                        impacted.append((child_id, new_status, reason))
                    else:
                        child_belief.confidence = max(0.2, round(child_belief.confidence * 0.7, 3))
                        reason = f"Upstream supporting belief '{parent_belief.belief_id}' was {parent_belief.status.value}."
                        impacted.append((child_id, child_belief.status, reason))

                elif parent_belief.status in {BeliefStatus.CONTESTED, BeliefStatus.STALE, BeliefStatus.REVALIDATION_REQUIRED}:
                    child_belief.confidence = max(0.2, round(child_belief.confidence * 0.85, 3))
                    child_belief.uncertainty = round(1.0 - child_belief.confidence, 3)
                    if child_belief.status == BeliefStatus.CONFIDENT:
                        child_belief.status = BeliefStatus.PROVISIONAL
                    reason = f"Upstream belief '{parent_belief.belief_id}' entered state {parent_belief.status.value}."
                    impacted.append((child_id, child_belief.status, reason))

                # Recurse downstream
                _traverse(child_id, depth + 1)

        _traverse(parent_belief.belief_id, 1)
        return impacted
