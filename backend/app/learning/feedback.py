"""User feedback ingestion, rate-limiting, and anti-poisoning defenses (Task 43)."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger("kairo.learning.feedback")


def utc_now() -> datetime:
    return datetime.now(UTC)


class FeedbackItem(BaseModel):
    """User feedback entry with rating, sentiment, and scope (Spec 11)."""

    model_config = ConfigDict(extra="ignore")

    feedback_id: str = Field(default_factory=lambda: f"fb_{uuid.uuid4().hex[:10]}")
    user_id: str = "default_user"
    project_id: str | None = None
    target_id: str = Field(..., description="ID of plan, task, or strategy evaluated")
    feedback_type: str = Field(..., description="positive, negative, correction, preference, rating")
    rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = None
    scope: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "feedback_id": self.feedback_id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "target_id": self.target_id,
            "feedback_type": self.feedback_type,
            "rating": self.rating,
            "comment": self.comment,
            "scope": self.scope,
            "created_at": self.created_at.isoformat(),
        }


class FeedbackIngestor:
    """Ingests user feedback with rate limiting and poisoning anomaly detection (Spec 162-165)."""

    def __init__(self, rate_limit_per_minute: int = 10) -> None:
        self.rate_limit = rate_limit_per_minute
        # user_id -> list of submission datetimes
        self._rate_windows: dict[str, list[datetime]] = {}
        self._history: list[FeedbackItem] = []

    def check_rate_limit(self, user_id: str) -> bool:
        """Check whether user has exceeded feedback submission velocity."""
        now = utc_now()
        one_min_ago = now - timedelta(minutes=1)

        window = self._rate_windows.setdefault(user_id, [])
        # Purge timestamps older than 1 minute
        window[:] = [t for t in window if t > one_min_ago]

        if len(window) >= self.rate_limit:
            logger.warning("Feedback rate limit exceeded for user '%s'", user_id)
            return False

        window.append(now)
        return True

    def ingest(self, item: FeedbackItem) -> tuple[bool, str]:
        """Ingest feedback with safety and rate-limit guardrails."""
        if not self.check_rate_limit(item.user_id):
            return False, "Rate limit exceeded: too many feedback submissions within 1 minute."

        # Safety boundary check (Spec 12): User feedback cannot alter security or policy directly
        comment_lower = (item.comment or "").lower()
        if any(term in comment_lower for term in ["bypass security", "grant root", "override policy", "disable auth"]):
            logger.warning("Feedback injection attempt rejected for user '%s': %s", item.user_id, item.comment)
            return False, "Feedback contains prohibited policy override instructions."

        self._history.append(item)
        return True, "Feedback accepted"

    def list_feedback(self, target_id: str | None = None) -> list[FeedbackItem]:
        if target_id:
            return [f for f in self._history if f.target_id == target_id]
        return list(self._history)
