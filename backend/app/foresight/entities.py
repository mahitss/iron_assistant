"""Entity management, lifecycle states, and temporal validity for World Model (Task 65, Spec 4, 7)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.foresight.schemas import (
    ForesightEntity,
    StateAuthority,
    UncertaintyGrade,
    WorldScope,
)

logger = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# Canonical state validation dictionaries
SERVICE_STATES = {"HEALTHY", "DEGRADED", "FAILED", "RECOVERING", "UNKNOWN"}
RESOURCE_STATES = {"AVAILABLE", "ALLOCATED", "CONSTRAINED", "EXHAUSTED", "UNKNOWN"}
PLAN_STATES = {"PLANNED", "ACTIVE", "BLOCKED", "COMPLETED", "FAILED", "STALE"}

# Freshness TTL in seconds by entity type
DEFAULT_FRESHNESS_TTL: dict[str, int] = {
    "service": 60,  # Telemetry stale after 60s
    "resource": 120,  # Resource utilization stale after 2m
    "database": 180,
    "agent": 300,
    "plan": 3600,  # Plan stale after 1 hour without update
    "environment": 600,
    "system": 300,
}


class ForesightEntityManager:
    """Manages domain entities with lifecycle states, confidence, and freshness boundaries."""

    def __init__(self) -> None:
        self._entities: dict[str, ForesightEntity] = {}

    def upsert_entity(
        self,
        entity_id: str,
        name: str,
        entity_type: str,
        state: str = "UNKNOWN",
        attributes: dict[str, Any] | None = None,
        scope: WorldScope = WorldScope.SYSTEM,
        confidence: float = 0.8,
        authority: StateAuthority = StateAuthority.OBSERVED,
        provenance: dict[str, Any] | None = None,
        tenant_id: str = "default",
        valid_from: datetime | None = None,
        valid_until: datetime | None = None,
    ) -> ForesightEntity:
        """Register or update an entity state.

        Invariant: UNKNOWN != HEALTHY. Defaulting an unobserved entity to HEALTHY is forbidden.
        """
        now = _now_utc()
        cleaned_state = state.upper()

        # Validate specialized lifecycle states if known
        t_lower = entity_type.lower()
        if "service" in t_lower and cleaned_state not in SERVICE_STATES:
            cleaned_state = "UNKNOWN"
        elif "resource" in t_lower and cleaned_state not in RESOURCE_STATES:
            cleaned_state = "UNKNOWN"
        elif "plan" in t_lower and cleaned_state not in PLAN_STATES:
            cleaned_state = "PLANNED"

        existing = self._entities.get(entity_id)
        version = (existing.version + 1) if existing else 1

        entity = ForesightEntity(
            entity_id=entity_id,
            type=entity_type,
            name=name,
            attributes=attributes or {},
            state=cleaned_state,
            scope=scope,
            valid_from=valid_from or (existing.valid_from if existing else now),
            valid_until=valid_until,
            confidence=confidence,
            uncertainty=UncertaintyGrade.KNOWN if confidence >= 0.9 else UncertaintyGrade.LIKELY,
            authority=authority,
            provenance=provenance or {"source": "manual_or_telemetry"},
            version=version,
            is_stale=False,
            tenant_id=tenant_id,
        )

        self._entities[entity_id] = entity
        logger.info(
            "ENTITY_UPSERTED: id=%s type=%s state=%s version=%d",
            entity_id,
            entity_type,
            cleaned_state,
            version,
        )
        return entity

    def get_entity(self, entity_id: str) -> ForesightEntity | None:
        """Retrieve entity by ID and evaluate freshness dynamically."""
        entity = self._entities.get(entity_id)
        if not entity:
            return None
        self._evaluate_freshness(entity)
        return entity

    def list_entities(
        self,
        entity_type: str | None = None,
        scope: WorldScope | None = None,
        state: str | None = None,
        tenant_id: str = "default",
    ) -> list[ForesightEntity]:
        """List entities matching optional filters, evaluating freshness for all."""
        results: list[ForesightEntity] = []
        for ent in self._entities.values():
            if tenant_id != "default" and ent.tenant_id != tenant_id:
                continue
            if entity_type and ent.type.lower() != entity_type.lower():
                continue
            if scope and ent.scope != scope:
                continue
            if state and ent.state.upper() != state.upper():
                continue
            self._evaluate_freshness(ent)
            results.append(ent)
        return results

    def remove_entity(self, entity_id: str) -> bool:
        """Remove entity from live registry."""
        if entity_id in self._entities:
            del self._entities[entity_id]
            return True
        return False

    def _evaluate_freshness(self, entity: ForesightEntity) -> None:
        """Mark entity stale if last observed timestamp exceeds TTL (Invariant: STALE != CURRENT)."""
        now = _now_utc()
        ttl_seconds = DEFAULT_FRESHNESS_TTL.get(entity.type.lower(), 600)
        age_seconds = (now - entity.valid_from).total_seconds()
        if age_seconds > ttl_seconds:
            entity.is_stale = True
            if entity.uncertainty == UncertaintyGrade.KNOWN:
                entity.uncertainty = UncertaintyGrade.UNCERTAIN

    def clear(self) -> None:
        """Clear memory cache (for tests)."""
        self._entities.clear()


foresight_entity_manager = ForesightEntityManager()
