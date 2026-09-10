"""Structured audit trail and lifecycle tracing for Strategic Planning (Task 58)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger("kairo.planning.audit")


class PlanAuditEvent(BaseModel):
    """Structured audit trail entry for strategic planning events."""

    event_id: str = Field(default_factory=lambda: f"paud_{uuid.uuid4().hex[:12]}")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: str  # PLAN_CREATED, PLAN_REVISED, PHASE_STARTED, MILESTONE_REACHED, TASK_STARTED, CHECKPOINT_EVALUATED, etc.
    plan_id: str | None = None
    actor: str = "system"
    details: dict[str, Any] = Field(default_factory=dict)


class PlanAuditor:
    """Records tamper-evident planning events."""

    def __init__(self) -> None:
        self._events: list[PlanAuditEvent] = []

    def record_event(
        self,
        event_type: str = "GENERIC_EVENT",
        plan_id: str | None = None,
        actor: str = "system",
        details: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> PlanAuditEvent:
        """Appends an event to the in-memory audit trail and emits structured log."""
        evt_type = event_type or kwargs.get("action", "GENERIC_EVENT")
        evt = PlanAuditEvent(
            event_type=evt_type,
            plan_id=plan_id,
            actor=actor,
            details=details or {},
        )
        self._events.append(evt)
        logger.info(f"[PLAN AUDIT] type={evt_type} plan={plan_id} actor={actor}")
        return evt

    def log_event(
        self,
        plan_id: str | None = None,
        action: str = "GENERIC_ACTION",
        actor: str = "system",
        details: dict[str, Any] | None = None,
    ) -> PlanAuditEvent:
        """Alias for record_event compatible with service callers."""
        return self.record_event(
            event_type=action,
            plan_id=plan_id,
            actor=actor,
            details=details,
        )

    def get_events(self, plan_id: str | None = None) -> list[PlanAuditEvent]:
        if plan_id:
            return [e for e in self._events if e.plan_id == plan_id]
        return list(self._events)

    def get_plan_events(self, plan_id: str | None = None) -> list[dict[str, Any]]:
        """Return serialized audit events for a plan."""
        return [e.model_dump(mode="json") for e in self.get_events(plan_id)]


plan_auditor = PlanAuditor()
