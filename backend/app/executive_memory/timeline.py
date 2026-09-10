"""Timeline intelligence, chronological event ingestion, and historical query support (INVARIANTS 9-13, 129-134)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
import uuid

from app.executive_memory.schemas import TimelineEventSchema, TimelineEventType
from app.executive_memory.temporal import TemporalEngine


class TimelineEngine:
    """Manages the chronological, authoritative timeline of project and system events."""

    def __init__(self) -> None:
        # event_id -> TimelineEventSchema
        self._events: dict[str, TimelineEventSchema] = {}
        # dedup_hash -> event_id
        self._dedup_index: set[str] = set()

    def _generate_dedup_key(
        self,
        event_type: str,
        project_id: str | None,
        timestamp: datetime,
        description: str,
    ) -> str:
        ts_str = timestamp.isoformat()
        return f"{event_type}:{project_id or 'none'}:{ts_str}:{description.strip().lower()}"

    def record_event(
        self,
        event_type: TimelineEventType,
        source: str,
        description_reference: str,
        project_id: str | None = None,
        actor: str = "kairo",
        impact: str = "MEDIUM",
        timestamp: datetime | None = None,
        provenance: dict[str, Any] | None = None,
    ) -> TimelineEventSchema:
        """INVARIANT 10 & 130: Records timeline event with authoritative timestamp and deduplication."""
        event_time = TemporalEngine.ensure_utc(timestamp)
        type_str = event_type.value if hasattr(event_type, "value") else str(event_type)

        dedup_key = self._generate_dedup_key(type_str, project_id, event_time, description_reference)
        if dedup_key in self._dedup_index:
            # INVARIANT 130: Return existing matching event instead of duplicating
            for ev in self._events.values():
                if self._generate_dedup_key(ev.event_type, ev.project_id, ev.timestamp, ev.description_reference) == dedup_key:
                    return ev

        eid = f"evt_{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC)
        event = TimelineEventSchema(
            event_id=eid,
            timestamp=event_time,
            event_type=event_type,
            source=source,
            project_id=project_id,
            actor=actor,
            description_reference=description_reference.strip(),
            impact=impact,
            provenance=provenance or {"source": source},
            created_at=now,
        )
        self._events[eid] = event
        self._dedup_index.add(dedup_key)
        return event

    def list_events(
        self,
        project_id: str | None = None,
        event_type: TimelineEventType | str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        as_of: datetime | None = None,
        limit: int | None = None,
    ) -> list[TimelineEventSchema]:
        """Returns chronologically ordered events matching filter criteria."""
        effective_until = as_of or until
        results = list(self._events.values())
        if project_id:
            results = [e for e in results if e.project_id == project_id]
        if event_type:
            target_type = event_type.value if hasattr(event_type, "value") else str(event_type)
            results = [e for e in results if e.event_type == target_type]
        if since:
            since_utc = TemporalEngine.ensure_utc(since)
            results = [e for e in results if e.timestamp >= since_utc]
        if effective_until:
            until_utc = TemporalEngine.ensure_utc(effective_until)
            results = [e for e in results if e.timestamp <= until_utc]

        sorted_dicts = TemporalEngine.sort_events_deterministically([e.model_dump() for e in results])
        events = [TimelineEventSchema(**d) for d in sorted_dicts]
        if limit:
            events = events[:limit]
        return events

    def get_events_as_of(self, cutoff_timestamp: datetime, project_id: str | None = None) -> list[TimelineEventSchema]:
        """INVARIANT 20: Returns events strictly available up to the given cutoff timestamp."""
        return self.list_events(project_id=project_id, until=cutoff_timestamp)

    def correlate_events(self, event_ids: list[str]) -> list[TimelineEventSchema]:
        """INVARIANT 131-134: Correlates related events while preserving explicit links."""
        matched = [self._events[eid] for eid in event_ids if eid in self._events]
        sorted_dicts = TemporalEngine.sort_events_deterministically([e.model_dump() for e in matched])
        return [TimelineEventSchema(**d) for d in sorted_dicts]
