"""Tests for insight deduplication and state cooldown transitions."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base
from app.proactive.cooldown import CooldownTracker
from app.proactive.deduplicator import InsightDeduplicator
from app.proactive.models import ProactiveInsight
from app.proactive.schemas import CandidateInsight
from app.proactive.state import InsightPriority, SourceType


@pytest.fixture
async def db_session():
    """Create in-memory SQLite database session for unit tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_fingerprint_deduplication(db_session: AsyncSession):
    """Identical insights within deduplication window must be suppressed."""
    candidate = CandidateInsight(
        user_id="user_dedup",
        source_type=SourceType.GITHUB,
        source_id="repo_1",
        category="github.ci.failed",
        title="CI Failed",
        summary="Build failed",
        priority=InsightPriority.HIGH,
    )
    fp = InsightDeduplicator.compute_fingerprint(candidate)
    assert len(fp) == 64

    # Before insertion, not a duplicate
    is_dup = await InsightDeduplicator.is_duplicate(candidate, fp, db_session)
    assert not is_dup

    # Insert insight
    insight = ProactiveInsight(
        user_id="user_dedup",
        source_type=str(SourceType.GITHUB),
        source_id="repo_1",
        title="CI Failed",
        summary="Build failed",
        priority=InsightPriority.HIGH,
        fingerprint=fp,
        status="delivered",
    )
    db_session.add(insight)
    await db_session.commit()

    # After insertion, must be recognized as duplicate
    is_dup_now = await InsightDeduplicator.is_duplicate(candidate, fp, db_session)
    assert is_dup_now


@pytest.mark.asyncio
async def test_cooldown_condition_transitions():
    """Monitored states suppress notifications until a condition transition occurs."""
    CooldownTracker.reset_local_cache()

    user_id = "user_cooldown"
    source_type = "SERVICE_CHECK"
    source_id = "api_gateway"
    state_key = "health"

    # 1. First failure: UP -> DOWN: Should notify!
    alert1 = await CooldownTracker.should_notify_transition(
        user_id=user_id,
        source_type=source_type,
        source_id=source_id,
        state_key=state_key,
        current_state_value="DOWN",
    )
    assert alert1 is True

    # 2. 5 minutes later, still DOWN: Unchanged state in cooldown -> Suppress!
    alert2 = await CooldownTracker.should_notify_transition(
        user_id=user_id,
        source_type=source_type,
        source_id=source_id,
        state_key=state_key,
        current_state_value="DOWN",
    )
    assert alert2 is False

    # 3. State recovers: DOWN -> UP: Transition detected -> Should notify!
    alert3 = await CooldownTracker.should_notify_transition(
        user_id=user_id,
        source_type=source_type,
        source_id=source_id,
        state_key=state_key,
        current_state_value="UP",
    )
    assert alert3 is True
