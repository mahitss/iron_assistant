"""Nested Focus Session Manager and Resumption Engine (Task 109, Spec 7, 8, 9, 44, 46, 47).

Manages:
- Bounded nested focus stack (Max depth <= 5)
- Focus transitions and audit logging
- Anti-churn hysteresis and Cognitive Fragmentation detection
- Compact ResumptionContext creation for interrupted work
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from app.attention.domain import (
    AttentionCandidate,
    AttentionLifecycleState,
    CognitiveHealthStatus,
    FocusSession,
    FocusSwitchReason,
    FocusTarget,
    FocusTransition,
    ResumptionContext,
    gen_attn_id,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


class FocusManager:
    """Orchestrates nested focus sessions, preemption stack, and churn monitoring."""

    MAX_STACK_DEPTH = 5
    CHURN_WINDOW_SEC = 300  # 5 minutes
    CHURN_SWITCH_THRESHOLD = 5  # > 5 switches in 5 mins indicates potential churn

    def __init__(self) -> None:
        self.active_session: Optional[FocusSession] = None
        self.stack: List[FocusSession] = []
        self.transitions: List[FocusTransition] = []
        self.recent_switches: List[Tuple[str, datetime]] = []

    def current_depth(self) -> int:
        return len(self.stack)

    def can_push(self) -> bool:
        return self.current_depth() < self.MAX_STACK_DEPTH

    def detect_focus_churn(self) -> Tuple[bool, float, str]:
        """Detects pathological rapid focus switching without progress (Spec 44).

        Returns:
            (is_churn, fragmentation_score, explanation)
        """
        now = utc_now()
        # Clean expired switch records
        self.recent_switches = [
            (target, ts)
            for target, ts in self.recent_switches
            if (now - ts).total_seconds() <= self.CHURN_WINDOW_SEC
        ]

        switch_count = len(self.recent_switches)
        if switch_count < 3:
            return False, 0.0, "Focus switching rate normal."

        targets = [t for t, _ in self.recent_switches]
        unique_targets = len(set(targets))
        # Fragmentation score based on rapid oscillation across distinct targets
        fragmentation = round(min(1.0, (switch_count / 10.0) * (unique_targets / max(1, switch_count))), 3)

        if switch_count >= self.CHURN_SWITCH_THRESHOLD:
            reason = (
                f"Cognitive Fragmentation Alert: {switch_count} focus switches across "
                f"{unique_targets} targets in past {self.CHURN_WINDOW_SEC}s (score={fragmentation})."
            )
            return True, fragmentation, reason

        return False, fragmentation, f"Moderate switching activity (score={fragmentation})."

    def enter_focus(
        self,
        candidate: AttentionCandidate,
        target: FocusTarget,
        reason: FocusSwitchReason = FocusSwitchReason.USER_REQUEST,
        switching_cost: float = 0.2,
        expected_duration_sec: int = 300,
        interruption_policy: str = "NORMAL",
        save_current_context_fn: Optional[Any] = None,
    ) -> Tuple[FocusSession, Optional[FocusTransition]]:
        """Transitions active focus to a new candidate, pushing current focus to the stack."""
        now = utc_now()
        transition: Optional[FocusTransition] = None

        if self.active_session:
            if not self.can_push():
                raise RuntimeError(
                    f"Maximum focus nesting depth ({self.MAX_STACK_DEPTH}) reached. "
                    "Cannot push further nested focus sessions."
                )

            # Preserve state of current session into ResumptionContext
            resumption = (
                save_current_context_fn()
                if save_current_context_fn
                else ResumptionContext(
                    objective=self.active_session.primary_target.name,
                    progress_summary="Work in progress when interrupted",
                    saved_at=now,
                )
            )
            self.active_session.resumption_context = resumption
            self.active_session.is_active = False
            self.stack.append(self.active_session)

            transition = FocusTransition(
                previous_target=self.active_session.primary_target.target_id,
                new_target=target.target_id,
                reason=reason,
                trigger_candidate_id=candidate.candidate_id,
                switching_cost=switching_cost,
                timestamp=now,
                details=f"Pushed session {self.active_session.session_id} to stack (depth {len(self.stack)})",
            )
            self.transitions.append(transition)
            self.recent_switches.append((target.target_id, now))
        else:
            transition = FocusTransition(
                previous_target=None,
                new_target=target.target_id,
                reason=reason,
                trigger_candidate_id=candidate.candidate_id,
                switching_cost=0.0,
                timestamp=now,
                details="Initial focus session allocated.",
            )
            self.transitions.append(transition)
            self.recent_switches.append((target.target_id, now))

        parent_id = self.stack[-1].session_id if self.stack else None
        session = FocusSession(
            parent_session_id=parent_id,
            depth=len(self.stack),
            primary_target=target,
            candidate_id=candidate.candidate_id,
            reason=reason,
            start_time=now,
            expected_duration_sec=expected_duration_sec,
            interruption_policy=interruption_policy,
            is_active=True,
        )
        self.active_session = session
        candidate.lifecycle = AttentionLifecycleState.FOCUSED

        return session, transition

    def complete_focus(
        self,
        session_id: Optional[str] = None,
        reason: str = "Objective accomplished",
    ) -> Tuple[Optional[FocusSession], Optional[FocusSession]]:
        """Completes active focus and pops the previous session from stack to resume work.

        Returns:
            (completed_session, resumed_session)
        """
        if not self.active_session:
            return None, None

        completed = self.active_session
        completed.is_active = False
        completed.end_time = utc_now()
        completed.success_condition = reason

        resumed: Optional[FocusSession] = None
        if self.stack:
            resumed = self.stack.pop()
            resumed.is_active = True
            self.active_session = resumed

            trans = FocusTransition(
                previous_target=completed.primary_target.target_id,
                new_target=resumed.primary_target.target_id,
                reason=FocusSwitchReason.FOCUS_COMPLETED,
                trigger_candidate_id=resumed.candidate_id,
                switching_cost=0.1,
                timestamp=utc_now(),
                details=f"Popped session {resumed.session_id} from stack upon completing {completed.session_id}",
            )
            self.transitions.append(trans)
        else:
            self.active_session = None

        return completed, resumed

    def abort_focus(self, reason: str = "Cancelled") -> Tuple[Optional[FocusSession], Optional[FocusSession]]:
        """Aborts current focus session and pops next available from stack."""
        return self.complete_focus(reason=f"Aborted: {reason}")
