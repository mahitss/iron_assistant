"""Transactional boundary coordinator for state changes and outbox event staging (Task 39, Spec 18-21)."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_sessionmaker
from app.events.outbox import TransactionalOutbox
from app.events.schemas import Event

logger = logging.getLogger("kairo.state.transactions")


class StateTransactionManager:
    """Coordinates atomic database transactions combining state mutation, changelog, and outbox."""

    @classmethod
    @asynccontextmanager
    async def transaction(cls, session: AsyncSession | None = None) -> AsyncGenerator[AsyncSession, None]:
        """Provides an atomic transaction context.
        
        If a session is passed in, uses the existing transaction.
        Otherwise creates a new session and manages commit/rollback.
        """
        if session is not None:
            yield session
            return

        factory = get_sessionmaker()
        if factory is None:
            # Running without persistent DB (in-memory test mode)
            yield None  # type: ignore
            return

        async with factory() as new_session:
            try:
                yield new_session
                await new_session.commit()
            except Exception as exc:
                await new_session.rollback()
                logger.error("State transaction aborted due to error: %s", exc)
                raise

    @classmethod
    async def stage_outbox_event(
        cls,
        session: AsyncSession | None,
        event: Event,
    ) -> None:
        """Atomically stages an event into the transactional outbox table if a session is active."""
        if session is not None:
            await TransactionalOutbox.stage_event(session, event)
            logger.debug("Staged outbox event %s (%s)", event.event_id, event.event_type)
