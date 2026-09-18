"""Ordering Engine for Task 111:
Ensures deterministic temporal ordering, deduplication, and late/out-of-order event classification.

Strict Invariants:
- EVENT ORDER != PROCESSING ORDER
- TEMPORAL ORDER != CAUSATION
- DUPLICATE EVENTS DO NOT DUPLICATE STATE TRANSITIONS
- LATE EVENTS DO NOT SILENTLY CORRUPT CURRENT STATE
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
from typing import Dict, List, Set, Tuple

from app.temporal.domain import (
    TemporalEvent,
    TemporalWatermark,
    gen_temporal_id,
    utc_now,
)


class OrderingEngine:
    """Provides deterministic ordering, deduplication, and late-arrival handling."""

    LATE_THRESHOLD_SECONDS = 300.0  # Events arriving > 5m after high-water mark are tagged late

    @classmethod
    def sort_events(cls, events: List[TemporalEvent]) -> List[TemporalEvent]:
        """Deterministically sort events by event_time, sequence_number, monotonic_timestamp, ID."""
        return sorted(
            events,
            key=lambda e: (
                e.clocks.event_time,
                e.sequence_number,
                e.monotonic_timestamp,
                e.temporal_event_id,
            ),
        )

    @classmethod
    def deduplicate(
        cls,
        events: List[TemporalEvent],
        seen_canonical_ids: Set[str],
    ) -> Tuple[List[TemporalEvent], List[TemporalEvent]]:
        """Deduplicates incoming events.
        
        Returns:
            (unique_events, duplicate_events)
        """
        unique: List[TemporalEvent] = []
        duplicates: List[TemporalEvent] = []

        for e in events:
            if e.canonical_event_id in seen_canonical_ids:
                e.is_duplicate = True
                duplicates.append(e)
            else:
                seen_canonical_ids.add(e.canonical_event_id)
                unique.append(e)

        return unique, duplicates

    @classmethod
    def detect_late_and_out_of_order(
        cls,
        events: List[TemporalEvent],
        current_watermark: datetime,
    ) -> List[TemporalEvent]:
        """Identifies out-of-order and late events relative to current watermark."""
        for e in events:
            # If event occurred before the current processing watermark, it's out of order
            if e.clocks.event_time < current_watermark:
                e.is_out_of_order = True
                lag = (current_watermark - e.clocks.event_time).total_seconds()
                if lag > cls.LATE_THRESHOLD_SECONDS:
                    e.is_late = True
        return events

    @classmethod
    def advance_watermark(
        cls,
        watermark: TemporalWatermark,
        processed_events: List[TemporalEvent],
    ) -> TemporalWatermark:
        """Advances processing and ingestion watermarks based on processed batch."""
        now = utc_now()
        watermark.last_updated = now

        if not processed_events:
            return watermark

        max_event_time = max(e.clocks.event_time for e in processed_events)
        max_ingested_time = max(e.clocks.ingested_time for e in processed_events)

        if max_event_time > watermark.source_watermark:
            watermark.source_watermark = max_event_time

        if max_ingested_time > watermark.ingestion_watermark:
            watermark.ingestion_watermark = max_ingested_time

        watermark.processing_watermark = now
        watermark.reconciliation_watermark = now

        return watermark
