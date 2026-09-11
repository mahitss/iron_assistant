"""Relationship and causal edge management for Autonomous World Model (Task 65, Spec 5, 6)."""

from __future__ import annotations

import logging
from typing import Any

from app.foresight.safety import ForesightSafetyError
from app.foresight.schemas import (
    ForesightRelationship,
    RelationshipType,
    WorldScope,
)

logger = logging.getLogger(__name__)


class ForesightRelationshipManager:
    """Manages semantic and causal edges connecting entities in the world graph."""

    def __init__(self) -> None:
        self._relationships: dict[str, ForesightRelationship] = {}

    def add_relationship(
        self,
        source_entity_id: str,
        target_entity_id: str,
        relationship_type: RelationshipType = RelationshipType.DEPENDS_ON,
        causal_strength: float = 0.5,
        evidence: list[str] | None = None,
        confidence: float = 0.8,
        conditions: list[str] | None = None,
        scope: WorldScope = WorldScope.SYSTEM,
        is_critical: bool = False,
        provenance: dict[str, Any] | None = None,
    ) -> ForesightRelationship:
        """Add or update an edge between two entities.

        Invariant: CORRELATION != CAUSATION (Spec 6).
        A CAUSES relationship requires explicit empirical evidence.
        """
        evidence_list = evidence or []
        if relationship_type == RelationshipType.CAUSES and not evidence_list:
            raise ForesightSafetyError(
                f"Causal Invariant Violation: Relationship CAUSES between '{source_entity_id}' and '{target_entity_id}' "
                "requires empirical evidence or intervention backing. Precedence alone does not prove causation."
            )

        edge_id = f"rel_{source_entity_id}__{relationship_type.value}__{target_entity_id}"
        rel = ForesightRelationship(
            rel_id=edge_id,
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            relationship_type=relationship_type,
            causal_strength=causal_strength,
            evidence=evidence_list,
            confidence=confidence,
            conditions=conditions or [],
            scope=scope,
            is_critical=is_critical,
            provenance=provenance or {"declared": True},
        )
        self._relationships[edge_id] = rel
        logger.info(
            "RELATIONSHIP_ADDED: id=%s (%s -[%s]-> %s)",
            edge_id,
            source_entity_id,
            relationship_type.value,
            target_entity_id,
        )
        return rel

    def get_relationship(self, rel_id: str) -> ForesightRelationship | None:
        """Retrieve relationship by ID."""
        return self._relationships.get(rel_id)

    def list_relationships(
        self,
        source_id: str | None = None,
        target_id: str | None = None,
        relationship_type: RelationshipType | None = None,
    ) -> list[ForesightRelationship]:
        """List relationships matching criteria."""
        results: list[ForesightRelationship] = []
        for r in self._relationships.values():
            if source_id and r.source_entity_id != source_id:
                continue
            if target_id and r.target_entity_id != target_id:
                continue
            if relationship_type and r.relationship_type != relationship_type:
                continue
            results.append(r)
        return results

    def remove_relationship(self, rel_id: str) -> bool:
        """Remove a relationship edge."""
        if rel_id in self._relationships:
            del self._relationships[rel_id]
            return True
        return False

    def clear(self) -> None:
        """Clear relationship cache (for tests)."""
        self._relationships.clear()


foresight_relationship_manager = ForesightRelationshipManager()
