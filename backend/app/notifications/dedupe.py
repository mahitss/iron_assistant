"""Deterministic deduplication and structured dedupe key generation for Kairo Notifications (Task 34, Spec 43-45)."""

from datetime import UTC, datetime, timedelta
import hashlib
import logging
from typing import Any
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.notifications.models import NotificationModel
from app.notifications.schemas import NotificationType

logger = logging.getLogger("kairo.notifications.dedupe")


class NotificationDeduplicator:
    """
    Computes deterministic dedupe keys and evaluates whether an incoming notification is a duplicate.
    Enforces Dedupe Safety: Never merges distinct security events based on loose string similarity.
    """

    def __init__(self, default_window_seconds: int = 300) -> None:
        self.default_window_seconds = default_window_seconds
        # In-memory sliding cache: dedupe_key -> last_seen_datetime
        self._cache: dict[str, datetime] = {}

    @classmethod
    def compute_dedupe_key(
        cls,
        user_id: str,
        event_type: str,
        notification_type: NotificationType,
        resource_id: str | None = None,
        state: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> str:
        """
        Build a deterministic dedupe key based on structured identity.
        Format: sha256(user_id:event_type:resource_id:state[:security_discriminator])
        """
        payload = payload or {}
        resource = resource_id or payload.get("task_id") or payload.get("approval_id") or payload.get("device_id") or "global"
        meaningful_state = state or payload.get("status") or payload.get("state") or "default"

        elements = [user_id, event_type, str(resource), str(meaningful_state)]

        # Spec 45 Dedupe Safety: For SECURITY events, append distinct discriminators
        # (e.g. distinct IP, session_id, violation_id) so distinct events are never collapsed
        if notification_type == NotificationType.SECURITY:
            sec_discriminator = payload.get("session_id") or payload.get("incident_id") or payload.get("violation_id") or ""
            if sec_discriminator:
                elements.append(str(sec_discriminator))

        raw_str = ":".join(elements)
        digest = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()[:32]
        return f"dedupe_{digest}"

    async def is_duplicate(
        self,
        dedupe_key: str,
        db_session: AsyncSession,
        window_seconds: int | None = None,
    ) -> bool:
        """
        Check if an active notification with this dedupe_key was created within the dedupe window.
        """
        window = window_seconds or self.default_window_seconds
        now = datetime.now(UTC)
        cutoff = now - timedelta(seconds=window)

        # 1. Fast in-memory check
        last_seen = self._cache.get(dedupe_key)
        if last_seen and last_seen > cutoff:
            logger.info("Notification deduplicated via memory cache: %s", dedupe_key)
            return True

        # 2. Authoritative database check
        stmt = (
            select(NotificationModel)
            .where(
                NotificationModel.dedupe_key == dedupe_key,
                NotificationModel.created_at >= cutoff,
            )
            .order_by(desc(NotificationModel.created_at))
            .limit(1)
        )
        res = await db_session.execute(stmt)
        record = res.scalars().first()

        if record:
            self._cache[dedupe_key] = record.created_at if record.created_at.tzinfo is not None else record.created_at.replace(tzinfo=UTC)
            logger.info("Notification deduplicated via DB record: %s (id: %s)", dedupe_key, record.id)
            return True

        return False

    def record_seen(self, dedupe_key: str) -> None:
        """Record timestamp of newly created notification dedupe key."""
        now = datetime.now(UTC)
        self._cache[dedupe_key] = now
        # Clean up stale memory cache keys (> 1 hour)
        cutoff = now - timedelta(seconds=3600)
        self._cache = {k: v for k, v in self._cache.items() if v > cutoff}
