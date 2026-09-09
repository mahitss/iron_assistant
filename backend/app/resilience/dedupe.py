"""Event deduplication, monotonic version ordering, and stale event rejection."""

from datetime import UTC, datetime, timedelta
import logging
from typing import Any

from app.resilience.schemas import utc_now

logger = logging.getLogger(__name__)


class EventDedupeManager:
    """Provides sliding-window event deduplication and strict sequence ordering per entity."""

    def __init__(self, ttl_seconds: int = 3600) -> None:
        self.ttl = timedelta(seconds=ttl_seconds)
        self._processed_events: dict[str, datetime] = {}
        self._entity_versions: dict[str, int] = {}

    def is_duplicate_event(self, event_id: str) -> bool:
        """Checks if an event_id was already delivered within the deduplication window."""
        now = utc_now()
        # Evict expired entries occasionally
        if len(self._processed_events) > 2000:
            self._evict_expired(now)

        if event_id in self._processed_events:
            recorded = self._processed_events[event_id]
            if now - recorded < self.ttl:
                logger.info("Resilience: Duplicate event '%s' detected and suppressed.", event_id)
                return True
        self._processed_events[event_id] = now
        return False

    def is_stale_event(self, entity_id: str, event_version: int) -> bool:
        """Checks if event version is older than or equal to current observed entity version."""
        current_ver = self._entity_versions.get(entity_id, 0)
        if event_version <= current_ver:
            logger.warning(
                "Resilience: Stale event for entity '%s' (event v%d <= current v%d) rejected.",
                entity_id, event_version, current_ver
            )
            return True
        self._entity_versions[entity_id] = event_version
        return False

    def _evict_expired(self, now: datetime) -> None:
        expired = [eid for eid, t in self._processed_events.items() if now - t > self.ttl]
        for eid in expired:
            self._processed_events.pop(eid, None)
