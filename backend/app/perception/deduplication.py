"""Event Deduplication, Idempotency Protection, and Fingerprint Tracking (Task 46)."""

from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timezone
import logging
from typing import Optional

from app.perception.events import PerceptionEvent

logger = logging.getLogger("kairo.perception.deduplication")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EventDeduplicator:
    """Detects and suppresses duplicate environmental events to preserve idempotency (Spec 16, 17)."""

    def __init__(self, max_capacity: int = 10000) -> None:
        self.max_capacity = max_capacity
        # event_id -> seen_timestamp
        self._seen_ids: OrderedDict[str, datetime] = OrderedDict()
        # event_hash -> seen_timestamp
        self._seen_hashes: OrderedDict[str, datetime] = OrderedDict()

    def is_duplicate(self, event: PerceptionEvent) -> bool:
        """Check if an event ID or structural payload hash has already been processed (Spec 16)."""
        now = utc_now()

        # 1. Check ID-based duplicate
        if event.event_id in self._seen_ids:
            logger.info("Duplicate event ignored by ID: %s (source=%s)", event.event_id, event.source_id)
            return True

        # 2. Check hash-based duplicate (same payload/sequence/timestamp from same source)
        h = event.compute_hash()
        if h in self._seen_hashes:
            logger.info("Duplicate event ignored by hash: %s (source=%s, type=%s)", event.event_id, event.source_id, event.event_type.value)
            return True

        # Evict oldest if capacity exceeded
        if len(self._seen_ids) >= self.max_capacity:
            self._seen_ids.popitem(last=False)
        if len(self._seen_hashes) >= self.max_capacity:
            self._seen_hashes.popitem(last=False)

        self._seen_ids[event.event_id] = now
        self._seen_hashes[h] = now
        return False

    def clear(self) -> None:
        self._seen_ids.clear()
        self._seen_hashes.clear()
