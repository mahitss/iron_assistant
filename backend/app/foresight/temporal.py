"""Temporal state versioning, historical reconstruction, late event handling, and world diff engine (Task 65, Spec 8, 9, 11, 15)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.foresight.schemas import (
    ForesightEntity,
    ForesightRelationship,
    RelationshipType,
    StateAuthority,
    StateVersionRecord,
    WorldDiff,
)

logger = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class TemporalWorldManager:
    """Maintains immutable historical state versions and reconstructs past worlds (Spec 8, 9)."""

    def __init__(self) -> None:
        # Map of entity_id -> chronological list of StateVersionRecord
        self._history: dict[str, list[StateVersionRecord]] = {}

    def record_state_transition(
        self,
        entity_id: str,
        state: str,
        observed_at: datetime | None = None,
        source: str = "system",
        confidence: float = 0.8,
        authority: StateAuthority = StateAuthority.OBSERVED,
        metadata: dict[str, Any] | None = None,
    ) -> StateVersionRecord:
        """Append an immutable state transition to history.

        Invariant: Never silently overwrite state without a versioned record.
        """
        now = _now_utc()
        obs_time = observed_at or now

        if entity_id not in self._history:
            self._history[entity_id] = []

        history_list = self._history[entity_id]
        next_version = len(history_list) + 1

        rec = StateVersionRecord(
            entity_id=entity_id,
            state_version=next_version,
            state=state.upper(),
            observed_at=obs_time,
            received_at=now,
            valid_from=obs_time,
            valid_until=None,
            source=source,
            confidence=confidence,
            authority=authority,
            metadata=metadata or {},
        )

        # Update previous record's valid_until if chronological
        if history_list and history_list[-1].observed_at <= obs_time:
            history_list[-1].valid_until = obs_time

        history_list.append(rec)
        # Sort chronologically by observed_at to handle out-of-order ingestion
        history_list.sort(key=lambda r: r.observed_at)

        logger.info(
            "STATE_VERSION_RECORDED: entity=%s version=%d state=%s observed_at=%s",
            entity_id,
            next_version,
            state.upper(),
            obs_time.isoformat(),
        )
        return rec

    def ingest_out_of_order_event(
        self,
        entity_id: str,
        state: str,
        event_timestamp: datetime,
        source: str = "late_telemetry",
        confidence: float = 0.75,
    ) -> StateVersionRecord:
        """Handle late, out-of-order events without corrupting current true state (Spec 11).

        Invariant: HISTORICAL STATE != CURRENT STATE. A late historical event must not
        overwrite the current state if a newer observation exists.
        """
        now = _now_utc()
        history_list = self._history.setdefault(entity_id, [])

        # Check if late event is older than our most recent observation
        is_late = bool(history_list and event_timestamp < history_list[-1].observed_at)

        rec = StateVersionRecord(
            entity_id=entity_id,
            state_version=len(history_list) + 1,
            state=state.upper(),
            observed_at=event_timestamp,
            received_at=now,
            valid_from=event_timestamp,
            valid_until=None,
            source=source,
            confidence=confidence,
            authority=StateAuthority.OBSERVED,
            metadata={"is_out_of_order": is_late},
        )

        history_list.append(rec)
        history_list.sort(key=lambda r: r.observed_at)

        # Recompute validity intervals across chronological chain
        for i in range(len(history_list) - 1):
            history_list[i].valid_until = history_list[i + 1].observed_at
        history_list[-1].valid_until = None

        logger.info(
            "OUT_OF_ORDER_EVENT_INGESTED: entity=%s state=%s obs_time=%s is_late=%s",
            entity_id,
            state.upper(),
            event_timestamp.isoformat(),
            is_late,
        )
        return rec

    def get_state_at_time(self, entity_id: str, point_in_time: datetime) -> str | None:
        """Answer 'What was true at time T?' (Spec 9).

        Retrieves historical state of an entity at a given timestamp.
        """
        history_list = self._history.get(entity_id, [])
        if not history_list:
            return None

        # Find the record that was active at point_in_time
        active_record: StateVersionRecord | None = None
        for r in history_list:
            if r.observed_at <= point_in_time:
                active_record = r
            else:
                break
        return active_record.state if active_record else None

    def get_history(self, entity_id: str) -> list[StateVersionRecord]:
        """Return full chronological state history for an entity."""
        return list(self._history.get(entity_id, []))

    def compute_diff(
        self,
        entities_a: dict[str, ForesightEntity],
        entities_b: dict[str, ForesightEntity],
        relationships_a: dict[str, ForesightRelationship],
        relationships_b: dict[str, ForesightRelationship],
    ) -> WorldDiff:
        """Compute structural difference between two world states or snapshots (Spec 15).

        Identifies:
        - added / removed entities
        - changed states
        - new / removed dependencies
        - changed relationships
        """
        added_entities = [k for k in entities_b if k not in entities_a]
        removed_entities = [k for k in entities_a if k not in entities_b]

        changed_states: dict[str, dict[str, str]] = {}
        for eid in entities_a:
            if eid in entities_b:
                s_a = entities_a[eid].state
                s_b = entities_b[eid].state
                if s_a != s_b:
                    changed_states[eid] = {"before": s_a, "after": s_b}

        # Dependencies diff
        deps_a = {
            k: r
            for k, r in relationships_a.items()
            if r.relationship_type in (RelationshipType.DEPENDS_ON, RelationshipType.CAUSES)
        }
        deps_b = {
            k: r
            for k, r in relationships_b.items()
            if r.relationship_type in (RelationshipType.DEPENDS_ON, RelationshipType.CAUSES)
        }

        new_dependencies = [k for k in deps_b if k not in deps_a]
        removed_dependencies = [k for k in deps_a if k not in deps_b]

        # Other relationships
        changed_relationships = [
            k for k in relationships_b if k not in relationships_a and k not in new_dependencies
        ]

        return WorldDiff(
            added_entities=added_entities,
            removed_entities=removed_entities,
            changed_states=changed_states,
            new_dependencies=new_dependencies,
            removed_dependencies=removed_dependencies,
            changed_relationships=changed_relationships,
            changed_assumptions=[],
            new_risks=[],
            new_opportunities=[],
        )

    def clear(self) -> None:
        """Clear temporal history (for tests)."""
        self._history.clear()


temporal_world_manager = TemporalWorldManager()
