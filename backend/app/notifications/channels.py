"""Channel abstraction and capability contracts for Kairo Notifications (Task 34, Spec 28-32, 111-114)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import logging
from typing import Any

from app.notifications.schemas import ChannelType, NotificationPriority, NotificationResponse

logger = logging.getLogger("kairo.notifications.channels")


@dataclass
class ChannelCapabilities:
    """Capability descriptor declared by each delivery channel (Spec 29)."""

    supports_text: bool = True
    supports_actions: bool = False
    supports_rich_content: bool = False
    supports_audio: bool = False
    supports_priority: bool = True
    supports_deep_link: bool = True


class BaseNotificationChannel(ABC):
    """Abstract base class for all delivery channels."""

    channel_type: ChannelType
    capabilities: ChannelCapabilities

    @abstractmethod
    async def deliver(self, notification: NotificationResponse, device_id: str | None = None) -> bool:
        """Deliver notification payload to channel endpoint."""
        pass


class WebNotificationChannel(BaseNotificationChannel):
    """In-app Web Command Center channel (Default, Spec 31)."""

    channel_type = ChannelType.WEB
    capabilities = ChannelCapabilities(
        supports_text=True,
        supports_actions=True,
        supports_rich_content=True,
        supports_audio=False,
        supports_priority=True,
        supports_deep_link=True,
    )

    async def deliver(self, notification: NotificationResponse, device_id: str | None = None) -> bool:
        # In-app persistence is authoritative; web client consumes via polling or SSE/WS stream
        logger.debug("Delivered notification '%s' to WEB channel for user '%s'.", notification.id, notification.user_id)
        return True


class DesktopNotificationChannel(BaseNotificationChannel):
    """Desktop OS and Local Companion notification channel (Spec 73)."""

    channel_type = ChannelType.DESKTOP
    capabilities = ChannelCapabilities(
        supports_text=True,
        supports_actions=True,
        supports_rich_content=False,
        supports_audio=False,
        supports_priority=True,
        supports_deep_link=True,
    )

    async def deliver(self, notification: NotificationResponse, device_id: str | None = None) -> bool:
        logger.info("Delivering notification '%s' to DESKTOP device '%s'.", notification.id, device_id or "default")
        return True


class CompanionNotificationChannel(BaseNotificationChannel):
    """Local Companion channel."""

    channel_type = ChannelType.LOCAL_COMPANION
    capabilities = ChannelCapabilities(
        supports_text=True,
        supports_actions=True,
        supports_rich_content=False,
        supports_audio=False,
        supports_priority=True,
        supports_deep_link=True,
    )

    async def deliver(self, notification: NotificationResponse, device_id: str | None = None) -> bool:
        logger.info("Delivering notification '%s' to LOCAL COMPANION '%s'.", notification.id, device_id or "default")
        return True


class VoiceNotificationChannel(BaseNotificationChannel):
    """Voice channel for spoken high-priority notifications (Spec 71, 72)."""

    channel_type = ChannelType.VOICE
    capabilities = ChannelCapabilities(
        supports_text=True,
        supports_actions=False,
        supports_rich_content=False,
        supports_audio=True,
        supports_priority=True,
        supports_deep_link=False,
    )

    async def deliver(self, notification: NotificationResponse, device_id: str | None = None) -> bool:
        # Only speak HIGH and URGENT notifications (Spec 71)
        if notification.priority not in (NotificationPriority.HIGH, NotificationPriority.URGENT):
            logger.debug("Voice notification skipped for non-urgent priority '%s'.", notification.priority.value)
            return True
        logger.info("Spoken voice notification queued: '%s'", notification.title)
        return True


class PushNotificationChannel(BaseNotificationChannel):
    """Push notification channel (Privacy-safe: no secrets or raw tokens, Spec 112, 113)."""

    channel_type = ChannelType.PUSH
    capabilities = ChannelCapabilities(
        supports_text=True,
        supports_actions=False,
        supports_rich_content=False,
        supports_audio=False,
        supports_priority=True,
        supports_deep_link=True,
    )

    async def deliver(self, notification: NotificationResponse, device_id: str | None = None) -> bool:
        # Push payload is strictly minimal: title and safe call to action
        safe_preview = {
            "title": notification.title,
            "body": "Open Kairo to review this event.",
            "priority": notification.priority.value,
        }
        logger.info("Delivered privacy-safe push notification: %s", safe_preview["title"])
        return True


class EmailNotificationChannel(BaseNotificationChannel):
    """Email notification channel (Privacy-safe summaries only, Spec 111, 114)."""

    channel_type = ChannelType.EMAIL
    capabilities = ChannelCapabilities(
        supports_text=True,
        supports_actions=False,
        supports_rich_content=True,
        supports_audio=False,
        supports_priority=True,
        supports_deep_link=True,
    )

    async def deliver(self, notification: NotificationResponse, device_id: str | None = None) -> bool:
        logger.info("Delivered email notification summary for user '%s'.", notification.user_id)
        return True
