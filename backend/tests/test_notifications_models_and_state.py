"""Tests for Notification models, lifecycle states, and expiration (Task 34, Spec 2-4, 64, 128)."""

from datetime import UTC, datetime, timedelta
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.notifications.models import (
    NotificationActionModel,
    NotificationDeliveryModel,
    NotificationModel,
    NotificationPreferenceModel,
)
from app.notifications.retention import NotificationRetentionManager
from app.notifications.schemas import (
    ActionStatus,
    ActionType,
    ChannelType,
    DeliveryStatus,
    NotificationPriority,
    NotificationState,
    NotificationType,
)


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
async def test_notification_creation_and_relationships(db_session: AsyncSession):
    """Verify notification model persistence with actions and delivery attempts (Spec 2, 39, 129)."""
    now = datetime.now(UTC)
    notif = NotificationModel(
        id="notif_test_1",
        user_id="user_alice",
        project_id="proj_backend",
        task_id="task_ci_investigation",
        type=NotificationType.TASK.value,
        priority=NotificationPriority.NORMAL.value,
        title="CI Investigation Complete",
        body="Kairo finished investigating CI failure on main.",
        status=NotificationState.PENDING.value,
        created_at=now,
        correlation_id="corr_abc123",
        dedupe_key="dedupe_user_alice_task_ci",
        metadata_json={"build_id": "9876"},
    )
    db_session.add(notif)

    # Add action
    action = NotificationActionModel(
        id="act_test_1",
        notification_id="notif_test_1",
        type=ActionType.OPEN.value,
        label="View Report",
        target_id="task_ci_investigation",
        status=ActionStatus.PENDING.value,
        created_at=now,
    )
    db_session.add(action)

    # Add delivery
    delivery = NotificationDeliveryModel(
        id="del_test_1",
        notification_id="notif_test_1",
        user_id="user_alice",
        channel=ChannelType.WEB.value,
        status=DeliveryStatus.DELIVERED.value,
        attempts=1,
        delivered_at=now,
    )
    db_session.add(delivery)

    await db_session.commit()
    await db_session.refresh(notif)

    assert notif.id == "notif_test_1"
    assert notif.user_id == "user_alice"
    assert len(notif.actions) == 1
    assert notif.actions[0].label == "View Report"
    assert len(notif.deliveries) == 1
    assert notif.deliveries[0].channel == "WEB"


@pytest.mark.asyncio
async def test_notification_state_transitions(db_session: AsyncSession):
    """Verify lifecycle state transitions (PENDING -> DELIVERED -> READ -> DISMISSED) (Spec 3)."""
    now = datetime.now(UTC)
    notif = NotificationModel(
        id="notif_test_2",
        user_id="user_alice",
        type=NotificationType.TASK.value,
        priority=NotificationPriority.NORMAL.value,
        title="Task Update",
        body="Task is processing.",
        status=NotificationState.PENDING.value,
        created_at=now,
        correlation_id="corr_1",
    )
    db_session.add(notif)
    await db_session.commit()

    # Delivering -> Delivered
    notif.status = NotificationState.DELIVERED.value
    await db_session.commit()
    await db_session.refresh(notif)
    assert notif.status == "DELIVERED"

    # Read
    notif.status = NotificationState.READ.value
    notif.read_at = datetime.now(UTC)
    await db_session.commit()
    await db_session.refresh(notif)
    assert notif.status == "READ"
    assert notif.read_at is not None

    # Dismissed
    notif.status = NotificationState.DISMISSED.value
    notif.dismissed_at = datetime.now(UTC)
    await db_session.commit()
    await db_session.refresh(notif)
    assert notif.status == "DISMISSED"
    assert notif.dismissed_at is not None


@pytest.mark.asyncio
async def test_stale_notification_expiration(db_session: AsyncSession):
    """Verify expired notifications and actions are marked EXPIRED by retention manager (Spec 14, 64)."""
    past = datetime.now(UTC) - timedelta(minutes=10)
    notif = NotificationModel(
        id="notif_expired_1",
        user_id="user_alice",
        type=NotificationType.APPROVAL.value,
        priority=NotificationPriority.HIGH.value,
        title="Expired Approval",
        body="Approval requested for database migration.",
        status=NotificationState.DELIVERED.value,
        created_at=past - timedelta(minutes=5),
        expires_at=past,
        correlation_id="corr_exp",
    )
    action = NotificationActionModel(
        id="act_expired_1",
        notification_id="notif_expired_1",
        type=ActionType.APPROVE.value,
        label="Approve",
        target_id="app_123",
        status=ActionStatus.PENDING.value,
        created_at=past - timedelta(minutes=5),
        expires_at=past,
    )
    db_session.add(notif)
    db_session.add(action)
    await db_session.commit()

    # Run expiration cleanup
    expired_count = await NotificationRetentionManager.expire_stale_notifications(db_session)
    assert expired_count >= 1

    await db_session.refresh(notif)
    await db_session.refresh(action)
    assert notif.status == NotificationState.EXPIRED.value
    assert action.status == ActionStatus.EXPIRED.value
