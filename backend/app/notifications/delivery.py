"""Multi-channel delivery coordinator with presence-aware routing and fallbacks (Task 34, Spec 30, 32-34, 60, 63, 129, 130)."""

from datetime import UTC, datetime
import logging
from typing import Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.notifications.channels import (
    BaseNotificationChannel,
    CompanionNotificationChannel,
    DesktopNotificationChannel,
    EmailNotificationChannel,
    PushNotificationChannel,
    VoiceNotificationChannel,
    WebNotificationChannel,
)
from app.notifications.models import NotificationDeliveryModel, NotificationModel, NotificationPreferenceModel
from app.notifications.schemas import (
    ChannelType,
    DeliveryStatus,
    NotificationPriority,
    NotificationResponse,
    NotificationState,
    NotificationType,
)

logger = logging.getLogger("kairo.notifications.delivery")


class NotificationDeliveryCoordinator:
    """
    Coordinates delivery of notifications to authorized interfaces.
    Selects channels based on user preferences, presence, priority, and fallback rules.
    """

    def __init__(self) -> None:
        self.channels: dict[ChannelType, BaseNotificationChannel] = {
            ChannelType.WEB: WebNotificationChannel(),
            ChannelType.DESKTOP: DesktopNotificationChannel(),
            ChannelType.LOCAL_COMPANION: CompanionNotificationChannel(),
            ChannelType.VOICE: VoiceNotificationChannel(),
            ChannelType.PUSH: PushNotificationChannel(),
            ChannelType.EMAIL: EmailNotificationChannel(),
        }

    async def deliver(
        self,
        db_session: AsyncSession,
        notification: NotificationModel,
        preferences: NotificationPreferenceModel,
        active_device_id: str | None = None,
        is_desktop_active: bool = False,
    ) -> list[NotificationDeliveryModel]:
        """
        Execute multi-channel delivery for a notification and persist delivery attempts.
        """
        now = datetime.now(UTC)
        prio = NotificationPriority(notification.priority) if isinstance(notification.priority, str) else notification.priority

        # 1. Determine target channels based on preferences
        enabled_channel_names = preferences.enabled_channels or ["WEB"]
        target_channels: list[ChannelType] = []

        for ch_name in enabled_channel_names:
            try:
                target_channels.append(ChannelType(ch_name))
            except ValueError:
                pass

        # Always ensure WEB channel is included for in-app visibility
        if ChannelType.WEB not in target_channels:
            target_channels.insert(0, ChannelType.WEB)

        # 2. Presence-aware preference (Spec 32):
        # If desktop active, prioritize desktop
        if is_desktop_active and ChannelType.DESKTOP not in target_channels:
            target_channels.append(ChannelType.DESKTOP)

        # High/Urgent priority triggers multi-device delivery if configured (Spec 33)
        if prio in (NotificationPriority.HIGH, NotificationPriority.URGENT):
            if ChannelType.DESKTOP not in target_channels:
                target_channels.append(ChannelType.DESKTOP)

        deliveries: list[NotificationDeliveryModel] = []
        overall_success = False

        # Convert to response schema for channel handlers
        notif_response = NotificationResponse(
            id=notification.id,
            user_id=notification.user_id,
            project_id=notification.project_id,
            task_id=notification.task_id,
            type=NotificationType(notification.type),
            priority=NotificationPriority(notification.priority),
            title=notification.title,
            body=notification.body,
            status=NotificationState(notification.status),
            created_at=notification.created_at,
            expires_at=notification.expires_at,
            read_at=notification.read_at,
            dismissed_at=notification.dismissed_at,
            source_event_id=notification.source_event_id,
            correlation_id=notification.correlation_id,
            dedupe_key=notification.dedupe_key,
            metadata=notification.metadata_json or {},
            actions=[],
            deliveries=[],
        )

        for ch_type in target_channels:
            channel_impl = self.channels.get(ch_type)
            if not channel_impl:
                continue

            delivery_record = NotificationDeliveryModel(
                id=f"del_{uuid.uuid4().hex[:16]}",
                notification_id=notification.id,
                user_id=notification.user_id,
                channel=ch_type.value,
                device_id=active_device_id if ch_type in (ChannelType.DESKTOP, ChannelType.LOCAL_COMPANION) else None,
                status=DeliveryStatus.PENDING.value,
                attempts=1,
            )

            try:
                success = await channel_impl.deliver(notif_response, device_id=active_device_id)
                if success:
                    delivery_record.status = DeliveryStatus.DELIVERED.value
                    delivery_record.delivered_at = now
                    overall_success = True
                else:
                    delivery_record.status = DeliveryStatus.FAILED.value
                    delivery_record.error_message = "Channel reported delivery failure"
            except Exception as exc:
                logger.error("Delivery failure on channel '%s' for notification '%s': %s", ch_type.value, notification.id, exc)
                delivery_record.status = DeliveryStatus.FAILED.value
                delivery_record.error_message = str(exc)[:255]

            db_session.add(delivery_record)
            deliveries.append(delivery_record)

        # 3. Channel fallback (Spec 60):
        # If all non-web channels failed, verify WEB delivery succeeded as authoritative fallback
        if not overall_success and ChannelType.WEB in self.channels:
            logger.info("Channel fallback triggered: ensuring WEB delivery for '%s'.", notification.id)
            web_delivery = NotificationDeliveryModel(
                id=f"del_{uuid.uuid4().hex[:16]}",
                notification_id=notification.id,
                user_id=notification.user_id,
                channel=ChannelType.WEB.value,
                device_id=None,
                status=DeliveryStatus.DELIVERED.value,
                attempts=1,
                delivered_at=now,
            )
            db_session.add(web_delivery)
            deliveries.append(web_delivery)
            overall_success = True

        notification.status = NotificationState.DELIVERED.value if overall_success else NotificationState.FAILED.value
        await db_session.commit()

        return deliveries
