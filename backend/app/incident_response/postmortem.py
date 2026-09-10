"""Blameless postmortem generation, timeline synthesis, and preventive action item formulation (Task 61)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.incident_response.schemas import (
    IncidentResponse,
    PostmortemReport,
)

logger = logging.getLogger(__name__)


class PostmortemEngine:
    """Generates structured, blameless post-incident reviews and converts findings into actionable preventive items.

    Invariant 90-95: Separates root cause from contributing factors; formulates preventive planning tasks without blame.
    """

    def generate_postmortem(self, incident: IncidentResponse) -> PostmortemReport:
        """Construct a blameless post-incident report from incident history, hypotheses, and actions."""
        # 1. Determine verified root cause or maintain unknown
        leading_cause = "ROOT_CAUSE_UNKNOWN"
        for h in incident.hypotheses:
            if h.status.value in ("VERIFIED", "SUPPORTED") and h.confidence >= 0.75:
                leading_cause = h.candidate_cause
                break

        # 2. Extract contributing factors
        contributing: list[str] = []
        if len(incident.affected_services) > 1:
            contributing.append(f"Tight inter-service coupling across {incident.affected_services}")
        if len(incident.affected_resources) > 2:
            contributing.append("Shared infrastructure resource contention")
        if not incident.recovery_plan or len(incident.recovery_plan.steps) > 3:
            contributing.append("Complex multi-stage recovery dependencies")

        # 3. Assess what worked vs what failed
        what_worked: list[str] = [
            f"Rapid triage and classification under environment '{incident.environment}'",
            f"Containment and blast radius evaluation across {len(incident.affected_services)} services",
        ]
        what_failed: list[str] = []

        for act in incident.actions:
            if act.status.value in ("COMPLETED", "VERIFIED"):
                what_worked.append(f"Action '{act.title}' executed and verified successfully")
            elif act.status.value == "FAILED":
                what_failed.append(f"Action '{act.title}' encountered failure during execution")

        # 4. Formulate preventive action items for Strategic Planning
        action_items: list[dict[str, Any]] = [
            {
                "id": f"ai_{uuid.uuid4().hex[:6]}",
                "title": f"Implement Automated Canary Verification for {incident.affected_resources[:1]}",
                "type": "MONITORING_IMPROVEMENT",
                "priority": "HIGH",
            },
            {
                "id": f"ai_{uuid.uuid4().hex[:6]}",
                "title": f"Update Runbook and Failure Invariants for {leading_cause[:40]}",
                "type": "RUNBOOK_UPDATE",
                "priority": "MEDIUM",
            },
        ]

        # 5. Lessons learned
        lessons = [
            "Continuous verification checkpoints prevent premature incident resolution.",
            "Independent signal corroboration improves diagnostic accuracy without noise.",
        ]

        summary = (
            f"Incident '{incident.title}' ({incident.severity.value}) occurred in {incident.environment}. "
            f"Cause was diagnosed as: {leading_cause}."
        )
        impact_summary = (
            f"Impacted {len(incident.affected_services)} services, {len(incident.affected_resources)} resources, "
            f"and {len(incident.affected_goals)} strategic goals."
        )

        report = PostmortemReport(
            postmortem_id=f"pm_{uuid.uuid4().hex[:8]}",
            incident_id=incident.incident_id,
            summary=summary,
            impact_summary=impact_summary,
            root_cause=leading_cause,
            contributing_factors=contributing,
            what_worked=what_worked,
            what_failed=what_failed,
            action_items=action_items,
            lessons_learned=lessons,
        )

        logger.info("POSTMORTEM_GENERATED: incident=%s root_cause='%s'", incident.incident_id, leading_cause)
        return report


postmortem_engine = PostmortemEngine()
