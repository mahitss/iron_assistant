"""Event Publisher with security authority verification, trace sanitization, and lineage tracking.

Ensures that model outputs or untrusted sources can NEVER forge privileged security events,
and redacts sensitive credentials from all event payloads before publication.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.events.db import get_event_db_session
from app.events.models import EventRecord
from app.events.metrics import event_metrics
from app.events.registry import event_registry
from app.events.safety import EventSecurityGuard
from app.events.schemas import Event, EventSource

logger = logging.getLogger(__name__)


class EventPublisher:
    """Security-hardened event publisher."""

    def __init__(self, bus: Any = None) -> None:
        self.bus = bus

    def create_event(
        self,
        event_type: str,
        source: str,
        payload: Dict[str, Any],
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        causation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Event:
        """Constructs a canonical Event with lineage and default versioning."""
        definition = event_registry.get(event_type)
        version = definition.version if definition else "1.0.0"

        event = Event(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            event_version=version,
            timestamp=datetime.now(timezone.utc),
            source=source,
            user_id=user_id,
            project_id=project_id,
            correlation_id=correlation_id or str(uuid.uuid4()),
            causation_id=causation_id,
            payload=payload,
            metadata=metadata or {},
        )
        return event

    async def publish(
        self,
        event: Event,
        persist_log: bool = True,
    ) -> Event:
        """Sanitizes, authorizes, metrics-records, persists, and publishes an event to the bus.

        Raises:
            PermissionError: if an unauthorized source attempts to publish a privileged event.
        """
        # 1. SECURITY AUTHORITY ENFORCEMENT
        EventSecurityGuard.validate_publication_authority(event.event_type, event.source)

        # 2. ZERO-SECRET SANITIZATION
        sanitized_event = EventSecurityGuard.sanitize_event(event)

        # 3. METRICS RECORDING
        await event_metrics.record_published(sanitized_event.event_type, sanitized_event.source)

        # 4. AUDIT & EVENT LOG PERSISTENCE (Best-effort non-blocking)
        if persist_log:
            try:
                async with get_event_db_session() as session:
                    if session is not None:
                        db_record = EventRecord(
                            id=sanitized_event.event_id,
                            event_type=sanitized_event.event_type,
                            event_version=sanitized_event.event_version,
                            timestamp=sanitized_event.timestamp,
                            source=sanitized_event.source,
                            user_id=sanitized_event.user_id,
                            project_id=sanitized_event.project_id,
                            correlation_id=sanitized_event.correlation_id,
                            causation_id=sanitized_event.causation_id,
                            payload_json=sanitized_event.payload,
                            metadata_json=sanitized_event.metadata,
                        )
                        session.add(db_record)
                        await session.commit()
            except Exception as db_err:
                logger.debug("Non-fatal: could not persist event log to DB: %s", db_err)

        # 5. DISPATCH TO BUS
        if self.bus is not None:
            await self.bus.dispatch(sanitized_event)

        return sanitized_event
