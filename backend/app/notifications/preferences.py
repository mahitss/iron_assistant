"""User notification preferences and quiet hours policy manager (Task 34, Spec 49-53, 105)."""

from datetime import UTC, datetime, time
import logging
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.ext.asyncio import AsyncSession

from app.notifications.models import NotificationPreferenceModel
from app.notifications.schemas import (
    ChannelType,
    NotificationPreferencesRequest,
    NotificationPreferencesResponse,
    NotificationPriority,
    NotificationType,
)

logger = logging.getLogger("kairo.notifications.preferences")


class NotificationPreferencesManager:
    """
    Manages user preferences and evaluates quiet hours.
    Security Invariant (Spec 50, 105): Mandatory security notifications cannot be disabled or silenced by quiet hours.
    """

    DEFAULT_CHANNELS = [ChannelType.WEB.value]
    DEFAULT_MIN_PRIORITY = NotificationPriority.LOW.value

    @classmethod
    async def get_or_create_preferences(
        cls,
        db_session: AsyncSession,
        user_id: str,
    ) -> NotificationPreferenceModel:
        """Fetch existing preferences or initialize safe system defaults."""
        record = await db_session.get(NotificationPreferenceModel, user_id)
        if not record:
            now = datetime.now(UTC)
            record = NotificationPreferenceModel(
                user_id=user_id,
                enabled_channels=cls.DEFAULT_CHANNELS,
                type_preferences={},
                quiet_hours_enabled=False,
                quiet_hours_start="22:00",
                quiet_hours_end="08:00",
                timezone="UTC",
                digest_enabled=False,
                digest_frequency="daily",
                grouping_enabled=True,
                min_priority=cls.DEFAULT_MIN_PRIORITY,
                updated_at=now,
            )
            db_session.add(record)
            await db_session.commit()
            await db_session.refresh(record)
        return record

    @classmethod
    async def update_preferences(
        cls,
        db_session: AsyncSession,
        user_id: str,
        request: NotificationPreferencesRequest,
    ) -> NotificationPreferenceModel:
        """Update preferences while preventing disabling mandatory security signals."""
        record = await cls.get_or_create_preferences(db_session, user_id)

        # Ensure at least WEB channel is enabled if any channels specified
        channels = [c.value if hasattr(c, "value") else str(c) for c in request.enabled_channels]
        if not channels:
            channels = [ChannelType.WEB.value]

        # Security invariant (Spec 105): If user attempts to disable SECURITY in type_preferences,
        # enforce enabled: True
        clean_types = dict(request.type_preferences)
        if NotificationType.SECURITY.value in clean_types:
            clean_types[NotificationType.SECURITY.value] = True

        record.enabled_channels = channels
        record.type_preferences = clean_types
        record.quiet_hours_enabled = request.quiet_hours_enabled
        record.quiet_hours_start = request.quiet_hours_start
        record.quiet_hours_end = request.quiet_hours_end
        record.timezone = request.timezone
        record.digest_enabled = request.digest_enabled
        record.digest_frequency = request.digest_frequency
        record.grouping_enabled = request.grouping_enabled
        record.min_priority = request.min_priority.value if hasattr(request.min_priority, "value") else str(request.min_priority)
        record.updated_at = datetime.now(UTC)

        await db_session.commit()
        await db_session.refresh(record)
        return record

    @classmethod
    def is_in_quiet_hours(
        cls,
        record: NotificationPreferenceModel,
        now_dt: datetime | None = None,
    ) -> bool:
        """Evaluate if given time falls within configured quiet hours window."""
        if not record.quiet_hours_enabled:
            return False

        try:
            tz = ZoneInfo(record.timezone)
        except (ZoneInfoNotFoundError, Exception):
            tz = ZoneInfo("UTC")

        now_utc = now_dt or datetime.now(UTC)
        now_local = now_utc.astimezone(tz).time()

        try:
            sp = [int(p) for p in record.quiet_hours_start.split(":")]
            ep = [int(p) for p in record.quiet_hours_end.split(":")]
            start_time = time(hour=sp[0], minute=sp[1])
            end_time = time(hour=ep[0], minute=ep[1])
        except Exception:
            start_time = time(22, 0)
            end_time = time(8, 0)

        if start_time <= end_time:
            return start_time <= now_local <= end_time
        # Overnight range (e.g. 22:00 to 08:00)
        return now_local >= start_time or now_local <= end_time

    @classmethod
    def should_deliver_during_quiet_hours(
        cls,
        notification_type: NotificationType,
        priority: NotificationPriority,
    ) -> bool:
        """
        Evaluate if notification bypasses quiet hours.
        HIGH and URGENT security events, approvals, and emergency stops always deliver (Spec 49, 50).
        """
        if priority == NotificationPriority.URGENT:
            return True
        if notification_type == NotificationType.APPROVAL:
            return True
        if notification_type == NotificationType.SECURITY and priority in (NotificationPriority.HIGH, NotificationPriority.URGENT):
            return True
        return False
