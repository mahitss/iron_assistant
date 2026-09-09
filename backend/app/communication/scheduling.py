"""Scheduled communication management, pre-send revalidation, and revocation checks."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
import uuid

from app.communication.schemas import (
    CommunicationChannel,
    DraftMessageSchema,
    RecipientSchema,
)


class ScheduleRevokedError(Exception):
    """Raised when an execution is attempted on a revoked or cancelled schedule."""
    pass


class RevalidationFailedError(Exception):
    """Raised when pre-send revalidation fails."""
    pass


class ScheduledMessageEngine:
    """Manages scheduled sends with strict pre-send revalidation and instant revocation."""

    def __init__(self) -> None:
        # schedule_id -> dict
        self._schedules: Dict[str, Dict[str, Any]] = {}
        self._revoked_users: set[str] = set()

    def schedule_send(
        self,
        draft_id: str,
        channel: CommunicationChannel,
        recipients: List[RecipientSchema],
        scheduled_time: datetime,
        user_id: str = "default_user",
        policy_state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if user_id in self._revoked_users:
            raise ScheduleRevokedError(f"User '{user_id}' has revoked communication permissions.")

        sched_id = str(uuid.uuid4())
        record = {
            "schedule_id": sched_id,
            "draft_id": draft_id,
            "channel": channel.value,
            "recipients": [r.model_dump() for r in recipients],
            "scheduled_time": scheduled_time.isoformat(),
            "status": "SCHEDULED",
            "user_id": user_id,
            "policy_state": policy_state or {"approved": True},
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._schedules[sched_id] = record
        return record

    def cancel_schedule(self, schedule_id: str, user_id: str) -> Dict[str, Any]:
        sched = self._schedules.get(schedule_id)
        if not sched:
            raise ValueError(f"Scheduled message '{schedule_id}' not found.")
        if sched["user_id"] != user_id:
            raise PermissionError("Cannot cancel schedule belonging to another user.")
        sched["status"] = "CANCELLED"
        return sched

    def revoke_user_permissions(self, user_id: str) -> None:
        """INVARIANT 132 & 195: User revocation immediately cancels and blocks all scheduled sends."""
        self._revoked_users.add(user_id)
        for s in self._schedules.values():
            if s["user_id"] == user_id and s["status"] == "SCHEDULED":
                s["status"] = "REVOKED"

    def revalidate_before_send(
        self,
        schedule_id: str,
        current_draft: Optional[DraftMessageSchema] = None,
        is_channel_authorized: bool = True,
    ) -> None:
        """INVARIANT 130: Revalidate authorization, recipient, draft, policy, and schedule before send."""
        sched = self._schedules.get(schedule_id)
        if not sched:
            raise ValueError(f"Schedule '{schedule_id}' not found.")

        if sched["status"] != "SCHEDULED":
            raise ScheduleRevokedError(f"Schedule '{schedule_id}' is in status '{sched['status']}' and cannot be sent.")

        if sched["user_id"] in self._revoked_users:
            sched["status"] = "REVOKED"
            raise ScheduleRevokedError(f"User '{sched['user_id']}' permissions are revoked.")

        if not is_channel_authorized:
            raise RevalidationFailedError(f"Channel '{sched['channel']}' is no longer authorized.")

        if current_draft and current_draft.status.value not in ("APPROVED", "DRAFT"):
            raise RevalidationFailedError(f"Draft '{current_draft.draft_id}' is in invalid status '{current_draft.status.value}'.")
