"""Unit tests for Automation SQLAlchemy models and entity relationships."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.automation.models import (
    ApprovalRequest,
    Workflow,
    WorkflowRun,
    WorkflowStep,
)
from app.db.session import Base


@pytest.fixture
async def async_db_session():
    """Isolated in-memory SQLite database session for unit tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_workflow_lifecycle_and_relationships(async_db_session: AsyncSession):
    """Verify creating a workflow, run, step, and cascading delete."""
    now = datetime.now(UTC)

    # 1. Create Workflow
    wf = Workflow(
        user_id="user_123",
        name="Daily CI Check",
        description="Inspects GitHub CI status every morning",
        enabled=True,
        trigger_type="schedule",
        trigger_config={"interval": "daily", "time": "08:00", "timezone": "UTC"},
        action_config={"steps": [{"type": "action", "config": {"tool": "datetime", "arguments": {}}}]},
        created_at=now,
        updated_at=now,
        next_run_at=now + timedelta(days=1),
    )
    async_db_session.add(wf)
    await async_db_session.commit()
    await async_db_session.refresh(wf)

    assert wf.id is not None
    assert wf.version == 1

    # 2. Create WorkflowRun
    run = WorkflowRun(
        workflow_id=wf.id,
        user_id=wf.user_id,
        status="pending",
        idempotency_key=f"manual_{wf.id}_test1",
        created_at=now,
        updated_at=now,
    )
    async_db_session.add(run)
    await async_db_session.commit()
    await async_db_session.refresh(run)

    assert run.id is not None
    assert run.workflow_id == wf.id

    # 3. Create WorkflowStep
    step = WorkflowStep(
        run_id=run.id,
        step_index=0,
        step_type="action",
        configuration={"tool": "datetime"},
        status="pending",
    )
    async_db_session.add(step)
    await async_db_session.commit()
    await async_db_session.refresh(step)

    assert step.id is not None
    assert step.step_index == 0

    # 4. Create ApprovalRequest
    approval = ApprovalRequest(
        user_id=wf.user_id,
        run_id=run.id,
        step_id=step.id,
        tool_name="git_push",
        tool_args={},
        permission_level="EXTERNAL",
        status="pending",
        created_at=now,
        expires_at=now + timedelta(seconds=30),
    )
    async_db_session.add(approval)
    await async_db_session.commit()
    await async_db_session.refresh(approval)

    assert approval.id is not None

    # 5. Cascading deletion of workflow deletes runs, steps, and approvals
    await async_db_session.delete(wf)
    await async_db_session.commit()

    runs_stmt = select(WorkflowRun).where(WorkflowRun.workflow_id == wf.id)
    res_runs = await async_db_session.execute(runs_stmt)
    assert res_runs.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_idempotency_key_unique_constraint(async_db_session: AsyncSession):
    """Verify that duplicate idempotency keys raise IntegrityError."""
    now = datetime.now(UTC)
    wf = Workflow(
        user_id="user_test",
        name="Idempotency Test",
        trigger_type="manual",
        trigger_config={},
        action_config={},
        created_at=now,
        updated_at=now,
    )
    async_db_session.add(wf)
    await async_db_session.commit()

    run1 = WorkflowRun(
        workflow_id=wf.id,
        user_id="user_test",
        status="pending",
        idempotency_key="unique_key_12345",
        created_at=now,
        updated_at=now,
    )
    async_db_session.add(run1)
    await async_db_session.commit()

    # Attempt inserting identical idempotency key
    run2 = WorkflowRun(
        workflow_id=wf.id,
        user_id="user_test",
        status="pending",
        idempotency_key="unique_key_12345",
        created_at=now,
        updated_at=now,
    )
    async_db_session.add(run2)
    with pytest.raises(IntegrityError):
        await async_db_session.commit()
