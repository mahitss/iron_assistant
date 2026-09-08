"""Unit tests for WorkflowExecutor step execution, conditions, and approvals."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.automation.actions import ActionExecutionResult, WorkflowActionRunner
from app.automation.executor import WorkflowExecutor
from app.automation.models import Notification, Workflow, WorkflowRun
from app.automation.state import WorkflowStatus
from app.db.session import Base
from app.tools.permissions import PermissionLevel


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
async def test_executor_runs_action_and_notification_steps(async_db_session: AsyncSession):
    """Verify executing a workflow with datetime action step and notification step."""
    now = datetime.now(UTC)
    wf = Workflow(
        user_id="user_test",
        name="Clock and Notify",
        enabled=True,
        trigger_type="manual",
        trigger_config={},
        action_config={
            "steps": [
                {
                    "type": "action",
                    "config": {"tool": "datetime", "arguments": {}},
                },
                {
                    "type": "notification",
                    "config": {
                        "title": "Time Check Completed",
                        "message": "Current time successfully fetched.",
                        "level": "info",
                    },
                },
            ]
        },
        created_at=now,
        updated_at=now,
    )
    async_db_session.add(wf)
    await async_db_session.commit()

    run = WorkflowRun(
        workflow_id=wf.id,
        user_id=wf.user_id,
        status="pending",
        idempotency_key="run_clock_1",
        created_at=now,
        updated_at=now,
    )
    async_db_session.add(run)
    await async_db_session.commit()

    executor = WorkflowExecutor(session=async_db_session)
    completed_run = await executor.execute_run(run.id)

    assert completed_run.status == WorkflowStatus.COMPLETED.value

    # Verify notification was created
    notif_stmt = select(Notification).where(Notification.run_id == run.id)
    notif_res = await async_db_session.execute(notif_stmt)
    notif = notif_res.scalar_one_or_none()
    assert notif is not None
    assert notif.title == "Time Check Completed"


@pytest.mark.asyncio
async def test_executor_pauses_for_approval_on_restricted_tools(async_db_session: AsyncSession):
    """Verify workflow pauses in WAITING_APPROVAL when tool requires approval."""
    now = datetime.now(UTC)

    # Mock action runner returning requires_approval
    class MockApprovalRunner(WorkflowActionRunner):
        async def execute_action(self, tool_name, arguments, is_approved=False):
            if not is_approved:
                return ActionExecutionResult(
                    success=False,
                    requires_approval=True,
                    permission_level=PermissionLevel.EXTERNAL,
                    tool_name=tool_name,
                    tool_args=arguments,
                )
            return ActionExecutionResult(success=True, result={"pushed": True})

    wf = Workflow(
        user_id="user_test",
        name="Deploy Workflow",
        enabled=True,
        trigger_type="manual",
        trigger_config={},
        action_config={
            "steps": [
                {
                    "type": "action",
                    "config": {"tool": "git_push", "arguments": {"remote": "origin"}},
                }
            ]
        },
        created_at=now,
        updated_at=now,
    )
    async_db_session.add(wf)
    await async_db_session.commit()

    run = WorkflowRun(
        workflow_id=wf.id,
        user_id=wf.user_id,
        status="pending",
        idempotency_key="run_deploy_1",
        created_at=now,
        updated_at=now,
    )
    async_db_session.add(run)
    await async_db_session.commit()

    executor = WorkflowExecutor(session=async_db_session, action_runner=MockApprovalRunner())
    paused_run = await executor.execute_run(run.id)

    assert paused_run.status == WorkflowStatus.WAITING_APPROVAL.value


@pytest.mark.asyncio
async def test_executor_condition_step_stopping(async_db_session: AsyncSession):
    """Verify condition step with on_false='stop' cleanly terminates workflow."""
    now = datetime.now(UTC)
    wf = Workflow(
        user_id="user_test",
        name="Conditional Workflow",
        enabled=True,
        trigger_type="manual",
        trigger_config={},
        action_config={
            "steps": [
                {
                    "type": "action",
                    "config": {"tool": "calculator", "arguments": {"expression": "2 + 2"}},
                },
                {
                    "type": "condition",
                    "config": {
                        "field": "result",
                        "operator": "equals",
                        "value": 999,  # False! 4 != 999
                        "on_false": "stop",
                    },
                },
                {
                    "type": "notification",
                    "config": {"title": "Should Not Reach Here", "message": "Never"},
                },
            ]
        },
        created_at=now,
        updated_at=now,
    )
    async_db_session.add(wf)
    await async_db_session.commit()

    run = WorkflowRun(
        workflow_id=wf.id,
        user_id=wf.user_id,
        status="pending",
        idempotency_key="run_cond_1",
        created_at=now,
        updated_at=now,
    )
    async_db_session.add(run)
    await async_db_session.commit()

    executor = WorkflowExecutor(session=async_db_session)
    completed_run = await executor.execute_run(run.id)

    assert completed_run.status == WorkflowStatus.COMPLETED.value

    # Verify 3rd step (notification) was never reached/created
    notif_stmt = select(Notification).where(Notification.run_id == run.id)
    notif_res = await async_db_session.execute(notif_stmt)
    assert notif_res.scalar_one_or_none() is None
