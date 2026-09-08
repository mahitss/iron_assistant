"""Tests for user proactive settings, category toggles, priority filters, and quiet hours."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base
from app.proactive.models import UserProactiveSettings
from app.proactive.notifier import NotificationService
from app.proactive.schemas import UserProactiveSettingsUpdate
from app.proactive.service import ProactiveService
from app.proactive.state import InsightPriority, InsightStatus, SourceType


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
async def test_proactive_disabled_by_user_except_security(db_session: AsyncSession):
    """When user disables proactive intelligence, routine events are suppressed but CRITICAL security events pass."""
    user_id = "user_pref_1"
    await ProactiveService.update_settings(
        db_session,
        user_id,
        UserProactiveSettingsUpdate(proactive_enabled=False),
    )

    # 1. Normal workflow failure should be suppressed
    normal = await ProactiveService.process_event(
        db_session=db_session,
        user_id=user_id,
        source_type=SourceType.WORKFLOW,
        category="workflow.failed",
        payload={"error": "db timeout"},
    )
    assert normal is None

    # 2. Critical security emergency stop MUST still be created
    sec = await ProactiveService.process_event(
        db_session=db_session,
        user_id=user_id,
        source_type=SourceType.SECURITY,
        category="security.emergency_stop",
        payload={"reason": "Compromise detected"},
    )
    assert sec is not None
    assert sec.priority == InsightPriority.CRITICAL


@pytest.mark.asyncio
async def test_category_toggle_suppression(db_session: AsyncSession):
    """User can disable specific event categories like workflow failures or web change notifications."""
    user_id = "user_pref_2"
    await ProactiveService.update_settings(
        db_session,
        user_id,
        UserProactiveSettingsUpdate(notify_on_workflow_failure=False),
    )

    insight = await ProactiveService.process_event(
        db_session=db_session,
        user_id=user_id,
        source_type=SourceType.WORKFLOW,
        category="workflow.failed",
        payload={"error": "fail"},
    )
    assert insight is None


@pytest.mark.asyncio
async def test_minimum_priority_filtering(db_session: AsyncSession):
    """Setting minimum priority to HIGH filters out LOW and MEDIUM insights."""
    user_id = "user_pref_3"
    await ProactiveService.update_settings(
        db_session,
        user_id,
        UserProactiveSettingsUpdate(minimum_priority="HIGH"),
    )

    # Medium web change should be filtered
    med = await ProactiveService.process_event(
        db_session=db_session,
        user_id=user_id,
        source_type=SourceType.WEB_MONITOR,
        category="web_monitor.changed",
        payload={"url": "https://example.com"},
    )
    assert med is None

    # High priority approval should pass
    high = await ProactiveService.process_event(
        db_session=db_session,
        user_id=user_id,
        source_type=SourceType.APPROVAL,
        category="approval.required",
        payload={"tool_name": "rm_file"},
    )
    assert high is not None
    assert high.priority == InsightPriority.HIGH


def test_quiet_hours_calculation():
    """Verify quiet hours detection across overnight windows."""
    settings = UserProactiveSettings(
        user_id="user_qh",
        quiet_hours_enabled=True,
        quiet_hours_start="22:00",
        quiet_hours_end="08:00",
        timezone="UTC",
    )

    # 23:30 UTC -> inside quiet hours
    dt_night = datetime(2026, 9, 8, 23, 30, tzinfo=UTC)
    assert NotificationService.is_in_quiet_hours(settings, dt_night) is True

    # 04:15 UTC -> inside quiet hours
    dt_early = datetime(2026, 9, 8, 4, 15, tzinfo=UTC)
    assert NotificationService.is_in_quiet_hours(settings, dt_early) is True

    # 14:00 UTC -> outside quiet hours
    dt_day = datetime(2026, 9, 8, 14, 0, tzinfo=UTC)
    assert NotificationService.is_in_quiet_hours(settings, dt_day) is False


@pytest.mark.asyncio
async def test_quiet_hours_delays_low_medium(db_session: AsyncSession):
    """During quiet hours, LOW and MEDIUM insights are stored as NEW without active delivery."""
    user_id = "user_qh_delivery"
    now_utc = datetime.now(UTC)
    # Configure quiet hours that actively cover the current time
    curr_hour = now_utc.hour
    start_str = f"{(curr_hour - 1) % 24:02d}:00"
    end_str = f"{(curr_hour + 2) % 24:02d}:00"

    await ProactiveService.update_settings(
        db_session,
        user_id,
        UserProactiveSettingsUpdate(
            quiet_hours_enabled=True,
            quiet_hours_start=start_str,
            quiet_hours_end=end_str,
            timezone="UTC",
        ),
    )

    # MEDIUM web change -> status should be 'new' (held)
    item = await ProactiveService.process_event(
        db_session=db_session,
        user_id=user_id,
        source_type=SourceType.WEB_MONITOR,
        category="web_monitor.changed",
        payload={"url": "https://example.com/test"},
    )
    assert item is not None
    assert item.status == InsightStatus.NEW
