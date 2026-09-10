"""Chronological timeline construction and fact-inference distinction (Task 60)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.situational_awareness.schemas import (
    NormalizedEvent,
    SituationTimelineEntry,
)

logger = logging.getLogger(__name__)


class TimelineEngine:
    """Builds chronological situation timelines clearly separating observed facts from inferences.

    Invariant 104: Timeline order does not prove causal relationship.
    """

    def build_timeline(
        self,
        events: list[NormalizedEvent],
        inferences: list[dict[str, Any]] | None = None,
    ) -> list[SituationTimelineEntry]:
        """Construct a sorted timeline from events and inference points."""
        entries: list[SituationTimelineEntry] = []

        # 1. Add observed events as facts
        for evt in events:
            summary = f"[{evt.source}] {evt.subject}"
            if evt.resource:
                summary += f" (resource: {evt.resource})"
            entry = SituationTimelineEntry(
                timestamp=evt.occurred_at,
                event_type=evt.event_type,
                summary=summary,
                is_inference=False,
                evidence_id=evt.event_id,
            )
            entries.append(entry)

        # 2. Add inferences / hypotheses as explicit inference entries
        for inf in inferences or []:
            ts = inf.get("timestamp", datetime.now(timezone.utc))
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts)
            entry = SituationTimelineEntry(
                timestamp=ts,
                event_type=inf.get("type", "INFERENCE"),
                summary=f"[INFERENCE] {inf.get('summary', '')}",
                is_inference=True,
                evidence_id=inf.get("evidence_id"),
            )
            entries.append(entry)

        # 3. Sort chronologically to properly position late-arriving events
        entries.sort(key=lambda x: x.timestamp)
        return entries


timeline_engine = TimelineEngine()
