"""Follow-up tracking, trigger handling, bounded anti-spam limits, and response interpretation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import logging
import re
from typing import Any, Dict, List, Optional
import uuid

from app.communication.schemas import (
    FollowUpSchema,
    FollowUpTrigger,
    MessageSchema,
)

logger = logging.getLogger(__name__)


class FollowUpLimitExceededError(Exception):
    """Raised when automated follow-up attempts exceed configured anti-spam bounds."""
    pass


class FollowUpEngine:
    """Manages scheduled follow-ups, trigger evaluation, and bounds on automated messaging."""

    def __init__(self, max_default_attempts: int = 3) -> None:
        self.max_default_attempts = max_default_attempts
        # followup_id -> FollowUpSchema
        self._followups: Dict[str, FollowUpSchema] = {}

    def schedule_followup(
        self,
        thread_id: str,
        owner: str,
        action: str,
        due_at: Optional[datetime] = None,
        trigger: FollowUpTrigger = FollowUpTrigger.NO_RESPONSE,
        max_attempts: Optional[int] = None,
        user_id: str = "default_user",
    ) -> FollowUpSchema:
        f_id = str(uuid.uuid4())
        limit = max_attempts if max_attempts is not None else self.max_default_attempts
        target_due = due_at or (datetime.now(UTC) + timedelta(days=2))

        fu = FollowUpSchema(
            followup_id=f_id,
            thread_id=thread_id,
            trigger=trigger,
            owner=owner,
            due_at=target_due,
            action=action,
            status="OPEN",
            attempts_count=0,
            max_attempts=limit,
            user_id=user_id,
        )
        self._followups[f_id] = fu
        return fu

    def record_attempt(self, followup_id: str) -> FollowUpSchema:
        fu = self._followups.get(followup_id)
        if not fu:
            raise ValueError(f"FollowUp '{followup_id}' not found.")

        # INVARIANT 34 & 134: Bound follow-up attempts to prevent infinite follow-up loops / spam
        if fu.attempts_count >= fu.max_attempts:
            fu.status = "EXHAUSTED"
            raise FollowUpLimitExceededError(
                f"Follow-up {followup_id} has reached its maximum attempts limit ({fu.max_attempts}). Stopping to prevent spam."
            )

        fu.attempts_count += 1
        if fu.attempts_count >= fu.max_attempts:
            fu.status = "EXHAUSTED"
        return fu

    def interpret_response(self, message: MessageSchema) -> str:
        """INVARIANT 136: Distinguish no response, negative response, positive response, and ambiguous response.

        Silence (no response) is NOT necessarily rejection.
        """
        text = message.content_reference.lower()
        # Check ambiguous expressions first
        if any(w in text for w in ["maybe", "not sure", "depends", "let me check", "checking", "tentative"]):
            return "ambiguous_response"

        # Check negative response with word boundaries to avoid matching 'no' inside 'not'
        negative_keywords = ["no", "decline", "reject", "cancel", "not interested", "stop"]
        if any(re.search(rf"\b{re.escape(w)}\b", text) for w in negative_keywords):
            return "negative_response"

        # Check positive response
        if any(w in text for w in ["yes", "approved", "sounds good", "let's do it", "agreed", "confirmed"]):
            return "positive_response"

        return "informational_response"

    def list_pending_followups(self, user_id: Optional[str] = None) -> List[FollowUpSchema]:
        now = datetime.now(UTC)
        results = [
            fu for fu in self._followups.values()
            if fu.status == "OPEN" and fu.due_at <= now
        ]
        if user_id:
            results = [fu for fu in results if fu.user_id == user_id]
        return results
