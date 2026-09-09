"""Interactive Clarification Requests, Minimum Questions, and Safe Defaults (Task 48)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger("kairo.intent.clarification")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ClarificationRequest:
    """Targeted, minimal question requested from user to resolve ambiguity (Spec 58-62).
    
    CRITICAL INVARIANT (Spec 61, 62):
    Only use a default when reasonable, reversible, and low-risk.
    NEVER default destructive/high-impact actions!
    """

    question: str
    reason: str
    affected_decision: str
    intent_id: str
    options: List[str] = field(default_factory=list)
    default_if_any: Optional[str] = None
    is_destructive: bool = False
    clarification_id: str = field(default_factory=lambda: f"clar_{uuid.uuid4().hex[:8]}")
    status: str = "PENDING"  # PENDING, ANSWERED, EXPIRED, CANCELLED
    response: Optional[str] = None
    created_at: datetime = field(default_factory=utc_now)
    answered_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        # Enforce Spec 62: Never default destructive actions!
        if self.is_destructive and self.default_if_any is not None:
            logger.warning("Dangerous default removed from destructive clarification %s", self.clarification_id)
            self.default_if_any = None

    def record_answer(self, user_answer: str) -> None:
        self.response = user_answer
        self.status = "ANSWERED"
        self.answered_at = utc_now()
        logger.info("Clarification %s answered: '%s'", self.clarification_id, user_answer)

    @property
    def selected_answer(self) -> Optional[str]:
        return self.response

    @property
    def is_resolved(self) -> bool:
        return self.status == "ANSWERED"


    def to_dict(self) -> Dict[str, Any]:
        return {
            "clarification_id": self.clarification_id,
            "intent_id": self.intent_id,
            "question": self.question,
            "reason": self.reason,
            "affected_decision": self.affected_decision,
            "options": self.options,
            "default_if_any": self.default_if_any,
            "is_destructive": self.is_destructive,
            "status": self.status,
            "response": self.response,
            "created_at": self.created_at.isoformat(),
            "answered_at": self.answered_at.isoformat() if self.answered_at else None,
        }


class ClarificationManager:
    """Coordinates and deduplicates clarification requests to avoid user interrogation fatigue (Spec 58-62)."""

    def __init__(self) -> None:
        # clarification_id -> ClarificationRequest
        self._requests: Dict[str, ClarificationRequest] = {}

    def create_request(
        self,
        intent_id: str,
        question: str,
        reason: str,
        affected_decision: str,
        options: Optional[List[str]] = None,
        default_if_any: Optional[str] = None,
        is_destructive: bool = False,
    ) -> ClarificationRequest:
        req = ClarificationRequest(
            intent_id=intent_id,
            question=question,
            reason=reason,
            affected_decision=affected_decision,
            options=options or [],
            default_if_any=default_if_any,
            is_destructive=is_destructive,
        )
        self._requests[req.clarification_id] = req
        return req

    def get_pending_clarifications(self, intent_id: Optional[str] = None) -> List[ClarificationRequest]:
        reqs = [r for r in self._requests.values() if r.status == "PENDING"]
        if intent_id:
            reqs = [r for r in reqs if r.intent_id == intent_id]
        return reqs

    def answer_clarification(self, clarification_id: str, answer: str) -> Optional[ClarificationRequest]:
        req = self._requests.get(clarification_id)
        if req:
            req.record_answer(answer)
        return req
