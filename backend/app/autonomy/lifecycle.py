"""Autonomous Run Lifecycle Manager, Wait States, and Ownership Validation (Task 45)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
from typing import Any, Callable, Dict, List, Optional

from app.autonomy.state import AutonomousRunState, can_transition

logger = logging.getLogger("kairo.autonomy.lifecycle")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class InvalidStateTransitionError(Exception):
    """Raised when an autonomous run attempts an illegal state transition (Spec 3)."""


class WaitConditionType(str, Enum):
    APPROVAL = "APPROVAL"
    USER_INPUT = "USER_INPUT"
    EXTERNAL_DEPENDENCY = "EXTERNAL_DEPENDENCY"
    SCHEDULED_TIME = "SCHEDULED_TIME"
    RATE_LIMIT = "RATE_LIMIT"
    RESOURCE = "RESOURCE"


@dataclass
class WaitStateRecord:
    """Detailed record of why a run entered WAITING status and what condition triggers resume (Spec 62-64)."""

    condition_type: WaitConditionType
    reason: str
    resume_condition: Dict[str, Any]
    entered_at: datetime = field(default_factory=utc_now)
    expires_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "condition_type": self.condition_type.value,
            "reason": self.reason,
            "resume_condition": self.resume_condition,
            "entered_at": self.entered_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class RunLifecycleManager:
    """Orchestrates transitions between the 14 lifecycle states and tracks wait conditions (Spec 3, 4, 62-64)."""

    def __init__(self) -> None:
        # run_id -> WaitStateRecord
        self._wait_states: Dict[str, WaitStateRecord] = {}
        # run_id -> list of transition logs
        self._transition_history: Dict[str, List[Dict[str, Any]]] = {}

    def transition_state(
        self,
        run_id: str,
        current: AutonomousRunState,
        target: AutonomousRunState,
        reason: str = "",
        on_transition_hook: Optional[Callable[[str, AutonomousRunState, AutonomousRunState], None]] = None,
    ) -> AutonomousRunState:
        """Enforce strict legal transitions across the 14 lifecycle states (Spec 3)."""
        if not can_transition(current, target):
            logger.error("Illegal state transition on run %s: %s -> %s", run_id, current.value, target.value)
            raise InvalidStateTransitionError(
                f"Illegal state transition for run {run_id}: Cannot transition from {current.value} to {target.value}."
            )

        log_entry = {
            "from_state": current.value,
            "to_state": target.value,
            "reason": reason,
            "timestamp": utc_now().isoformat(),
        }
        self._transition_history.setdefault(run_id, []).append(log_entry)
        logger.info("Run %s transitioned %s -> %s (%s)", run_id, current.value, target.value, reason)

        # Clear wait state if transitioning away from WAITING
        if current == AutonomousRunState.WAITING and target != AutonomousRunState.WAITING:
            self._wait_states.pop(run_id, None)

        if on_transition_hook:
            try:
                on_transition_hook(run_id, current, target)
            except Exception as exc:
                logger.warning("Error running transition hook: %s", exc)

        return target

    def enter_wait_state(
        self,
        run_id: str,
        current: AutonomousRunState,
        condition_type: WaitConditionType,
        reason: str,
        resume_condition: Dict[str, Any],
        expires_at: Optional[datetime] = None,
    ) -> AutonomousRunState:
        """Transition run to WAITING with explicit, durable resume condition (Spec 62-64)."""
        new_state = self.transition_state(
            run_id=run_id,
            current=current,
            target=AutonomousRunState.WAITING,
            reason=f"Waiting on {condition_type.value}: {reason}",
        )
        record = WaitStateRecord(
            condition_type=condition_type,
            reason=reason,
            resume_condition=resume_condition,
            expires_at=expires_at,
        )
        self._wait_states[run_id] = record
        return new_state

    def get_wait_state(self, run_id: str) -> Optional[WaitStateRecord]:
        return self._wait_states.get(run_id)

    def check_resume_condition(self, run_id: str, current_context: Dict[str, Any]) -> bool:
        """Evaluate whether condition required to resume from WAITING is satisfied (Spec 64)."""
        wait_rec = self._wait_states.get(run_id)
        if not wait_rec:
            return True

        cond = wait_rec.resume_condition
        expected_event = cond.get("event")
        if expected_event and current_context.get("event") == expected_event:
            return True

        expected_approval = cond.get("approval_id")
        if expected_approval and current_context.get("approved") is True and current_context.get("approval_id") == expected_approval:
            return True

        return False

    def get_history(self, run_id: str) -> List[Dict[str, Any]]:
        return self._transition_history.get(run_id, [])
