"""Database session helper for Kairo Event Bus."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_sessionmaker


@asynccontextmanager
async def get_event_db_session() -> AsyncGenerator[Optional[AsyncSession], None]:
    """Provides an async database session if configured, or None if database is inactive."""
    maker = get_sessionmaker()
    if maker is None:
        yield None
        return

    async with maker() as session:
        yield session
