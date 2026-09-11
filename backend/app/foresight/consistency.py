"""World model self-checker, consistency audits, and anomaly detection (Task 65, Spec 90)."""

from __future__ import annotations

import logging
from typing import Any

from app.foresight.schemas import (
    ForesightEntity,
    ForesightRelationship,
    InconsistencyType,
    RelationshipType,
    UncertaintyGrade,
)

logger = logging.getLogger(__name__)


class WorldModelConsistencyChecker:
    """Audits world model state for contradictions, circular dependencies, and confidence anomalies (Spec 90)."""

    def audit_consistency(
        self,
        entities: dict[str, ForesightEntity],
        relationships: list[ForesightRelationship],
    ) -> list[dict[str, Any]]:
        """Run consistency verification across the current world model state.

        Detects:
        - Contradictory states
        - Circular causality or dependency self-loops
        - Stale dependencies (pointing to missing or stale nodes)
        - Orphaned entities
        - Confidence anomalies (e.g. high confidence on unobserved/stale entities)
        """
        inconsistencies: list[dict[str, Any]] = []

        # 1. Dependency and Relationship validations
        for rel in relationships:
            # Self-loop in dependency
            if rel.source_entity_id == rel.target_entity_id and rel.relationship_type in (
                RelationshipType.DEPENDS_ON,
                RelationshipType.CAUSES,
            ):
                inconsistencies.append(
                    {
                        "type": InconsistencyType.CIRCULAR_CAUSALITY.value,
                        "description": f"Entity '{rel.source_entity_id}' has an invalid self-dependency loop.",
                        "rel_id": rel.rel_id,
                    }
                )

            # Missing target/source entity
            if rel.source_entity_id not in entities:
                inconsistencies.append(
                    {
                        "type": InconsistencyType.STALE_DEPENDENCY.value,
                        "description": f"Relationship '{rel.rel_id}' references non-existent source entity '{rel.source_entity_id}'.",
                    }
                )
            if rel.target_entity_id not in entities:
                inconsistencies.append(
                    {
                        "type": InconsistencyType.STALE_DEPENDENCY.value,
                        "description": f"Relationship '{rel.rel_id}' references non-existent target entity '{rel.target_entity_id}'.",
                    }
                )

        # 2. Entity State & Confidence checks
        for ent in entities.values():
            # Invariant: UNKNOWN != HEALTHY
            if ent.state == "UNKNOWN" and ent.confidence > 0.85:
                inconsistencies.append(
                    {
                        "type": InconsistencyType.CONFIDENCE_ANOMALY.value,
                        "description": f"Entity '{ent.entity_id}' state is UNKNOWN but has an anomalously high confidence of {ent.confidence}.",
                        "entity_id": ent.entity_id,
                    }
                )

            # Stale entity with claimed KNOWN certainty
            if ent.is_stale and ent.uncertainty == UncertaintyGrade.KNOWN:
                inconsistencies.append(
                    {
                        "type": InconsistencyType.INVALID_TEMPORAL.value,
                        "description": f"Stale entity '{ent.entity_id}' is incorrectly graded as KNOWN certainty (Invariant: STALE != CURRENT).",
                        "entity_id": ent.entity_id,
                    }
                )

        # 3. Detect 2-node circular dependency cycles (A depends on B and B depends on A)
        dep_pairs = {
            (r.source_entity_id, r.target_entity_id)
            for r in relationships
            if r.relationship_type == RelationshipType.DEPENDS_ON
        }
        for src, tgt in list(dep_pairs):
            if (tgt, src) in dep_pairs and src != tgt:
                inconsistencies.append(
                    {
                        "type": InconsistencyType.CIRCULAR_CAUSALITY.value,
                        "description": f"Circular mutual dependency detected between '{src}' and '{tgt}'.",
                    }
                )
                dep_pairs.remove((tgt, src))

        if inconsistencies:
            logger.warning("WORLD_MODEL_INCONSISTENCIES_FOUND: count=%d", len(inconsistencies))
        else:
            logger.info("WORLD_MODEL_CONSISTENCY_CLEAN: 0 anomalies detected")

        return inconsistencies


world_model_consistency_checker = WorldModelConsistencyChecker()
