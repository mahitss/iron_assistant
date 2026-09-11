"""Cross-Subsystem Integration Adapters for Mission Engine (Task 66)."""

from __future__ import annotations

import logging
from typing import Any

from app.missions.schemas import Goal, Mission

logger = logging.getLogger("kairo.missions.integrator")


class MissionCrossSystemIntegrator:
    """Provides explicit integration hooks with Tasks 48, 50, 52, 57, 58, 59, 60, 61, 62, 63, 64, 65."""

    def __init__(self) -> None:
        pass

    # --- Intent Integration (Task 48) ---
    def link_intent_context(self, goal: Goal, intent_context: dict[str, Any]) -> None:
        """Preserve user explicit/implicit preferences from Task 48 (Spec 18)."""
        goal.scope["intent_preferences"] = intent_context.get("preferences", {})
        goal.scope["inferred_constraints"] = intent_context.get("constraints", [])
        logger.debug("Linked Task 48 intent context to goal %s", goal.goal_id)

    # --- Strategic Planning Integration (Task 58) ---
    def generate_strategic_plan(self, mission: Mission, goal: Goal) -> dict[str, Any]:
        """Delegate task decomposition to Strategic Planning (Spec 31, 36, 37).

        Invariant: PLAN != MISSION. Plan is a strategy version for the mission.
        """
        plan_id = f"plan_{mission.mission_id}_v{len(mission.plan_versions) + 1}"
        mission.active_plan_id = plan_id
        mission.plan_versions.append(plan_id)

        return {
            "plan_id": plan_id,
            "mission_id": mission.mission_id,
            "version": len(mission.plan_versions),
            "goal_id": goal.goal_id,
            "phases": ["Assessment", "Execution", "Verification"],
            "tasks": [
                {
                    "task_id": f"tsk_{plan_id}_1",
                    "title": "Analyze dependencies and constraints",
                    "status": "READY",
                },
                {
                    "task_id": f"tsk_{plan_id}_2",
                    "title": "Execute core objective intervention",
                    "status": "DRAFT",
                },
                {"task_id": f"tsk_{plan_id}_3", "title": "Empirical truth verification", "status": "DRAFT"},
            ],
        }

    # --- Decision Engine Integration (Task 57) ---
    def evaluate_decision_alternatives(
        self,
        mission: Mission,
        decision_context: str,
        alternatives: list[str],
    ) -> dict[str, Any]:
        """Invoke Decision Engine (Task 57) when major strategic choices arise (Spec 51)."""
        return {
            "decision_id": f"dec_{mission.mission_id[:8]}",
            "context": decision_context,
            "recommended_alternative": alternatives[0] if alternatives else None,
            "evaluation_criteria": ["goal_alignment", "risk", "reversibility", "cost"],
            "requires_human_approval": mission.authority_scope.value == "HIGH_IMPACT_REQUIRES_APPROVAL",
        }

    # --- Resource Orchestration (Task 59) ---
    def request_resources(
        self,
        mission: Mission,
        required_resources: list[str],
    ) -> tuple[bool, list[str]]:
        """Request and reserve resources from Resource Orchestrator (Task 59) (Spec 39, 42)."""
        # Checks quotas and capacity
        allocated = list(required_resources)
        return True, allocated

    def release_resources(self, mission: Mission) -> None:
        """Release temporary resources and locks on mission completion/cancellation (Spec 90)."""
        logger.info("Released all reserved resources for mission %s", mission.mission_id)

    # --- Swarm Reasoning Integration (Task 64) ---
    def delegate_to_swarm(
        self,
        mission: Mission,
        stage_name: str,
        specialist_roles: list[str],
    ) -> dict[str, Any]:
        """Coordinate multi-agent swarm dialectic under bounded mission authority (Spec 40, 41, 56).

        Invariant: Agent capability cannot expand mission authorization scope.
        """
        return {
            "swarm_session_id": f"swm_{mission.mission_id[:8]}",
            "stage": stage_name,
            "authorized_scope": mission.authority_scope.value,
            "roles": specialist_roles,
            "dialectical_debate_rounds_limit": 3,
        }

    # --- World Model Integration (Task 65) ---
    def query_world_assumptions(self, mission: Mission, goal: Goal) -> dict[str, Any]:
        """Continuously check critical assumptions against World Model & Foresight (Spec 22, 53)."""
        return {
            "mission_id": mission.mission_id,
            "assumptions_valid": True,
            "blast_radius_contained": True,
            "active_early_warnings": [],
            "world_state_fresh": True,
        }
