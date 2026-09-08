"""Unit tests for SchedulerService polling, idempotency, and stale run recovery."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.automation.models import Workflow, WorkflowRun
from app.automation.scheduler import SchedulerService
from app.core.config import Settings
from app.db.session import Base


@pytest.fixture
async def async_db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_scheduler_polls_due_and_ignores_future_and_disabled(async_db_session: AsyncSession):
    """Verify scheduler selects due workflows and skips disabled or future ones."""
    now = datetime.now(UTC)
    settings = Settings(KAIRO_AUTOMATION_ENABLED=True, KAIRO_MIN_SCHEDULE_INTERVAL_SECONDS=60)
    scheduler = SchedulerService(settings=settings)

    # 1. Due enabled workflow
    due_wf = Workflow(
        user_id="user_1",
        name="Due Workflow",
        enabled=True,
        trigger_type="schedule",
        trigger_config={"interval": "hourly", "timezone": "UTC"},
        action_config={},
        created_at=now - timedelta(hours=2),
        updated_at=now - timedelta(hours=2),
        next_run_at=now - timedelta(minutes=5),  # in the past -> due!
    )
    # 2. Future enabled workflow
    future_wf = Workflow(
        user_id="user_1",
        name="Future Workflow",
        enabled=True,
        trigger_type="schedule",
        trigger_config={"interval": "hourly", "timezone": "UTC"},
        action_config={},
        created_at=now,
        updated_at=now,
        next_run_at=now + timedelta(hours=1),
    )
    # 3. Due but DISABLED workflow
    disabled_wf = Workflow(
        user_id="user_1",
        name="Disabled Workflow",
        enabled=False,
        trigger_type="schedule",
        trigger_config={"interval": "hourly", "timezone": "UTC"},
        action_config={},
        created_at=now - timedelta(hours=2),
        updated_at=now - timedelta(hours=2),
        next_run_at=now - timedelta(minutes=5),
    )
    async_db_session.add_all([due_wf, future_wf, disabled_wf])
    await async_db_session.commit()

    created_runs = await scheduler.poll_due_workflows(async_db_session)
    assert len(created_runs) == 1

    # Verify due_wf next_run_at was advanced
    await async_db_session.refresh(due_wf)
    assert due_wf.next_run_at is not None
    next_run = (
        due_wf.next_run_at
        if due_wf.next_run_at.tzinfo is not None
        else due_wf.next_run_at.replace(tzinfo=UTC)
    )
    assert next_run > now
    assert due_wf.last_run_at is not None


@pytest.mark.asyncio
async def test_scheduler_idempotency_prevents_duplicate_runs(async_db_session: AsyncSession):
    """Verify polling twice on the same schedule timestamp does not create duplicate runs."""
    now = datetime.now(UTC)
    settings = Settings(KAIRO_AUTOMATION_ENABLED=True, KAIRO_MIN_SCHEDULE_INTERVAL_SECONDS=60)
    scheduler = SchedulerService(settings=settings)

    original_due = now - timedelta(minutes=1)
    wf = Workflow(
        user_id="user_1",
        name="Idempotent Due Workflow",
        enabled=True,
        trigger_type="schedule",
        trigger_config={"interval": "daily", "time": "08:00", "timezone": "UTC"},
        action_config={},
        created_at=now,
        updated_at=now,
        next_run_at=original_due,
    )
    async_db_session.add(wf)
    await async_db_session.commit()

    # First poll creates run
    runs1 = await scheduler.poll_due_workflows(async_db_session)
    assert len(runs1) == 1

    # Force next_run_at back to the past with same schedule timestamp to simulate race/duplicate poll
    wf.next_run_at = original_due
    await async_db_session.commit()

    runs2 = await scheduler.poll_due_workflows(async_db_session)
    assert len(runs2) == 0  # Duplicate run prevented!


@pytest.mark.asyncio
async def test_scheduler_recovers_stale_runs(async_db_session: AsyncSession):
    """Verify runs stuck in 'running' beyond timeout are marked as failed."""
    now = datetime.now(UTC)
    settings = Settings(KAIRO_AUTOMATION_ENABLED=True, KAIRO_WORKFLOW_TIMEOUT_SECONDS=60)
    scheduler = SchedulerService(settings=settings)

    wf = Workflow(
        user_id="user_1",
        name="Stale Run Test",
        enabled=True,
        trigger_type="manual",
        trigger_config={},
        action_config={},
        created_at=now,
        updated_at=now,
    )
    async_db_session.add(wf)
    await async_db_session.commit()

    stale_run = WorkflowRun(
        workflow_id=wf.id,
        user_id="user_1",
        status="running",
        idempotency_key="stale_run_1",
        started_at=now - timedelta(seconds=120),  # 2 minutes ago (> 60s timeout)
        created_at=now - timedelta(seconds=120),
        updated_at=now - timedelta(seconds=120),
    )
    async_db_session.add(stale_run)
    await async_db_session.commit()

    recovered = await scheduler.recover_stale_runs(async_db_session)
    assert recovered == 1

    await async_db_session.refresh(stale_run)
    assert stale_run.status == "failed"
    assert "timed out" in stale_run.error.lower()
