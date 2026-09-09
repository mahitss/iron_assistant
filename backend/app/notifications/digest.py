"""Periodic digest generator for low-priority events without hallucination (Task 34, Spec 48, 145, 146)."""

from datetime import UTC, datetime, timedelta
import logging
from typing import Any
from pydantic import BaseModel, Field

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.notifications.models import NotificationModel
from app.notifications.schemas import NotificationPriority, NotificationResponse, NotificationType

logger = logging.getLogger("kairo.notifications.digest")


class DigestItem(BaseModel):
    notification_id: str
    type: str
    title: str
    created_at: datetime


class NotificationDigest(BaseModel):
    user_id: str
    frequency: str
    generated_at: datetime
    total_items: int
    items_by_type: dict[str, list[DigestItem]] = Field(default_factory=dict)
    summary_text: str


class NotificationDigestGenerator:
    """
    Generates structured periodic digests (hourly/daily) for low-priority notifications.
    Invariant (Spec 48, 145, 146):
      - Urgent and High-priority events are NEVER digested.
      - Every digest item maps 1:1 to an actual persisted notification (no hallucinated combined stories).
    """

    @classmethod
    async def generate_user_digest(
        cls,
        db_session: AsyncSession,
        user_id: str,
        since: datetime,
        frequency: str = "daily",
    ) -> NotificationDigest | None:
        """Fetch eligible low/normal notifications created since cutoff and build structured digest."""
        stmt = (
            select(NotificationModel)
            .where(
                NotificationModel.user_id == user_id,
                NotificationModel.created_at >= since,
                NotificationModel.priority.in_([NotificationPriority.LOW.value, NotificationPriority.NORMAL.value]),
            )
            .order_by(desc(NotificationModel.created_at))
        )
        res = await db_session.execute(stmt)
        records = list(res.scalars().all())

        if not records:
            return None

        items_by_type: dict[str, list[DigestItem]] = {}
        for rec in records:
            t = rec.type
            if t not in items_by_type:
                items_by_type[t] = []
            items_by_type[t].append(
                DigestItem(
                    notification_id=rec.id,
                    type=rec.type,
                    title=rec.title,
                    created_at=rec.created_at,
                )
            )

        # Build verified summary text
        type_summaries = [f"{len(items)} {t.lower()} updates" for t, items in items_by_type.items()]
        summary_text = f"Your {frequency} Kairo digest: " + ", ".join(type_summaries) + "."

        return NotificationDigest(
            user_id=user_id,
            frequency=frequency,
            generated_at=datetime.now(UTC),
            total_items=len(records),
            items_by_type=items_by_type,
            summary_text=summary_text,
        )
