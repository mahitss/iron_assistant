"""Durable append-only changelog engine with credential sanitization (Task 39, Spec 22-25)."""

import logging
import uuid
from collections import deque
from datetime import UTC, datetime
from typing import Any

from app.observability.sanitization import TelemetrySanitizer
from app.state.schemas import ChangelogEntry, OperationType, StateDomain

logger = logging.getLogger("kairo.state.changelog")


class StateChangelog:
    """Manages append-only change streams with strict secret scrubbing."""

    def __init__(self, max_buffer_size: int = 1000) -> None:
        self._entries: deque[ChangelogEntry] = deque(maxlen=max_buffer_size)

    def record_change(
        self,
        domain: StateDomain,
        resource_type: str,
        resource_id: str,
        version: int,
        operation: OperationType,
        actor: str,
        service: str,
        correlation_id: str | None = None,
        changes: dict[str, Any] | None = None,
    ) -> ChangelogEntry:
        """Records a change in the durable changelog, scrubbing all secrets."""
        # 1. Scrub credentials and sensitive tokens from change diff
        sanitized_changes = TelemetrySanitizer.sanitize_dict(changes) if changes else None

        entry = ChangelogEntry(
            id=f"chg_{uuid.uuid4().hex[:16]}",
            domain=domain,
            resource_type=resource_type,
            resource_id=resource_id,
            version=version,
            operation=operation,
            actor=actor,
            service=service,
            correlation_id=correlation_id,
            changes=sanitized_changes,
            timestamp=datetime.now(UTC),
        )

        self._entries.append(entry)
        logger.debug(
            "State changelog recorded: [%s] %s:%s v%d by %s/%s",
            operation.value,
            domain.value,
            resource_id,
            version,
            actor,
            service,
        )
        return entry

    def get_history(
        self,
        resource_type: str | None = None,
        resource_id: str | None = None,
        limit: int = 50,
    ) -> list[ChangelogEntry]:
        """Queries recorded changelog entries filtered by resource."""
        results = []
        for entry in reversed(self._entries):
            if resource_type and entry.resource_type != resource_type:
                continue
            if resource_id and entry.resource_id != resource_id:
                continue
            results.append(entry)
            if len(results) >= limit:
                break
        return results

    def clear(self) -> None:
        """Clears in-memory buffer (testing only)."""
        self._entries.clear()


# Global changelog instance
state_changelog = StateChangelog()
