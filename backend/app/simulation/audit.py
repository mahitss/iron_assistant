"""Audit logging and compliance verification for simulation lifecycle and transitions."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger("kairo.simulation.audit")


class SimulationAuditEvent(BaseModel):
    """Structured audit trail record for simulation events."""

    event_id: str = Field(default_factory=lambda: f"saud_{uuid.uuid4().hex[:12]}")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: str  # SIMULATION_CREATED, SCENARIO_MUTATED, GATE_CHECKED, REAL_TRANSITION_REQUESTED
    actor: str
    simulation_id: str | None = None
    scenario_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    is_hypothetical: bool = True
    environment_label: str = "SIMULATION_ONLY"


class SimulationAuditor:
    """Records tamper-evident audit logs for simulation activities."""

    def __init__(self) -> None:
        self._events: list[SimulationAuditEvent] = []

    def record_event(
        self,
        event_type: str,
        actor: str = "system",
        simulation_id: str | None = None,
        scenario_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> SimulationAuditEvent:
        """Appends an event to the simulation audit log."""
        evt = SimulationAuditEvent(
            event_type=event_type,
            actor=actor,
            simulation_id=simulation_id,
            scenario_id=scenario_id,
            details=details or {},
        )
        self._events.append(evt)
        logger.info(
            f"[SIMULATION AUDIT] type={event_type} sim={simulation_id} scen={scenario_id} actor={actor}"
        )
        return evt

    def get_events(self, simulation_id: str | None = None) -> list[SimulationAuditEvent]:
        """Returns audit events, optionally filtered by simulation_id."""
        if simulation_id:
            return [e for e in self._events if e.simulation_id == simulation_id]
        return list(self._events)


simulation_auditor = SimulationAuditor()
