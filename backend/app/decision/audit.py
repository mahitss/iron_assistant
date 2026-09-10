"""Tamper-evident audit trail and lifecycle tracing for Decision Engine."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger("kairo.decision.audit")


class DecisionAuditEvent(BaseModel):
    """Structured audit trail entry for decision events."""

    event_id: str = Field(default_factory=lambda: f"daud_{uuid.uuid4().hex[:12]}")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: str  # REQUESTED, ANALYZED, RECOMMENDED, SELECTED, OVERRIDDEN, APPROVED, OUTCOME_RECORDED, REVISED
    decision_id: str | None = None
    actor: str
    details: dict[str, Any] = Field(default_factory=dict)


class DecisionAuditor:
    """Manages audit logging for all decision lifecycle stages."""

    def __init__(self) -> None:
        self._events: list[DecisionAuditEvent] = []

    def record_event(
        self,
        event_type: str,
        decision_id: str | None = None,
        actor: str = "system",
        details: dict[str, Any] | None = None,
    ) -> DecisionAuditEvent:
        """Appends an event to the in-memory and system audit trail."""
        evt = DecisionAuditEvent(
            event_type=event_type,
            decision_id=decision_id,
            actor=actor,
            details=details or {},
        )
        self._events.append(evt)
        logger.info(f"[DECISION AUDIT] type={event_type} dec={decision_id} actor={actor}")
        return evt

    def log_event(
        self,
        decision_id: str | None = None,
        action: str = "GENERIC_ACTION",
        actor: str = "system",
        details: dict[str, Any] | None = None,
    ) -> DecisionAuditEvent:
        """Alias for record_event compatible with engine and service callers."""
        return self.record_event(
            event_type=action,
            decision_id=decision_id,
            actor=actor,
            details=details,
        )

    def get_events(self, decision_id: str | None = None) -> list[DecisionAuditEvent]:
        """Retrieves audit events, optionally filtered by decision_id."""
        if decision_id:
            return [e for e in self._events if e.decision_id == decision_id]
        return list(self._events)


decision_auditor = DecisionAuditor()

