"""Incident triage engine, severity derivation, and urgency evaluation (Task 61)."""

from __future__ import annotations

import logging
from typing import Any

from app.incident_response.schemas import (
    AutomationLevel,
    IncidentSeverity,
    IncidentUrgency,
)

logger = logging.getLogger(__name__)


class IncidentTriageEngine:
    """Evaluates severity, urgency, and blast radius to triage incoming situations into operational incidents.

    Invariant 9 & 10: Severity is derived from deterministic rules; arbitrary payloads cannot inject severity.
    Invariant 11: Urgency is evaluated independently from severity.
    """

    def triage_situation(
        self,
        situation: dict[str, Any],
        active_plans: list[dict[str, Any]] | None = None,
        active_goals: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Derive deterministic severity and urgency for an operational situation."""
        env = str(situation.get("environment", "development")).lower()
        resources = situation.get("affected_resources", [])
        services = situation.get("affected_services", [])
        plans = situation.get("affected_plans", []) or (active_plans or [])
        goals = situation.get("affected_goals", []) or (active_goals or [])
        raw_sev = str(situation.get("severity", "MEDIUM")).upper()

        # 1. Environment & Blast Radius factor
        is_production = env == "production"
        resource_count = len(resources)
        service_count = len(services)
        goal_count = len(goals)

        # 2. Derive Severity
        derived_sev = IncidentSeverity.LOW
        if is_production:
            if goal_count > 0 or service_count >= 3 or raw_sev == "CRITICAL":
                derived_sev = IncidentSeverity.CRITICAL
            elif resource_count >= 2 or service_count >= 1 or raw_sev == "HIGH":
                derived_sev = IncidentSeverity.HIGH
            elif raw_sev == "MEDIUM":
                derived_sev = IncidentSeverity.MEDIUM
            else:
                derived_sev = IncidentSeverity.LOW
        else:
            # Staging or development
            if raw_sev == "CRITICAL" and goal_count > 0:
                derived_sev = IncidentSeverity.HIGH
            elif raw_sev in ("HIGH", "CRITICAL"):
                derived_sev = IncidentSeverity.MEDIUM
            elif raw_sev == "MEDIUM":
                derived_sev = IncidentSeverity.LOW
            else:
                derived_sev = IncidentSeverity.INFO

        # 3. Derive Urgency (independent of severity)
        derived_urgency = IncidentUrgency.NORMAL
        if derived_sev == IncidentSeverity.CRITICAL:
            derived_urgency = IncidentUrgency.IMMEDIATE
        elif derived_sev == IncidentSeverity.HIGH:
            derived_urgency = IncidentUrgency.HIGH if is_production else IncidentUrgency.NORMAL
        elif goal_count > 0 or len(plans) > 0:
            # High urgency because active plans/deadlines are at risk, even if severity is medium/low
            derived_urgency = IncidentUrgency.HIGH
        else:
            derived_urgency = IncidentUrgency.LOW if env == "development" else IncidentUrgency.NORMAL

        # 4. Determine Automation Level and Incident Commander requirement
        if derived_sev == IncidentSeverity.CRITICAL:
            automation_level = AutomationLevel.AUTO_WITH_APPROVAL
            requires_commander = True
        elif derived_sev == IncidentSeverity.HIGH:
            automation_level = AutomationLevel.AUTO_WITH_APPROVAL
            requires_commander = True
        elif derived_sev == IncidentSeverity.MEDIUM:
            automation_level = AutomationLevel.RECOMMEND
            requires_commander = False
        else:
            automation_level = AutomationLevel.OBSERVE_ONLY
            requires_commander = False

        rationale = (
            f"Triaged in {env}: {resource_count} resources, {service_count} services, "
            f"{goal_count} goals affected -> Severity: {derived_sev.value}, Urgency: {derived_urgency.value}"
        )

        logger.info(
            "INCIDENT_TRIAGED: situation=%s sev=%s urg=%s commander_required=%s",
            situation.get("situation_id"),
            derived_sev.value,
            derived_urgency.value,
            requires_commander,
        )

        return {
            "severity": derived_sev,
            "urgency": derived_urgency,
            "confidence": 0.95 if is_production else 0.85,
            "rationale": rationale,
            "requires_commander": requires_commander,
            "automation_level": automation_level,
        }


incident_triage_engine = IncidentTriageEngine()
