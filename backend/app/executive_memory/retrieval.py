"""Date-aware and project-scoped context retrieval (INVARIANTS 106, 135, 136)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.executive_memory.temporal import TemporalEngine
from app.executive_memory.timeline import TimelineEngine


class ExecutiveRetrievalEngine:
    """Retrieves date-aware and project-scoped historical context."""

    def __init__(self, timeline_engine: TimelineEngine) -> None:
        self.timeline_engine = timeline_engine

    def retrieve_context(
        self,
        project_id: str | None = None,
        as_of: datetime | None = None,
        keywords: list[str] | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """INVARIANT 106 & 135: Scoped and date-aware retrieval."""
        cutoff = TemporalEngine.ensure_utc(as_of) if as_of else datetime.now(UTC)
        events = self.timeline_engine.get_events_as_of(cutoff, project_id=project_id)

        if keywords:
            filtered = []
            for ev in events:
                text = f"{ev.description_reference} {ev.event_type} {ev.actor}".lower()
                if any(k.lower() in text for k in keywords):
                    filtered.append(ev)
            events = filtered

        return [e.model_dump() for e in events[:limit]]
