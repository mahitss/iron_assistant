"""Causal dependency graph traversal, blast radius computation, and cascading failure propagation (Task 65, Spec 30, 31, 37)."""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from typing import Any

from app.foresight.schemas import (
    ForesightEntity,
    ForesightRelationship,
    RelationshipType,
)

logger = logging.getLogger(__name__)


class CausalPropagationEngine:
    """Traverses dependency graphs, computes blast radii, and evaluates cascading impacts (Spec 30, 31)."""

    def compute_blast_radius(
        self,
        root_entity_id: str,
        relationships: list[ForesightRelationship],
        max_depth: int = 5,
    ) -> list[str]:
        """Identify all downstream entities that depend on or are affected by root_entity_id.

        If root_entity degrades or fails, the blast radius contains all nodes that transitively DEPEND_ON it.
        """
        # Build reverse dependency map: who depends on whom
        # If A depends on B (rel.source=A, rel.target=B), then B failing affects A!
        dependents_map: dict[str, list[str]] = defaultdict(list)
        for r in relationships:
            if r.relationship_type in (
                RelationshipType.DEPENDS_ON,
                RelationshipType.USES,
                RelationshipType.CONSUMES,
            ):
                # source depends on target -> target degradation affects source
                dependents_map[r.target_entity_id].append(r.source_entity_id)
            elif r.relationship_type in (
                RelationshipType.AFFECTS,
                RelationshipType.CAUSES,
                RelationshipType.CONTROLS,
                RelationshipType.BLOCKS,
            ):
                # source affects target -> source degradation directly affects target
                dependents_map[r.source_entity_id].append(r.target_entity_id)

        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(root_entity_id, 0)])

        while queue:
            current, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for downstream in dependents_map.get(current, []):
                if downstream not in visited and downstream != root_entity_id:
                    visited.add(downstream)
                    queue.append((downstream, depth + 1))

        return list(visited)

    def identify_single_points_of_failure(
        self,
        entities: list[ForesightEntity],
        relationships: list[ForesightRelationship],
        critical_threshold: int = 2,
    ) -> list[str]:
        """Identify critical nodes on which multiple other systems depend with no alternative."""
        dependent_counts: dict[str, int] = defaultdict(int)
        for r in relationships:
            if r.is_critical or r.relationship_type in (RelationshipType.DEPENDS_ON, RelationshipType.USES):
                dependent_counts[r.target_entity_id] += 1

        spofs = [eid for eid, count in dependent_counts.items() if count >= critical_threshold]
        return spofs

    def propagate_cascading_impact(
        self,
        failing_entity_id: str,
        entities: dict[str, ForesightEntity],
        relationships: list[ForesightRelationship],
        initial_impact: float = 0.9,
    ) -> list[dict[str, Any]]:
        """Compute cascading degradation across dependencies with confidence decay (Spec 37).

        Invariant: Never fabricate causal certainty. Uncertainty compounds with chain length.
        """
        dependents_map: dict[str, list[ForesightRelationship]] = defaultdict(list)
        for r in relationships:
            if r.relationship_type in (RelationshipType.DEPENDS_ON, RelationshipType.USES):
                dependents_map[r.target_entity_id].append(r)
            elif r.relationship_type in (RelationshipType.AFFECTS, RelationshipType.CAUSES):
                dependents_map[r.source_entity_id].append(r)

        cascading_steps: list[dict[str, Any]] = []
        visited: set[str] = {failing_entity_id}
        queue: deque[tuple[str, float, int]] = deque([(failing_entity_id, initial_impact, 1)])

        while queue:
            curr_id, curr_impact, depth = queue.popleft()
            if depth > 4:
                continue

            for rel in dependents_map.get(curr_id, []):
                target = rel.source_entity_id if rel.target_entity_id == curr_id else rel.target_entity_id
                if target in visited:
                    continue

                visited.add(target)
                # Impact decay based on causal_strength and hop distance
                propagated_impact = round(curr_impact * rel.causal_strength * 0.85, 3)
                propagated_confidence = round(rel.confidence * (0.9**depth), 3)

                ent = entities.get(target)
                target_name = ent.name if ent else target

                step = {
                    "step": depth,
                    "affected_entity_id": target,
                    "affected_entity_name": target_name,
                    "propagated_from": curr_id,
                    "relationship": rel.relationship_type.value,
                    "estimated_impact": propagated_impact,
                    "confidence": propagated_confidence,
                    "is_critical": rel.is_critical,
                }
                cascading_steps.append(step)
                queue.append((target, propagated_impact, depth + 1))

        return cascading_steps


causal_propagation_engine = CausalPropagationEngine()
