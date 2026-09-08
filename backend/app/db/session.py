"""Database connection and async session management for Kairo."""

import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

logger = logging.getLogger("kairo.db")


class Base(DeclarativeBase):
    """Base declarative class for all Kairo database models."""


_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine | None:
    """Retrieve or initialize the SQLAlchemy async engine."""
    global _engine
    if _engine is not None:
        return _engine

    settings = get_settings()
    if not settings.DATABASE_URL:
        logger.info("DATABASE_URL is not configured; relational database is inactive.")
        return None

    try:
        # Convert any postgres:// to postgresql+asyncpg:// if needed
        db_url = settings.DATABASE_URL
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+asyncpg://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        _engine = create_async_engine(
            db_url,
            echo=settings.DEBUG and False,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
        return _engine
    except Exception as exc:
        logger.warning("Failed to initialize database engine: %s", exc)
        return None


def get_sessionmaker() -> async_sessionmaker[AsyncSession] | None:
    """Retrieve or initialize the async session maker."""
    global _sessionmaker
    if _sessionmaker is not None:
        return _sessionmaker

    engine = get_engine()
    if engine is None:
        return None

    _sessionmaker = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    return _sessionmaker


async def get_db_session() -> AsyncGenerator[AsyncSession | None, None]:
    """Dependency / generator yielding an active async database session."""
    session_factory = get_sessionmaker()
    if session_factory is None:
        yield None
        return

    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def reset_db_engine() -> None:
    """Reset global engine and sessionmaker (used for testing)."""
    global _engine, _sessionmaker
    _engine = None
    _sessionmaker = None
