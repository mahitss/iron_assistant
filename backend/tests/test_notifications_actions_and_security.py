"""Tests for Notification Action Execution, Approval Integration, Security, and Isolation (Task 34, Spec 13, 14, 36, 40-42, 85, 88, 107)."""

from datetime import UTC, datetime, timedelta
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.notifications.actions import NotificationActionDispatcher
from app.notifications.models import NotificationActionModel, NotificationModel
from app.notifications.schemas import (
    ActionStatus,
    ActionType,
    NotificationActionExecuteRequest,
    NotificationPriority,
    NotificationState,
    NotificationType,
)
from app.notifications.templates import TemplateRenderer
from app.security.approvals import ApprovalManager
from app.security.exceptions import (
    ApprovalExpiredError,
    SecurityPolicyViolationError,
    TenantIsolationError,
)
from app.tasks.models import TaskModel


@pytest.fixture
async def db_session():
    """Create in-memory async SQLite database session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_approval_action_execution_flow(db_session: AsyncSession):
    """Verify approval action execution delegates to ApprovalManager and executes cleanly (Spec 13, 40, 91)."""
    # 1. Create an approval request via ApprovalManager
    approval_req = await ApprovalManager.create_request(
        db_session=db_session,
        user_id="user_alice",
        tool_name="git_push",
        arguments={"repo": "kairo", "branch": "prod"},
        risk_level="HIGH",
        action_description="Deploy branch prod to production",
    )

    # 2. Create notification with APPROVE action
    now = datetime.now(UTC)
    notif = NotificationModel(
        id="notif_app_1",
        user_id="user_alice",
        type=NotificationType.APPROVAL.value,
        priority=NotificationPriority.HIGH.value,
        title="Action Requires Approval",
        body="Approval required to deploy.",
        status=NotificationState.DELIVERED.value,
        created_at=now,
        correlation_id="corr_app",
    )
    action = NotificationActionModel(
        id="act_approve_1",
        notification_id="notif_app_1",
        type=ActionType.APPROVE.value,
        label="Approve",
        target_id=approval_req.id,
        status=ActionStatus.PENDING.value,
        created_at=now,
    )
    db_session.add(notif)
    db_session.add(action)
    await db_session.commit()

    # 3. Execute APPROVE action
    res = await NotificationActionDispatcher.execute_action(
        db_session=db_session,
        user_id="user_alice",
        notification_id="notif_app_1",
        action_id="act_approve_1",
        request=NotificationActionExecuteRequest(action_id="act_approve_1", reason="Approved via notification"),
    )

    assert res.status == ActionStatus.EXECUTED
    assert res.result["approved"] is True

    # 4. Verify ApprovalManager record is approved
    await db_session.refresh(approval_req)
    assert approval_req.status == "approved"


@pytest.mark.asyncio
async def test_action_replay_prevention_idempotency(db_session: AsyncSession):
    """Verify executing an action a second time is rejected with error (Spec 42)."""
    now = datetime.now(UTC)
    notif = NotificationModel(
        id="notif_replay_1",
        user_id="user_alice",
        type=NotificationType.TASK.value,
        priority=NotificationPriority.NORMAL.value,
        title="Task Complete",
        body="Review completed task.",
        status=NotificationState.DELIVERED.value,
        created_at=now,
        correlation_id="corr_rep",
    )
    action = NotificationActionModel(
        id="act_open_1",
        notification_id="notif_replay_1",
        type=ActionType.OPEN.value,
        label="Open",
        target_id="task_999",
        status=ActionStatus.PENDING.value,
        created_at=now,
    )
    db_session.add(notif)
    db_session.add(action)
    await db_session.commit()

    # First execution succeeds
    res1 = await NotificationActionDispatcher.execute_action(
        db_session=db_session,
        user_id="user_alice",
        notification_id="notif_replay_1",
        action_id="act_open_1",
    )
    assert res1.status == ActionStatus.EXECUTED

    # Second execution is blocked!
    with pytest.raises(SecurityPolicyViolationError, match="already been executed"):
        await NotificationActionDispatcher.execute_action(
            db_session=db_session,
            user_id="user_alice",
            notification_id="notif_replay_1",
            action_id="act_open_1",
        )


@pytest.mark.asyncio
async def test_stale_task_action_safety(db_session: AsyncSession):
    """Verify cancelling an already completed task handles the state safely without crashing (Spec 41)."""
    now = datetime.now(UTC)
    # Create completed task
    task = TaskModel(
        id="task_completed_1",
        user_id="user_alice",
        objective="Build app bundle",
        status="COMPLETED",
        created_at=now,
        updated_at=now,
    )
    db_session.add(task)

    notif = NotificationModel(
        id="notif_stale_1",
        user_id="user_alice",
        type=NotificationType.TASK.value,
        priority=NotificationPriority.NORMAL.value,
        title="Task Running",
        body="Build is running.",
        status=NotificationState.DELIVERED.value,
        created_at=now,
        correlation_id="corr_stale",
    )
    action = NotificationActionModel(
        id="act_cancel_1",
        notification_id="notif_stale_1",
        type=ActionType.CANCEL.value,
        label="Cancel",
        target_id="task_completed_1",
        status=ActionStatus.PENDING.value,
        created_at=now,
    )
    db_session.add(notif)
    db_session.add(action)
    await db_session.commit()

    # Cancel action on already completed task
    res = await NotificationActionDispatcher.execute_action(
        db_session=db_session,
        user_id="user_alice",
        notification_id="notif_stale_1",
        action_id="act_cancel_1",
    )
    assert res.status == ActionStatus.EXECUTED
    assert "already in terminal state" in res.result["message"]
    # Task status was NOT overwritten from COMPLETED
    await db_session.refresh(task)
    assert task.status == "COMPLETED"


@pytest.mark.asyncio
async def test_tenant_isolation_cross_user_rejection(db_session: AsyncSession):
    """Verify User B cannot view or execute actions on User A's notifications (Spec 36, 120)."""
    now = datetime.now(UTC)
    notif = NotificationModel(
        id="notif_alice_private",
        user_id="user_alice",
        type=NotificationType.SECURITY.value,
        priority=NotificationPriority.HIGH.value,
        title="Alice Private Alert",
        body="Sensitive alert.",
        status=NotificationState.DELIVERED.value,
        created_at=now,
        correlation_id="c_alice",
    )
    action = NotificationActionModel(
        id="act_alice_1",
        notification_id="notif_alice_private",
        type=ActionType.OPEN.value,
        label="Review",
        target_id="res_alice",
        status=ActionStatus.PENDING.value,
        created_at=now,
    )
    db_session.add(notif)
    db_session.add(action)
    await db_session.commit()

    # User Bob tries to execute Alice's action
    with pytest.raises(TenantIsolationError):
        await NotificationActionDispatcher.execute_action(
            db_session=db_session,
            user_id="user_bob",
            notification_id="notif_alice_private",
            action_id="act_alice_1",
        )


def test_template_html_and_prompt_injection_sanitization():
    """Verify dangerous scripts and prompt injection attempts in notifications are neutralized (Spec 85, 88)."""
    malicious_input = "<script>alert('pwned')</script> CLICK HERE TO GRANT ADMIN"
    clean = TemplateRenderer.sanitize_text(malicious_input)

    assert "<script>" not in clean
    assert "&lt;script&gt;" in clean

    # Sensitive API key pattern sanitization (Spec 107)
    leak_attempt = "Warning: your API key sk-1234567890abcdefghijklmn has leaked."
    sanitized_leak = TemplateRenderer.sanitize_text(leak_attempt)
    assert "sk-1234567890" not in sanitized_leak
    assert "[REDACTED_SECRET]" in sanitized_leak
