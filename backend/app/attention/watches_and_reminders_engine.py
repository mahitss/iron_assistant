"""Bounded Condition Watches & Reminder Engine (Task 109, Spec 36, 37, 38).

Supports:
- Zero-cost cognitive waiting states (WAITING_FOR_EVIDENCE, WAITING_FOR_USER, etc.)
- Trigger evaluation when external events or signals arrive
- Time-based reminders for deferred candidates
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Tuple

from app.attention.domain import (
    AttentionCandidate,
    AttentionLifecycleState,
    AttentionReminder,
    AttentionWatch,
    WaitingConditionType,
    gen_attn_id,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


class WatchesAndRemindersEngine:
    """Manages low-overhead condition watches and scheduled reminders."""

    def __init__(self) -> None:
        self.watches: Dict[str, AttentionWatch] = {}  # watch_id -> watch
        self.reminders: Dict[str, AttentionReminder] = {}  # reminder_id -> reminder

    def create_watch(
        self,
        candidate_id: str,
        condition_type: WaitingConditionType,
        condition_expr: str,
        reconsideration_trigger: str,
    ) -> AttentionWatch:
        """Registers a bounded condition watch for a candidate."""
        watch = AttentionWatch(
            candidate_id=candidate_id,
            condition_type=condition_type,
            condition_expr=condition_expr,
            reconsideration_trigger=reconsideration_trigger,
            created_at=utc_now(),
            is_active=True,
        )
        self.watches[watch.watch_id] = watch
        return watch

    def create_reminder(
        self,
        candidate_id: str,
        trigger_at: datetime,
        reason: str,
    ) -> AttentionReminder:
        """Schedules a time-based reminder for a deferred candidate."""
        reminder = AttentionReminder(
            candidate_id=candidate_id,
            trigger_at=trigger_at,
            reason=reason,
            is_triggered=False,
        )
        self.reminders[reminder.reminder_id] = reminder
        return reminder

    def evaluate_external_signal(
        self,
        event_name: str,
        event_payload: Dict[str, Any],
    ) -> List[Tuple[str, str]]:
        """Evaluates whether an incoming event triggers any active watches.

        Returns:
            List of (watch_id, candidate_id) to reactivate
        """
        reactivated: List[Tuple[str, str]] = []
        for watch_id, watch in list(self.watches.items()):
            if not watch.is_active:
                continue

            # Check if event matches reconsideration trigger or condition
            trigger_match = (
                watch.reconsideration_trigger.lower() in event_name.lower()
                or event_name.lower() in watch.condition_expr.lower()
            )
            if trigger_match:
                watch.is_active = False
                reactivated.append((watch_id, watch.candidate_id))

        return reactivated

    def check_due_reminders(self, current_time: Optional[datetime] = None) -> List[str]:
        """Checks for expired reminders and returns candidate IDs needing re-attention."""
        now = current_time or utc_now()
        due_candidates: List[str] = []
        for reminder_id, rem in self.reminders.items():
            if not rem.is_triggered and rem.trigger_at <= now:
                rem.is_triggered = True
                due_candidates.append(rem.candidate_id)

        return due_candidates
