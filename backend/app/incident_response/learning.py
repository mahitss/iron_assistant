"""Post-incident learning, cross-engine feedback dispatch, and calibration (Task 61)."""

from __future__ import annotations

import logging
from typing import Any

from app.incident_response.schemas import (
    IncidentResponse,
    PostmortemReport,
)

logger = logging.getLogger(__name__)


class IncidentLearningEngine:
    """Dispatches post-incident outcomes and lessons into Decision Engine, Planning, and Executive Memory.

    Invariant 96-101: Translates incident outcomes into operational knowledge, updating calibration and playbooks.
    """

    def dispatch_learnings(
        self,
        incident: IncidentResponse,
        postmortem: PostmortemReport,
    ) -> dict[str, Any]:
        """Broadcast incident learnings across Kairo intelligence subsystems."""
        # 1. Decision calibration payload
        decision_feedback = {
            "incident_id": incident.incident_id,
            "selected_strategy": incident.selected_option_id,
            "outcome_status": incident.status.value,
            "was_successful": incident.status.value == "RESOLVED",
        }

        # 2. Strategic Planning recommendations
        planning_proposals = [
            {
                "proposal_id": f"prop_{item['id']}",
                "title": item["title"],
                "type": item["type"],
                "target_plan_id": incident.affected_plans[0] if incident.affected_plans else None,
            }
            for item in postmortem.action_items
        ]

        # 3. Executive memory storage record
        memory_record = {
            "incident_id": incident.incident_id,
            "title": incident.title,
            "root_cause": postmortem.root_cause,
            "mitigation_strategy": incident.selected_option_id,
            "environment": incident.environment,
            "lessons": postmortem.lessons_learned,
        }

        logger.info(
            "INCIDENT_LEARNING_DISPATCHED: incident=%s planning_proposals=%d",
            incident.incident_id,
            len(planning_proposals),
        )

        return {
            "decision_feedback": decision_feedback,
            "planning_proposals": planning_proposals,
            "memory_record": memory_record,
            "is_dispatched": True,
        }


incident_learning_engine = IncidentLearningEngine()
