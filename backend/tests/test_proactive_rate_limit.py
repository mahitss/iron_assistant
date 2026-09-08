"""Tests for proactive notification rate limiting and high-priority preservation."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base
from app.proactive.models import ProactiveInsight
from app.proactive.notifier import NotificationService
from app.proactive.state import InsightPriority, InsightStatus


@pytest.fixture
async def db_session():
    """Create in-memory SQLite database session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_rate_limit_suppresses_low_preserves_high(db_session: AsyncSession):
    """When the 20 notifications/hour limit is exceeded, LOW/MEDIUM are suppressed, but HIGH/CRITICAL pass."""
    user_id = "user_rate_limit"
    now = datetime.now(UTC)

    # Populate 25 recent notifications (exceeding 20/hr limit)
    for i in range(25):
        insight = ProactiveInsight(
            user_id=user_id,
            source_type="WORKFLOW",
            title=f"Notification {i}",
            summary=f"Summary {i}",
            priority=InsightPriority.LOW,
            status=InsightStatus.DELIVERED,
            fingerprint=f"fp_rl_{i}",
            created_at=now,
        )
        db_session.add(insight)
    await db_session.commit()

    # LOW priority -> Suppressed by rate limit
    low_allowed = await NotificationService.check_rate_limit(user_id, InsightPriority.LOW, db_session)
    assert low_allowed is False

    # MEDIUM priority -> Suppressed by rate limit
    med_allowed = await NotificationService.check_rate_limit(user_id, InsightPriority.MEDIUM, db_session)
    assert med_allowed is False

    # HIGH priority -> PRESERVED!
    high_allowed = await NotificationService.check_rate_limit(user_id, InsightPriority.HIGH, db_session)
    assert high_allowed is True

    # CRITICAL priority -> PRESERVED!
    crit_allowed = await NotificationService.check_rate_limit(user_id, InsightPriority.CRITICAL, db_session)
    assert crit_allowed is True
