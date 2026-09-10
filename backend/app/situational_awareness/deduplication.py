"""Sliding-window event deduplication and fingerprinting (Task 60)."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone

from app.situational_awareness.schemas import NormalizedEvent

logger = logging.getLogger(__name__)


class EventDeduplicator:
    """Detects duplicate events across multiple reporting monitors within a sliding time window."""

    def __init__(self, window_seconds: float = 120.0) -> None:
        self._window_seconds = window_seconds
        # Mapping: fingerprint -> (first_seen_timestamp, primary_event_id, count)
        self._seen_fingerprints: dict[str, tuple[datetime, str, int]] = {}

    def compute_fingerprint(self, event: NormalizedEvent) -> str:
        """Compute semantic fingerprint bucketed by time window."""
        epoch = event.occurred_at.timestamp()
        bucket = int(epoch / self._window_seconds)

        parts = {
            "type": event.event_type.lower(),
            "resource": (event.resource or "").lower(),
            "subject": event.subject.lower(),
            "environment": event.environment.lower(),
            "bucket": bucket,
        }
        canonical = json.dumps(parts, sort_keys=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def is_duplicate(self, event: NormalizedEvent) -> tuple[bool, str | None]:
        """Check if an event is a duplicate of a recently seen event.

        Returns:
            (is_duplicate, original_event_id)
        """
        self._purge_expired()
        fp = self.compute_fingerprint(event)

        if fp in self._seen_fingerprints:
            first_seen, original_id, count = self._seen_fingerprints[fp]
            self._seen_fingerprints[fp] = (first_seen, original_id, count + 1)
            logger.info(
                "EVENT_DEDUPLICATED: id=%s matches original=%s (count=%d)",
                event.event_id,
                original_id,
                count + 1,
            )
            return True, original_id

        now = datetime.now(timezone.utc)
        self._seen_fingerprints[fp] = (now, event.event_id, 1)
        return False, None

    def _purge_expired(self) -> None:
        """Remove fingerprints older than the sliding window."""
        now = datetime.now(timezone.utc)
        to_delete = []
        for fp, (first_seen, _, _) in self._seen_fingerprints.items():
            if (now - first_seen).total_seconds() > (self._window_seconds * 2):
                to_delete.append(fp)
        for fp in to_delete:
            del self._seen_fingerprints[fp]


event_deduplicator = EventDeduplicator()
