"""Dead Letter Queue and Manager for Kairo Unified Event Bus.

Captures exhausted retries and permanent failures with sanitized payloads,
and enforces strict replay-safety guardrails.
"""

from __future__ import annotations

import logging
import traceback
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.events.db import get_event_db_session
from app.events.models import DeadLetterEventRecord
from app.events.registry import event_registry
from app.events.safety import EventSecurityGuard
from app.events.schemas import Event, ReplaySafety

logger = logging.getLogger(__name__)


class DeadLetterManager:
    """Manages dead-lettered events and enforces replay-safety rules."""

    def __init__(self) -> None:
        self._in_memory_records: Dict[str, Dict[str, Any]] = {}

    async def record_failure(
        self,
        event: Event,
        subscriber_name: str,
        error: Exception,
        retry_count: int = 0,
        first_attempt_at: Optional[datetime] = None,
        db_session: Optional[AsyncSession] = None,
    ) -> str:
        """Record a failed event delivery to dead letter storage with sanitized traces."""
        dead_letter_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        first_attempt = first_attempt_at or now

        # Format and sanitize error trace
        raw_tb = traceback.format_exc()
        sanitized_tb = EventSecurityGuard.sanitize_payload({"trace": raw_tb}).get("trace", "")
        error_msg = EventSecurityGuard.sanitize_payload({"msg": str(error)}).get("msg", str(error))

        sanitized_payload = EventSecurityGuard.sanitize_payload(event.payload or {})

        record_data = {
            "id": dead_letter_id,
            "event_id": event.event_id,
            "event_type": event.event_type,
            "subscriber_name": subscriber_name,
            "failure_reason": error_msg,
            "error_traceback": sanitized_tb,
            "retry_count": retry_count,
            "first_attempt_at": first_attempt,
            "failed_at": now,
            "event_payload": sanitized_payload,
            "status": "UNRESOLVED",
            "replayed_at": None,
        }

        # Store in-memory for resilience
        self._in_memory_records[dead_letter_id] = record_data

        # Persist to database if possible
        if db_session is not None:
            try:
                db_record = DeadLetterEventRecord(**record_data)
                db_session.add(db_record)
                await db_session.commit()
            except Exception as db_err:
                logger.warning("Failed to commit dead letter record to database: %s", db_err)
        else:
            try:
                async with get_event_db_session() as session:
                    if session is not None:
                        db_record = DeadLetterEventRecord(**record_data)
                        session.add(db_record)
                        await session.commit()
            except Exception as db_err:
                logger.warning("Failed to commit dead letter record to database: %s", db_err)

        logger.error(
            "Dead letter recorded for event '%s' (type: %s) by subscriber '%s'. ID: %s. Reason: %s",
            event.event_id,
            event.event_type,
            subscriber_name,
            dead_letter_id,
            error_msg,
        )
        return dead_letter_id

    async def get_dead_letter(self, dead_letter_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve dead letter record by ID."""
        try:
            async with get_event_db_session() as session:
                if session is not None:
                    query = select(DeadLetterEventRecord).where(DeadLetterEventRecord.id == dead_letter_id)
                    res = await session.execute(query)
                    record = res.scalar_one_or_none()
                    if record:
                        return {
                            "id": record.id,
                            "event_id": record.event_id,
                            "event_type": record.event_type,
                            "subscriber_name": record.subscriber_name,
                            "failure_reason": record.failure_reason,
                            "error_traceback": record.error_traceback,
                            "retry_count": record.retry_count,
                            "first_attempt_at": record.first_attempt_at,
                            "failed_at": record.failed_at,
                            "event_payload": record.event_payload,
                            "status": record.status,
                            "replayed_at": record.replayed_at,
                        }
        except Exception as err:
            logger.debug("Database fetch failed for dead letter %s: %s", dead_letter_id, err)

        return self._in_memory_records.get(dead_letter_id)

    async def list_dead_letters(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List dead letters with pagination and status filter."""
        results: List[Dict[str, Any]] = []
        try:
            async with get_event_db_session() as session:
                if session is not None:
                    query = select(DeadLetterEventRecord)
                    if status:
                        query = query.where(DeadLetterEventRecord.status == status)
                    query = query.order_by(desc(DeadLetterEventRecord.failed_at)).limit(limit).offset(offset)
                    res = await session.execute(query)
                    records = res.scalars().all()
                    for r in records:
                        results.append({
                            "id": r.id,
                            "event_id": r.event_id,
                            "event_type": r.event_type,
                            "subscriber_name": r.subscriber_name,
                            "failure_reason": r.failure_reason,
                            "retry_count": r.retry_count,
                            "failed_at": r.failed_at.isoformat() if r.failed_at else None,
                            "status": r.status,
                            "event_payload": r.event_payload,
                        })
                    return results
        except Exception as err:
            logger.debug("Database list failed for dead letters: %s", err)

        # Fallback to in-memory records
        records_list = list(self._in_memory_records.values())
        if status:
            records_list = [r for r in records_list if r["status"] == status]
        records_list.sort(key=lambda r: r["failed_at"], reverse=True)
        return records_list[offset : offset + limit]

    async def replay_dead_letter(
        self,
        dead_letter_id: str,
        event_bus: Any,
        reviewed_by: Optional[str] = None,
        force: bool = False,
    ) -> bool:
        """Replay a dead-lettered event with strict safety checks.

        Raises:
            KeyError: if dead_letter_id not found
            PermissionError: if event type is NON_REPLAYABLE
            ValueError: if event requires review but force/reviewed_by not provided
        """
        record = await self.get_dead_letter(dead_letter_id)
        if not record:
            raise KeyError(f"Dead letter record not found: {dead_letter_id}")

        event_type = record["event_type"]
        definition = event_registry.get(event_type)
        replay_safety = definition.replay_safety if definition else ReplaySafety.REPLAY_REQUIRES_REVIEW

        # CRITICAL REPLAY SAFETY GUARD
        if replay_safety == ReplaySafety.NON_REPLAYABLE:
            logger.error(
                "Blocked replay of NON_REPLAYABLE event '%s' from dead letter %s",
                event_type,
                dead_letter_id,
            )
            raise PermissionError(
                f"Event type '{event_type}' is classified as NON_REPLAYABLE. Replaying this side-effecting event is strictly forbidden."
            )

        if replay_safety == ReplaySafety.REPLAY_REQUIRES_REVIEW and not (force or reviewed_by):
            raise ValueError(
                f"Event type '{event_type}' requires explicit human review before replay. Pass reviewed_by or force=True."
            )

        # Construct replayable canonical Event
        event_data = {
            "event_id": f"replay_{record['event_id']}_{uuid.uuid4().hex[:6]}",
            "event_type": event_type,
            "event_version": definition.version if definition else "1.0.0",
            "timestamp": datetime.now(timezone.utc),
            "source": "dead_letter_replay",
            "correlation_id": record.get("event_id"),
            "causation_id": dead_letter_id,
            "payload": record.get("event_payload") or {},
            "metadata": {
                "is_replay": True,
                "original_dead_letter_id": dead_letter_id,
                "reviewed_by": reviewed_by,
            },
        }
        event = Event(**event_data)

        # Dispatch via event bus
        await event_bus.publish(event)

        # Update dead letter status
        now = datetime.now(timezone.utc)
        record["status"] = "REPLAYED"
        record["replayed_at"] = now
        self._in_memory_records[dead_letter_id] = record

        try:
            async with get_event_db_session() as session:
                if session is not None:
                    stmt = (
                        update(DeadLetterEventRecord)
                        .where(DeadLetterEventRecord.id == dead_letter_id)
                        .values(status="REPLAYED", replayed_at=now)
                    )
                    await session.execute(stmt)
                    await session.commit()
        except Exception as db_err:
            logger.warning("Failed to update dead letter status in database: %s", db_err)

        logger.info("Successfully replayed dead letter %s (event: %s)", dead_letter_id, event_type)
        return True

    async def discard_dead_letter(self, dead_letter_id: str, reason: Optional[str] = None) -> bool:
        """Mark dead letter as discarded without replaying."""
        record = await self.get_dead_letter(dead_letter_id)
        if not record:
            raise KeyError(f"Dead letter record not found: {dead_letter_id}")

        record["status"] = "DISCARDED"
        self._in_memory_records[dead_letter_id] = record

        try:
            async with get_event_db_session() as session:
                if session is not None:
                    stmt = (
                        update(DeadLetterEventRecord)
                        .where(DeadLetterEventRecord.id == dead_letter_id)
                        .values(status="DISCARDED")
                    )
                    await session.execute(stmt)
                    await session.commit()
        except Exception as db_err:
            logger.warning("Failed to mark dead letter discarded in database: %s", db_err)

        logger.info("Discarded dead letter %s (reason: %s)", dead_letter_id, reason)
        return True


dead_letter_manager = DeadLetterManager()
