"""Agent health monitoring, heartbeats, and quarantine governance (Task 44)."""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger("kairo.agents.health")


def utc_now() -> datetime:
    return datetime.now(UTC)


class AgentHealthState(str, enum.Enum):
    """Health classification of an agent or provider (Spec 7)."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    FAILED = "FAILED"
    DRAINING = "DRAINING"


@dataclass
class AgentHealthRecord:
    """Live health status and heartbeat metadata for an agent (Spec 7, 8)."""

    agent_id: str
    state: AgentHealthState = AgentHealthState.HEALTHY
    last_heartbeat: datetime = field(default_factory=utc_now)
    consecutive_failures: int = 0
    is_quarantined: bool = False
    quarantine_reason: str | None = None

    def record_heartbeat(self) -> None:
        self.last_heartbeat = utc_now()
        if not self.is_quarantined and self.state == AgentHealthState.UNAVAILABLE:
            self.state = AgentHealthState.HEALTHY

    def record_failure(self, error: str) -> None:
        self.consecutive_failures += 1
        if self.consecutive_failures >= 3:
            self.state = AgentHealthState.DEGRADED
        if self.consecutive_failures >= 5:
            self.state = AgentHealthState.FAILED

    def record_success(self) -> None:
        self.consecutive_failures = 0
        if not self.is_quarantined:
            self.state = AgentHealthState.HEALTHY

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "state": self.state.value if hasattr(self.state, "value") else str(self.state),
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "consecutive_failures": self.consecutive_failures,
            "is_quarantined": self.is_quarantined,
            "quarantine_reason": self.quarantine_reason,
        }


class AgentHealthMonitor:
    """Monitors active agent heartbeats and applies governance quarantine (Spec 139, 140)."""

    def __init__(self, heartbeat_timeout_seconds: int = 60) -> None:
        self.heartbeat_timeout = heartbeat_timeout_seconds
        self._records: dict[str, AgentHealthRecord] = {}

    def get_record(self, agent_id: str) -> AgentHealthRecord:
        if agent_id not in self._records:
            self._records[agent_id] = AgentHealthRecord(agent_id=agent_id)
        return self._records[agent_id]

    def record_heartbeat(self, agent_id: str) -> None:
        self.get_record(agent_id).record_heartbeat()

    def quarantine_agent(self, agent_id: str, reason: str) -> None:
        """Quarantine an agent following repeated unsafe behavior or policy violation (Spec 139, 140).
        
        CRITICAL: Quarantined agent CANNOT receive consequential tasks.
        """
        rec = self.get_record(agent_id)
        rec.is_quarantined = True
        rec.quarantine_reason = reason
        rec.state = AgentHealthState.UNAVAILABLE
        logger.error("QUARANTINED agent '%s'. Reason: %s", agent_id, reason)

    def release_quarantine(self, agent_id: str, operator: str) -> None:
        rec = self.get_record(agent_id)
        rec.is_quarantined = False
        rec.quarantine_reason = None
        rec.state = AgentHealthState.HEALTHY
        rec.consecutive_failures = 0
        logger.info("Quarantine released for agent '%s' by operator '%s'", agent_id, operator)

    def check_liveness(self) -> None:
        """Detect timed out agents based on missing heartbeats."""
        threshold = utc_now() - timedelta(seconds=self.heartbeat_timeout)
        for rec in self._records.values():
            if rec.last_heartbeat < threshold and not rec.is_quarantined:
                rec.state = AgentHealthState.UNAVAILABLE
