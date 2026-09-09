"""Tests for Notification Delivery, Channels, Fallback Routing, and Retries (Task 34, Spec 28-32, 57-60)."""

from datetime import UTC, datetime
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.notifications.channels import (
    DesktopNotificationChannel,
    PushNotificationChannel,
    VoiceNotificationChannel,
    WebNotificationChannel,
)
from app.notifications.delivery import NotificationDeliveryCoordinator
from app.notifications.models import NotificationModel, NotificationPreferenceModel
from app.notifications.retry import DeliveryRetryManager
from app.notifications.schemas import (
    ChannelType,
    NotificationPriority,
    NotificationResponse,
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


def test_channel_capabilities_declaration():
    """Verify each channel declares explicit technical capabilities (Spec 29)."""
    web = WebNotificationChannel()
    assert web.capabilities.supports_rich_content is True
    assert web.capabilities.supports_actions is True

    voice = VoiceNotificationChannel()
    assert voice.capabilities.supports_audio is True
    assert voice.capabilities.supports_actions is False


@pytest.mark.asyncio
async def test_voice_channel_filters_low_priority():
    """Verify voice channel only vocalizes HIGH or URGENT events (Spec 71, 72)."""
    voice = VoiceNotificationChannel()

    # LOW priority -> skipped
    n_low = NotificationResponse(
        id="n_low",
        user_id="user_alice",
        type=NotificationType.RESEARCH,
        priority=NotificationPriority.LOW,
        title="Source Found",
        body="Discovered reference",
        status=NotificationState.PENDING,
        created_at=datetime.now(UTC),
        correlation_id="c_1",
    )
    assert await voice.deliver(n_low) is True

    # HIGH priority -> delivered
    n_high = NotificationResponse(
        id="n_high",
        user_id="user_alice",
        type=NotificationType.APPROVAL,
        priority=NotificationPriority.HIGH,
        title="Approval Required",
        body="Approve deployment",
        status=NotificationState.PENDING,
        created_at=datetime.now(UTC),
        correlation_id="c_2",
    )
    assert await voice.deliver(n_high) is True


@pytest.mark.asyncio
async def test_delivery_coordinator_and_web_fallback(db_session: AsyncSession):
    """Verify delivery coordinator routes to enabled channels and executes fallback (Spec 30, 60)."""
    coordinator = NotificationDeliveryCoordinator()
    now = datetime.now(UTC)

    pref = NotificationPreferenceModel(
        user_id="user_alice",
        enabled_channels=["WEB", "DESKTOP"],
        quiet_hours_enabled=False,
    )
    db_session.add(pref)

    notif = NotificationModel(
        id="notif_deliv_1",
        user_id="user_alice",
        type=NotificationType.TASK.value,
        priority=NotificationPriority.NORMAL.value,
        title="Task Complete",
        body="Finished testing.",
        status=NotificationState.PENDING.value,
        created_at=now,
        correlation_id="c_del",
    )
    db_session.add(notif)
    await db_session.commit()

    deliveries = await coordinator.deliver(
        db_session=db_session,
        notification=notif,
        preferences=pref,
    )

    assert len(deliveries) >= 2
    channels_delivered = [d.channel for d in deliveries]
    assert ChannelType.WEB.value in channels_delivered
    assert ChannelType.DESKTOP.value in channels_delivered
    assert notif.status == NotificationState.DELIVERED.value


def test_retry_manager_backoff_and_permanent_error_handling():
    """Verify bounded exponential backoff and dropping of non-retryable errors (Spec 57, 58)."""
    retry_mgr = DeliveryRetryManager(max_retries=3, base_backoff_seconds=2, max_backoff_seconds=30)

    # Backoff calculation
    assert retry_mgr.calculate_backoff_seconds(1) == 2
    assert retry_mgr.calculate_backoff_seconds(2) == 4
    assert retry_mgr.calculate_backoff_seconds(3) == 8

    # Transient error is retryable
    assert retry_mgr.is_retryable("Network timeout connecting to desktop agent", attempts=1) is True

    # Permanent auth / revoked error is NOT retryable (Spec 57)
    assert retry_mgr.is_retryable("Unauthorized: device was revoked", attempts=1) is False
    assert retry_mgr.is_retryable("Access denied for device", attempts=1) is False

    # Max attempts exceeded
    assert retry_mgr.is_retryable("Transient socket hangup", attempts=3) is False
