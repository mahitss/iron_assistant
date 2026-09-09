"""Operational incident management, correlation, and evidence-backed resolution (Task 38)."""

import uuid
from datetime import UTC, datetime
from typing import Any

from app.observability.schemas import (
    Incident,
    IncidentSeverity,
    IncidentStatus,
)


class IncidentManager:
    """Manages operational incidents, correlates related alerts, and enforces evidence-backed resolution."""

    def __init__(self) -> None:
        self._incidents: dict[str, Incident] = {}

    def report_failure(
        self,
        component: str,
        title: str,
        evidence: dict[str, Any],
        severity: IncidentSeverity = IncidentSeverity.MEDIUM,
    ) -> Incident:
        """Groups related failures for the same component into one active incident."""
        # Check if an OPEN incident for this component already exists
        for inc in self._incidents.values():
            if inc.status in (IncidentStatus.OPEN, IncidentStatus.ACKNOWLEDGED) and component in inc.affected_components:
                # Correlate failure into existing incident
                inc.evidence.append(evidence)
                inc.updated_at = datetime.now(UTC)
                # Escalate severity if incoming is higher
                if severity == IncidentSeverity.CRITICAL:
                    inc.severity = IncidentSeverity.CRITICAL
                return inc

        # Create new incident
        inc_id = f"inc_{uuid.uuid4().hex[:12]}"
        incident = Incident(
            id=inc_id,
            title=title,
            severity=severity,
            status=IncidentStatus.OPEN,
            affected_components=[component],
            evidence=[evidence],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self._incidents[inc_id] = incident
        return incident

    def acknowledge_incident(self, incident_id: str, acknowledged_by: str) -> Incident:
        """Marks an active incident as acknowledged by an operator."""
        inc = self._incidents.get(incident_id)
        if not inc:
            raise ValueError(f"Incident '{incident_id}' not found")
        inc.status = IncidentStatus.ACKNOWLEDGED
        inc.acknowledged_by = acknowledged_by
        inc.updated_at = datetime.now(UTC)
        return inc

    def resolve_incident(self, incident_id: str, recovery_evidence: str) -> Incident:
        """Resolves an incident with mandatory supporting recovery evidence.

        Hard Invariant: Incidents cannot be marked resolved merely because alerts stopped;
        they require demonstrable verification that the underlying system or dependency recovered.
        """
        if not recovery_evidence or not recovery_evidence.strip():
            raise ValueError("Resolution requires verifiable evidence that the issue recovered")

        inc = self._incidents.get(incident_id)
        if not inc:
            raise ValueError(f"Incident '{incident_id}' not found")

        inc.status = IncidentStatus.RESOLVED
        inc.resolved_at = datetime.now(UTC)
        inc.updated_at = datetime.now(UTC)
        inc.evidence.append({
            "event": "resolution_verification",
            "evidence": recovery_evidence.strip(),
            "timestamp": datetime.now(UTC).isoformat(),
        })
        return inc

    def get_incident(self, incident_id: str) -> Incident | None:
        return self._incidents.get(incident_id)

    def list_incidents(self, status: IncidentStatus | None = None) -> list[Incident]:
        results = list(self._incidents.values())
        if status:
            results = [inc for inc in results if inc.status == status]
        return sorted(results, key=lambda x: x.created_at, reverse=True)


incident_manager = IncidentManager()
