"""Transactional Outbox pattern for Kairo Unified Event Bus.

Ensures atomic persistence of state changes and event records within the same
database transaction, with an OutboxProcessor publishing pending events.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import asc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.events.bus import event_bus
from app.events.db import get_event_db_session
from app.events.dead_letter import dead_letter_manager
from app.events.models import EventOutboxRecord
from app.events.schemas import Event

logger = logging.getLogger(__name__)


class TransactionalOutbox:
    """Helper to stage events inside an active database transaction."""

    @staticmethod
    async def stage_event(
        session: AsyncSession,
        event: Event,
    ) -> EventOutboxRecord:
        """Stage an event in the outbox table within the caller's active database transaction."""
        event_dict = event.model_dump(mode="json")
        record = EventOutboxRecord(
            id=str(uuid.uuid4()),
            event_id=event.event_id,
            event_type=event.event_type,
            status="PENDING",
            event_data_json=event_dict,
            created_at=event.timestamp or datetime.now(timezone.utc),
            attempts=0,
        )
        session.add(record)
        return record


class OutboxProcessor:
    """Polls outbox table and publishes pending events to the EventBus."""

    def __init__(self, bus: Any = None, poll_interval: Optional[float] = None) -> None:
        self.bus = bus or event_bus
        self.poll_interval = (
            poll_interval
            if poll_interval is not None
            else getattr(settings, "KAIRO_EVENTS_OUTBOX_POLL_INTERVAL_SECONDS", 2.0)
        )
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def process_batch(self, limit: int = 50) -> int:
        """Poll and publish up to `limit` pending outbox records.

        Returns number of successfully published events.
        """
        published_count = 0

        try:
            async with get_event_db_session() as session:
                if session is None:
                    return 0

                query = (
                    select(EventOutboxRecord)
                    .where(EventOutboxRecord.status == "PENDING")
                    .order_by(asc(EventOutboxRecord.created_at))
                    .limit(limit)
                )
                res = await session.execute(query)
                records: List[EventOutboxRecord] = res.scalars().all()

                if not records:
                    return 0

                for record in records:
                    try:
                        # Reconstruct canonical Event
                        event = Event.model_validate(record.event_data_json)

                        # Publish to event bus without duplicate event log save
                        await self.bus.publish(event, persist_log=False)

                        # Mark outbox record published
                        record.status = "PUBLISHED"
                        record.published_at = datetime.now(timezone.utc)
                        published_count += 1
                    except Exception as err:
                        logger.error("Outbox publish error for record %s: %s", record.id, err)
                        record.attempts += 1
                        record.last_error = str(err)
                        if record.attempts >= 3:
                            record.status = "FAILED"
                            # Send to dead letter
                            try:
                                await dead_letter_manager.record_failure(
                                    event=event,
                                    subscriber_name="outbox_processor",
                                    error=err,
                                    retry_count=record.attempts,
                                    db_session=session,
                                )
                            except Exception as dl_err:
                                logger.critical("Failed to dead-letter outbox event: %s", dl_err)

                await session.commit()
        except Exception as batch_err:
            logger.debug("Outbox batch process error: %s", batch_err)

        return published_count

    async def _loop(self) -> None:
        logger.info("Outbox processor loop started (poll interval: %.1fs)", self.poll_interval)
        while self._running:
            try:
                await self.process_batch()
            except Exception as err:
                logger.error("Outbox processing error: %s", err)

            try:
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break
        logger.info("Outbox processor loop stopped.")

    async def start(self) -> None:
        """Start the background outbox polling task."""
        async with self._lock:
            if self._running:
                return
            self._running = True
            self._task = asyncio.create_task(self._loop(), name="outbox-processor")

    async def stop(self) -> None:
        """Stop background outbox polling."""
        async with self._lock:
            if not self._running:
                return
            self._running = False
            if self._task:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
                self._task = None


outbox_processor = OutboxProcessor()
transactional_outbox = TransactionalOutbox()
