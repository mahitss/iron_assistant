"""Downstream Subsystem Bridges and Authorization Separation for Task 108.

Enforces:
1. Intent != Authorization (Spec 27): SecurityCenter & ApprovalRegistry govern execution.
2. Intent != Goal (Spec 23): Goal Management in Task 100 remains authoritative.
3. Intent != Plan (Spec 24): Planner Engine handles task decomposition; Intent provides inputs.
4. Intent != Decision (Spec 25): Decision Intelligence (Task 94) selects actions.
5. EmergencyStop absolute primacy: fail-closed blocking across all handoffs.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.intent.domain import (
    Constraint,
    DesiredOutcome,
    GoalHypothesis,
    Intent,
    IntentSnapshot,
    Preference,
)
from app.security.emergency_stop import get_emergency_stop_service

logger = logging.getLogger("kairo.intent.bridges")


class DownstreamBridges:
    """Coordinates handoffs from Intent Engine to Goal, Plan, Decision, and Security subsystems."""

    def __init__(self) -> None:
        self.emergency_stop = get_emergency_stop_service()

    def check_emergency_stop(self, user_id: Optional[str] = None) -> bool:
        """Verifies EmergencyStop status. If stopped, blocks all downstream actions fail-closed."""
        if self.emergency_stop.is_stopped(user_id):
            logger.critical("EMERGENCY_STOP is active! All downstream handoffs fail-closed.")
            return True
        return False

    def handoff_to_goal_manager(
        self,
        intent: Intent,
        hypotheses: List[GoalHypothesis],
        user_id: str = "default_user",
    ) -> Dict[str, Any]:
        """Hands off understood intent to Task 100 Goal Management (Spec 23).
        
        Intent describes WHAT the user desires.
        Goal Management determines HOW it becomes managed objectives.
        """
        if self.check_emergency_stop(user_id):
            return {"status": "BLOCKED_BY_EMERGENCY_STOP", "goal_created": False}

        if intent.is_cancelled or intent.is_superseded:
            return {"status": "REJECTED_STALE_OR_CANCELLED", "goal_created": False}

        bundle = {
            "intent_id": intent.intent_id,
            "user_id": user_id,
            "target": intent.target,
            "scope": intent.scope,
            "priority": intent.priority.value,
            "goal_hypotheses": [h.model_dump(mode="json") for h in hypotheses],
            "status": "HANDED_OFF_TO_GOAL_MANAGER",
        }
        logger.info("Handed off intent %s to Goal Management", intent.intent_id)
        return bundle

    def prepare_planner_bundle(
        self,
        intent: Intent,
        outcome: DesiredOutcome,
        constraints: List[Constraint],
        user_id: str = "default_user",
    ) -> Dict[str, Any]:
        """Prepares planner input bundle (Spec 24). Intent Engine DOES NOT plan decomposition."""
        if self.check_emergency_stop(user_id):
            return {"status": "BLOCKED_BY_EMERGENCY_STOP"}

        return {
            "intent_id": intent.intent_id,
            "objective": intent.summary,
            "desired_outcome": outcome.model_dump(mode="json"),
            "constraints": [c.model_dump(mode="json") for c in constraints],
            "non_goals": list(intent.non_goals),
            "priority": intent.priority.value,
            "deadline": intent.deadline.isoformat() if intent.deadline else None,
            "uncertainty": {
                "target_confidence": intent.target_confidence,
                "overall_confidence": intent.overall_confidence,
            },
            "status": "READY_FOR_PLANNER",
        }

    def prepare_decision_bundle(
        self,
        snapshot: IntentSnapshot,
        preferences: List[Preference],
        user_id: str = "default_user",
    ) -> Dict[str, Any]:
        """Prepares Decision Intelligence input bundle (Spec 25). Task 94 selects actions."""
        if self.check_emergency_stop(user_id):
            return {"status": "BLOCKED_BY_EMERGENCY_STOP"}

        return {
            "snapshot_id": snapshot.snapshot_id,
            "intent_id": snapshot.intent_id,
            "intent_data": snapshot.intent_data,
            "constraints": snapshot.constraints,
            "non_goals": snapshot.non_goals,
            "preferences": [p.model_dump(mode="json") for p in preferences],
            "confidence_breakdown": snapshot.confidence_breakdown,
            "external_effect": snapshot.external_effect.value,
            "requires_security_evaluation": True,  # Non-negotiable invariant: Decision must consult SecurityCenter
            "status": "READY_FOR_DECISION_ENGINE",
        }
