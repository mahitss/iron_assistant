"""Explicit 17-State Lifecycle Recovery & Resilience State Machine (Task 76).

Validates and executes transitions across:
DETECTED -> ASSESSED -> CONTAINMENT_PLANNED -> CONTAINMENT_PENDING_APPROVAL
-> CONTAINMENT_EXECUTING -> CONTAINED -> RECOVERY_PLANNED
-> RECOVERY_PENDING_APPROVAL -> RECOVERY_EXECUTING -> RECOVERY_VERIFICATION
-> RECOVERY_MONITORING -> RECOVERED (or PARTIALLY_RECOVERED, RECOVERY_FAILED,
ROLLED_BACK, HUMAN_REQUIRED, ABORTED).
"""

from datetime import UTC, datetime
from typing import Any

from app.resilience.defense_schemas import (
    VALID_RECOVERY_TRANSITIONS,
    VALID_RESILIENCE_TRANSITIONS,
    RecoveryLifecycleState,
    RecoveryPlan,
    ResilienceAssessment,
    ResilienceState,
    utc_now,
)


class InvalidRecoveryTransitionError(ValueError):
    """Raised when an illegal transition is attempted on a RecoveryPlan."""
    pass


class InvalidResilienceTransitionError(ValueError):
    """Raised when an illegal transition is attempted on a ResilienceAssessment."""
    pass


class RecoveryStateMachine:
    """Manages verified state transitions for recovery plans and assessments."""

    def __init__(self) -> None:
        self.transition_history: list[dict[str, Any]] = []

    def can_transition_recovery(
        self,
        current_state: RecoveryLifecycleState,
        target_state: RecoveryLifecycleState,
    ) -> bool:
        """Checks if a transition between recovery states is allowed."""
        if current_state == target_state:
            return True
        allowed = VALID_RECOVERY_TRANSITIONS.get(current_state, set())
        return target_state in allowed

    def transition_recovery_plan(
        self,
        plan: RecoveryPlan,
        target_state: RecoveryLifecycleState,
        reason: str = "",
        actor: str = "system",
    ) -> RecoveryPlan:
        """Transitions a recovery plan to a new verified state."""
        current = plan.state
        if not self.can_transition_recovery(current, target_state):
            raise InvalidRecoveryTransitionError(
                f"Cannot transition RecoveryPlan {plan.plan_id} from {current.value} to {target_state.value}. "
                f"Valid next states: {[s.value for s in VALID_RECOVERY_TRANSITIONS.get(current, set())]}"
            )

        old_state = plan.state
        plan.state = target_state
        plan.updated_at = utc_now()

        event_record = {
            "plan_id": plan.plan_id,
            "from_state": old_state.value,
            "to_state": target_state.value,
            "reason": reason,
            "actor": actor,
            "timestamp": utc_now().isoformat(),
        }
        self.transition_history.append(event_record)
        return plan

    def can_transition_resilience(
        self,
        current_state: ResilienceState,
        target_state: ResilienceState,
    ) -> bool:
        """Checks if a transition between resilience assessment states is allowed."""
        if current_state == target_state:
            return True
        allowed = VALID_RESILIENCE_TRANSITIONS.get(current_state, set())
        return target_state in allowed

    def transition_resilience_assessment(
        self,
        assessment: ResilienceAssessment,
        target_state: ResilienceState,
        reason: str = "",
    ) -> ResilienceAssessment:
        """Transitions a resilience assessment to a new verified state."""
        current = assessment.state
        if not self.can_transition_resilience(current, target_state):
            raise InvalidResilienceTransitionError(
                f"Cannot transition ResilienceAssessment {assessment.resilience_assessment_id} from {current.value} to {target_state.value}. "
                f"Valid next states: {[s.value for s in VALID_RESILIENCE_TRANSITIONS.get(current, set())]}"
            )

        assessment.state = target_state
        assessment.updated_at = utc_now()
        return assessment
