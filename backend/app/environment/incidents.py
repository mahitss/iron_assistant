"""Incident Detection, Timeline Linking, and Blast Radius Estimation (Task 54, Prompts #96-#105)."""

from __future__ import annotations

import uuid
from typing import Any

from app.environment.schemas import DriftSeverity, ImpactLevel, Incident, IncidentStatus, ScopeType
from app.environment.temporal import utc_now
from app.environment.topology import TopologyGraph


class IncidentManager:
    """Detects incidents, correlates telemetry timelines, and bounds blast radius estimations."""

    @staticmethod
    def create_incident(
        scope: ScopeType,
        symptoms: list[str],
        affected_resources: list[str],
        evidence: dict[str, Any],
        suspected_cause: str | None = None,
        root_cause: str | None = None,
        severity: DriftSeverity = DriftSeverity.MEDIUM,
        scope_id: str | None = None,
        timeline_events: list[dict[str, Any]] | None = None,
    ) -> Incident:
        # Prompt #99, #100: Root cause requires verified evidence; otherwise suspected cause
        if root_cause and not evidence.get("root_cause_verified"):
            # Demote to suspected cause
            suspected_cause = suspected_cause or root_cause
            root_cause = None

        iid = f"inc_{uuid.uuid4().hex[:10]}"
        now = utc_now()
        initial_timeline = timeline_events or [
            {"timestamp": now.isoformat(), "event": "Incident detected", "symptoms": symptoms}
        ]

        return Incident(
            incident_id=iid,
            scope=scope,
            scope_id=scope_id,
            detected_at=now,
            severity=severity,
            symptoms=symptoms,
            affected_resources=affected_resources,
            suspected_cause=suspected_cause,
            root_cause=root_cause,
            evidence=evidence,
            status=IncidentStatus.DETECTED,
            timeline=initial_timeline,
        )

    @staticmethod
    def estimate_blast_radius(
        origin_node_id: str,
        topology: TopologyGraph,
        max_hops: int = 3,
    ) -> dict[str, Any]:
        """Prompt #103, #104: Estimates affected downstream resources without overstating certainty."""
        downstream = topology.bounded_traversal(
            start_node_id=origin_node_id,
            direction="incoming",  # Things that depend on origin_node
            max_depth=max_hops,
            max_nodes=100,
        )
        affected = [nid for nid in downstream["visited_node_ids"] if nid != origin_node_id]

        # Uncertainty handling: if traversal truncated or graph has unmapped edges
        uncertainty = None
        if downstream["truncated"]:
            uncertainty = "Blast radius traversal reached maximum node limit; full impact may be larger."

        impact = ImpactLevel.MEDIUM
        if len(affected) > 10:
            impact = ImpactLevel.HIGH
        elif len(affected) == 0:
            impact = ImpactLevel.LOW

        return {
            "origin_node_id": origin_node_id,
            "estimated_affected_count": len(affected),
            "affected_resources": affected,
            "estimated_impact": impact,
            "uncertainty_note": uncertainty,  # Prompt #104
        }
