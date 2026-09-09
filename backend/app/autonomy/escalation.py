"""Human-in-the-Loop Escalation and Approval Checkpoints (Task 45)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger("kairo.autonomy.escalation")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EscalationReason(str, Enum):
    AUTHORIZATION_MISSING = "AUTHORIZATION_MISSING"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    POLICY_AMBIGUITY = "POLICY_AMBIGUITY"
    REPEATED_FAILURE = "REPEATED_FAILURE"
    CRITICAL_UNCERTAINTY = "CRITICAL_UNCERTAINTY"
    EXTERNAL_DEPENDENCY_UNAVAILABLE = "EXTERNAL_DEPENDENCY_UNAVAILABLE"
    GOAL_IMPOSSIBLE = "GOAL_IMPOSSIBLE"


@dataclass
class EscalationRequest:
    """A minimal, targeted human-in-the-loop escalation query (Spec 115, 116)."""

    escalation_id: str
    run_id: str
    reason: EscalationReason
    question: str
    context_summary: str
    suggested_options: List[str] = field(default_factory=list)
    action_data: Dict[str, Any] = field(default_factory=dict)
    status: str = "PENDING"  # PENDING, RESOLVED, EXPIRED
    resolution: Optional[str] = None
    created_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "escalation_id": self.escalation_id,
            "run_id": self.run_id,
            "reason": self.reason.value,
            "question": self.question,
            "context_summary": self.context_summary,
            "suggested_options": self.suggested_options,
            "action_data": self.action_data,
            "status": self.status,
            "resolution": self.resolution,
            "created_at": self.created_at.isoformat(),
        }


class EscalationManager:
    """Manages escalation to human operators while avoiding needless questions (Spec 115-124)."""

    def __init__(self) -> None:
        self._pending: Dict[str, EscalationRequest] = {}

    def should_escalate(
        self,
        reason: EscalationReason,
        failure_count: int = 0,
        max_failures: int = 3,
        has_deterministic_fallback: bool = False,
    ) -> bool:
        """Enforce Spec 117: Do not ask needless questions if a safe deterministic fallback exists."""
        if has_deterministic_fallback:
            return False
        if reason in [EscalationReason.AUTHORIZATION_MISSING, EscalationReason.APPROVAL_REQUIRED, EscalationReason.GOAL_IMPOSSIBLE]:
            return True
        return failure_count >= max_failures

    def create_escalation(
        self,
        run_id: str,
        reason: EscalationReason,
        question: str,
        context_summary: str,
        suggested_options: Optional[List[str]] = None,
        action_data: Optional[Dict[str, Any]] = None,
    ) -> EscalationRequest:
        """Create targeted escalation request with minimal necessary context (Spec 116)."""
        esc_id = f"esc_{uuid.uuid4().hex[:10]}"
        req = EscalationRequest(
            escalation_id=esc_id,
            run_id=run_id,
            reason=reason,
            question=question,
            context_summary=context_summary,
            suggested_options=suggested_options or ["Approve", "Reject", "Abort"],
            action_data=action_data or {},
        )
        self._pending[esc_id] = req
        logger.warning("Created human escalation [%s] for run %s: %s", reason.value, run_id, question)
        return req

    def resolve_escalation(self, escalation_id: str, decision: str) -> EscalationRequest:
        req = self._pending.get(escalation_id)
        if not req:
            raise KeyError(f"Escalation {escalation_id} not found.")
        req.status = "RESOLVED"
        req.resolution = decision
        return req
