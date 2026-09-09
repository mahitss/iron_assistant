"""Retention and expiration cleanup manager for Kairo Notifications (Task 34, Spec 64-67, 131)."""

from datetime import UTC, datetime, timedelta
import logging

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.notifications.models import NotificationActionModel, NotificationDeliveryModel, NotificationModel
from app.notifications.schemas import ActionStatus, NotificationState

logger = logging.getLogger("kairo.notifications.retention")


class NotificationRetentionManager:
    """
    Executes retention pruning and marks expired notifications/actions.
    Invariant (Spec 66, 67): Notification cleanup never mutates or purges the Security Audit Log.
    """

    @classmethod
    async def expire_stale_notifications(cls, db_session: AsyncSession) -> int:
        """Mark unread notifications and actions whose expires_at has passed as EXPIRED."""
        now = datetime.now(UTC)

        # 1. Expire notifications
        stmt = (
            update(NotificationModel)
            .where(
                NotificationModel.expires_at <= now,
                NotificationModel.status.in_([NotificationState.PENDING.value, NotificationState.DELIVERED.value]),
            )
            .values(status=NotificationState.EXPIRED.value)
        )
        res = await db_session.execute(stmt)
        expired_notifs = res.rowcount or 0

        # 2. Expire actions
        action_stmt = (
            update(NotificationActionModel)
            .where(
                NotificationActionModel.expires_at <= now,
                NotificationActionModel.status == ActionStatus.PENDING.value,
            )
            .values(status=ActionStatus.EXPIRED.value)
        )
        action_res = await db_session.execute(action_stmt)
        expired_actions = action_res.rowcount or 0

        if expired_notifs > 0 or expired_actions > 0:
            await db_session.commit()
            logger.info("Marked %d notifications and %d actions as EXPIRED.", expired_notifs, expired_actions)

        return expired_notifs

    @classmethod
    async def purge_old_records(cls, db_session: AsyncSession, retention_days: int = 30) -> int:
        """Purge notifications older than retention window."""
        now = datetime.now(UTC)
        cutoff = now - timedelta(days=retention_days)

        # Delete cascades to actions and deliveries
        del_stmt = delete(NotificationModel).where(NotificationModel.created_at < cutoff)
        res = await db_session.execute(del_stmt)
        purged = res.rowcount or 0

        if purged > 0:
            await db_session.commit()
            logger.info("Purged %d notifications older than %d days.", purged, retention_days)

        return purged
