"""Resilient Outbox Bridge coordinating atomic state transitions with the transactional outbox."""

import logging
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.events.outbox import transactional_outbox
from app.events.schemas import Event
from app.resilience.schemas import utc_now

logger = logging.getLogger(__name__)


class OutboxBridge:
    """Bridges resilience events (recovery, checkpoints, circuit status) to the transactional outbox."""

    @staticmethod
    async def stage_resilience_event(
        session: AsyncSession,
        event_type: str,
        task_id: str,
        payload: dict[str, Any],
        user_id: str | None = None,
    ) -> None:
        """Atomically stages a resilience event within the active DB session transaction."""
        try:
            event = Event(
                event_type=event_type,
                source="resilience_runtime",
                data={
                    "task_id": task_id,
                    "user_id": user_id,
                    "timestamp": utc_now().isoformat(),
                    **payload,
                },
            )
            await transactional_outbox.stage_event(session, event)
            logger.debug("Resilience: Staged transactional outbox event '%s' for task '%s'", event_type, task_id)
        except Exception as exc:
            logger.error("Resilience: Failed to stage event '%s' to outbox: %s", event_type, exc)
            # Re-raise to ensure transaction rollback if atomic event staging is mandatory
            raise
