"""Governance State Machine: 8-state lifecycle and validated state transitions (Task 78)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.policy.governance_schemas import GovernanceDecisionType, GovernanceState

logger = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class GovernanceTransitionError(Exception):
    """Raised when an illegal governance state transition is attempted."""


class GovernanceStateMachine:
    """Validates and enforces legal state transitions across the 8-state governance lifecycle."""

    # Explicit directed transition graph
    VALID_TRANSITIONS: dict[GovernanceState, set[GovernanceState]] = {
        GovernanceState.PENDING_REVIEW: {
            GovernanceState.APPROVED,
            GovernanceState.DENIED,
            GovernanceState.REQUIRES_APPROVAL,
            GovernanceState.REQUIRES_HUMAN,
            GovernanceState.ABORTED,
        },
        GovernanceState.REQUIRES_APPROVAL: {
            GovernanceState.APPROVED,
            GovernanceState.DENIED,
            GovernanceState.EXPIRED,
            GovernanceState.ABORTED,
        },
        GovernanceState.REQUIRES_HUMAN: {
            GovernanceState.APPROVED,
            GovernanceState.DENIED,
            GovernanceState.EXPIRED,
            GovernanceState.ABORTED,
        },
        GovernanceState.APPROVED: {
            GovernanceState.EXECUTABLE,
            GovernanceState.EXPIRED,
            GovernanceState.ABORTED,
        },
        GovernanceState.EXECUTABLE: {
            GovernanceState.EXPIRED,
            GovernanceState.ABORTED,
        },
        GovernanceState.DENIED: set(),       # Terminal
        GovernanceState.EXPIRED: set(),      # Terminal
        GovernanceState.ABORTED: set(),      # Terminal
    }

    @classmethod
    def can_transition(cls, current: GovernanceState, target: GovernanceState) -> bool:
        """Check if transition from current to target is legally allowed."""
        return target in cls.VALID_TRANSITIONS.get(current, set())

    @classmethod
    def transition(cls, current: GovernanceState, target: GovernanceState) -> GovernanceState:
        """Execute validated state transition or raise GovernanceTransitionError."""
        if not cls.can_transition(current, target):
            raise GovernanceTransitionError(
                f"Illegal governance transition: {current.value} -> {target.value}. "
                f"Allowed destinations: {[s.value for s in cls.VALID_TRANSITIONS.get(current, set())]}"
            )
        logger.info("Governance state transition: %s -> %s", current.value, target.value)
        return target

    @classmethod
    def determine_initial_state(
        cls,
        decision: GovernanceDecisionType,
    ) -> GovernanceState:
        """Map initial evaluation decision to initial governance lifecycle state."""
        if decision == GovernanceDecisionType.ALLOWED:
            return GovernanceState.EXECUTABLE
        elif decision == GovernanceDecisionType.DENIED:
            return GovernanceState.DENIED
        elif decision == GovernanceDecisionType.REQUIRES_APPROVAL:
            return GovernanceState.REQUIRES_APPROVAL
        elif decision == GovernanceDecisionType.REQUIRES_HUMAN:
            return GovernanceState.REQUIRES_HUMAN
        elif decision == GovernanceDecisionType.CONFLICTING_POLICY:
            return GovernanceState.REQUIRES_HUMAN
        else:
            return GovernanceState.PENDING_REVIEW

    @classmethod
    def build_human_handoff_packet(
        cls,
        review_id: str,
        action: str,
        resource: str,
        risk_level: str,
        uncertainty_score: float = 0.0,
        evidence: list[str] | None = None,
        reason: str = "",
        constitutional_score: float = 1.0,
        suggested_decision: Any = None,
    ) -> dict[str, Any]:
        """Construct structured handoff packet for operator intervention."""
        return {
            "handoff_id": f"hnd_{review_id}",
            "review_id": review_id,
            "action": action,
            "resource": resource,
            "risk_level": risk_level,
            "uncertainty_score": uncertainty_score,
            "constitutional_score": constitutional_score,
            "suggested_decision": getattr(suggested_decision, "value", str(suggested_decision)),
            "reason_for_human": reason or "Action requires human oversight and sign-off.",
            "evidence": evidence or [],
            "options": [
                {"action": "APPROVE", "label": "Authorize Execution", "consequence": "Action will proceed to EXECUTABLE"},
                {"action": "DENY", "label": "Reject Action", "consequence": "Action will terminate as DENIED"},
            ],
            "created_at": _now_utc().isoformat(),
        }


default_state_machine = GovernanceStateMachine()
