"""Notification service managing in-app delivery, quiet hours, rate limiting, and read/dismiss lifecycles."""

import logging
from datetime import UTC, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.proactive.models import ProactiveInsight, UserProactiveSettings
from app.proactive.state import InsightPriority, InsightStatus

logger = logging.getLogger("kairo.proactive.notifier")


class NotificationService:
    """Delivers and manages user-scoped in-app notifications."""

    @classmethod
    def is_in_quiet_hours(
        cls,
        settings: UserProactiveSettings | None,
        now_dt: datetime | None = None,
    ) -> bool:
        """Evaluate whether current time falls within user's configured quiet hours."""
        if not settings or not settings.quiet_hours_enabled:
            return False

        try:
            tz = ZoneInfo(settings.timezone)
        except (ZoneInfoNotFoundError, Exception):
            tz = ZoneInfo("UTC")

        now_utc = now_dt or datetime.now(UTC)
        now_local = now_utc.astimezone(tz).time()

        try:
            start_parts = [int(p) for p in settings.quiet_hours_start.split(":")]
            end_parts = [int(p) for p in settings.quiet_hours_end.split(":")]
            start_time = time(hour=start_parts[0], minute=start_parts[1])
            end_time = time(hour=end_parts[0], minute=end_parts[1])
        except Exception:
            # Fallback default 22:00 -> 08:00
            start_time = time(22, 0)
            end_time = time(8, 0)

        if start_time <= end_time:
            return start_time <= now_local <= end_time
        # Overnight range (e.g. 22:00 to 08:00)
        return now_local >= start_time or now_local <= end_time

    @classmethod
    async def check_rate_limit(
        cls,
        user_id: str,
        priority: str,
        db_session: AsyncSession,
        redis_client: Any = None,
    ) -> bool:
        """Check hourly notification limits.

        Preserves HIGH and CRITICAL notifications even if the hourly limit is exceeded.
        Suppresses LOW and MEDIUM notifications when threshold is reached.
        """
        # Critical and High security/approval notifications are NEVER suppressed by rate limit
        p_upper = priority.upper()
        if p_upper in (InsightPriority.CRITICAL, InsightPriority.HIGH):
            return True

        cfg = get_settings()
        limit = getattr(cfg, "KAIRO_MAX_PROACTIVE_NOTIFICATIONS_PER_HOUR", 20)

        # Check DB count over last hour
        one_hour_ago = datetime.now(UTC) - timedelta(hours=1)
        count_query = select(func.count(ProactiveInsight.id)).where(
            ProactiveInsight.user_id == user_id,
            ProactiveInsight.created_at >= one_hour_ago,
            ProactiveInsight.status.in_([InsightStatus.DELIVERED, InsightStatus.NEW, InsightStatus.READ]),
        )
        res = await db_session.execute(count_query)
        recent_count = res.scalar_one()

        if recent_count >= limit:
            logger.warning(
                "Hourly proactive notification limit (%d) reached for user %s. Suppressed %s notification.",
                limit,
                user_id,
                priority,
            )
            return False

        return True

    @classmethod
    async def list_notifications(
        cls,
        db_session: AsyncSession,
        user_id: str,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ProactiveInsight], int, int]:
        """Fetch notifications for user, returning (items, total_count, unread_count)."""
        base = select(ProactiveInsight).where(ProactiveInsight.user_id == user_id)

        if status:
            base = base.where(ProactiveInsight.status == status)
        else:
            # Exclude dismissed and expired by default
            base = base.where(
                ProactiveInsight.status.in_([InsightStatus.NEW, InsightStatus.DELIVERED, InsightStatus.READ])
            )

        total_res = await db_session.execute(
            select(func.count(ProactiveInsight.id)).where(ProactiveInsight.user_id == user_id)
        )
        total = total_res.scalar_one()

        unread_res = await db_session.execute(
            select(func.count(ProactiveInsight.id)).where(
                ProactiveInsight.user_id == user_id,
                ProactiveInsight.status.in_([InsightStatus.NEW, InsightStatus.DELIVERED]),
            )
        )
        unread = unread_res.scalar_one()

        items_query = base.order_by(desc(ProactiveInsight.created_at)).offset(offset).limit(limit)
        items_res = await db_session.execute(items_query)
        items = list(items_res.scalars().all())

        return items, total, unread

    @classmethod
    async def mark_read(
        cls,
        db_session: AsyncSession,
        user_id: str,
        notification_id: str,
    ) -> ProactiveInsight | None:
        """Mark a notification as read with tenant isolation check."""
        query = select(ProactiveInsight).where(
            ProactiveInsight.id == notification_id,
            ProactiveInsight.user_id == user_id,
        )
        res = await db_session.execute(query)
        insight = res.scalar_one_or_none()
        if not insight:
            return None

        insight.status = InsightStatus.READ
        await db_session.commit()
        await db_session.refresh(insight)
        return insight

    @classmethod
    async def mark_dismissed(
        cls,
        db_session: AsyncSession,
        user_id: str,
        notification_id: str,
    ) -> ProactiveInsight | None:
        """Mark a notification as dismissed with tenant isolation check."""
        query = select(ProactiveInsight).where(
            ProactiveInsight.id == notification_id,
            ProactiveInsight.user_id == user_id,
        )
        res = await db_session.execute(query)
        insight = res.scalar_one_or_none()
        if not insight:
            return None

        insight.status = InsightStatus.DISMISSED
        await db_session.commit()
        await db_session.refresh(insight)
        return insight
