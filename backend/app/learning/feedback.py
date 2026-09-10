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


# =============================================================================
# TASK 52 FEEDBACK PROCESSOR & WEIGHTING
# =============================================================================

from app.learning.schemas import FeedbackType


class FeedbackProcessor:
    """Processes explicit feedback, user draft edits, and user override enforcement (INVARIANTS 25-29, 121-122)."""

    def __init__(self) -> None:
        self._feedback_records: list[dict[str, Any]] = []
        # user_id -> dict of recurring edit patterns
        self._user_edit_patterns: dict[str, dict[str, int]] = {}

    def process_feedback(
        self,
        target_id: str,
        feedback_type: FeedbackType,
        user_id: str,
        comment: str | None = None,
        edit_diff: dict[str, Any] | None = None,
        is_explicit: bool = True,
    ) -> dict[str, Any]:
        """INVARIANT 26: Explicit feedback receives full weight (1.0). Passive observation gets low weight (0.1)."""
        # INVARIANT 27: Do not assume "User didn't complain" means "User approved"
        weight = 1.0 if is_explicit else 0.1
        if feedback_type in (FeedbackType.CORRECT, FeedbackType.REJECT):
            weight = 1.0  # Corrections always carry authoritative weight

        record = {
            "target_id": target_id,
            "feedback_type": feedback_type.value if hasattr(feedback_type, "value") else str(feedback_type),
            "user_id": user_id,
            "comment": comment,
            "edit_diff": edit_diff or {},
            "is_explicit": is_explicit,
            "weight": weight,
            "timestamp": datetime.now(UTC),
        }
        self._feedback_records.append(record)

        # INVARIANT 28: User edit tracking
        if feedback_type == FeedbackType.EDIT and edit_diff:
            self._track_edit_pattern(user_id, edit_diff)

        return record

    def _track_edit_pattern(self, user_id: str, edit_diff: dict[str, Any]) -> None:
        patterns = self._user_edit_patterns.setdefault(user_id, {})
        edit_key = str(sorted(edit_diff.items()))
        patterns[edit_key] = patterns.get(edit_key, 0) + 1

    def get_candidate_preference_from_edits(self, user_id: str, min_repetitions: int = 3) -> list[str]:
        """INVARIANT 28: Repeated consistent edits create candidate preferences."""
        patterns = self._user_edit_patterns.get(user_id, {})
        return [k for k, count in patterns.items() if count >= min_repetitions]

    def enforce_user_override(
        self,
        learned_preference: Any,
        current_explicit_instruction: str,
    ) -> tuple[bool, str]:
        """INVARIANT 29 & 122: Current explicit instruction strictly overrides learned preference."""
        if current_explicit_instruction and current_explicit_instruction.strip():
            return True, f"Learned preference overridden by current explicit instruction: '{current_explicit_instruction}'"
        return False, "Using learned preference"

