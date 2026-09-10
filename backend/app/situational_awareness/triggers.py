"""Operational trigger bridges for Decision Engine, Strategic Planning, and Resource Orchestration (Task 60)."""

from __future__ import annotations

import logging
from typing import Any

from app.situational_awareness.schemas import (
    AutomationLevel,
    BlastRadiusImpact,
    Situation,
    SituationSeverity,
)

logger = logging.getLogger(__name__)


class SituationTriggerBridge:
    """Dispatches situational awareness triggers to Decision Engine, Planning, and Orchestration.

    Invariant 16 & 91: Decision Trigger != Decision.
    A trigger formulates an operational problem statement; it does not autonomously decide.
    """

    def generate_decision_request(
        self,
        situation: Situation,
        impact: BlastRadiusImpact,
    ) -> dict[str, Any]:
        """Formulate a structured decision request for the Executive Decision Engine (Task 57)."""
        options = [
            {"id": "opt_scale", "title": "Scale Resource Capacity", "risk": "LOW"},
            {"id": "opt_failover", "title": "Failover to Standby Provider", "risk": "MEDIUM"},
            {"id": "opt_rollback", "title": "Rollback Recent Deployment", "risk": "MEDIUM"},
            {"id": "opt_monitor", "title": "Continue Monitoring (Wait & See)", "risk": "HIGH"},
        ]

        decision_request = {
            "title": f"Incident Remediation: {situation.title}",
            "purpose": f"Remediate {situation.severity.value} situation on resources {situation.affected_resources}",
            "context": {
                "situation_id": situation.situation_id,
                "severity": situation.severity.value,
                "affected_services": impact.known_affected_services,
                "affected_plans": impact.affected_plans,
                "affected_goals": impact.affected_goals,
            },
            "candidate_options": options,
            "automation_level": AutomationLevel.REQUIRE_APPROVAL.value
            if situation.severity in (SituationSeverity.HIGH, SituationSeverity.CRITICAL)
            else AutomationLevel.RECOMMEND.value,
        }

        logger.info(
            "DECISION_TRIGGERED: situation=%s severity=%s", situation.situation_id, situation.severity.value
        )
        return decision_request

    def notify_plan_invalidation(
        self,
        situation: Situation,
        impact: BlastRadiusImpact,
    ) -> list[dict[str, Any]]:
        """Generate plan invalidation alerts for the Strategic Planning Engine (Task 58)."""
        notifications = []
        for plan_id in impact.affected_plans:
            notice = {
                "plan_id": plan_id,
                "situation_id": situation.situation_id,
                "reason": f"Plan blocked or at risk due to situation '{situation.title}'",
                "recommended_action": "REPLAN",
            }
            notifications.append(notice)
            logger.warning("PLAN_ALERT_TRIGGERED: plan=%s situation=%s", plan_id, situation.situation_id)
        return notifications

    def notify_orchestration_rebalance(
        self,
        situation: Situation,
    ) -> list[dict[str, Any]]:
        """Generate provider failover / reallocation requests for Resource Orchestration (Task 59)."""
        reallocations = []
        for res_id in situation.affected_resources:
            req = {
                "resource_id": res_id,
                "situation_id": situation.situation_id,
                "action": "EVALUATE_FAILOVER",
                "reason": f"Resource degradation detected in situation '{situation.title}'",
            }
            reallocations.append(req)
            logger.warning(
                "ORCHESTRATION_REBALANCE_TRIGGERED: resource=%s situation=%s", res_id, situation.situation_id
            )
        return reallocations


situation_trigger_bridge = SituationTriggerBridge()
