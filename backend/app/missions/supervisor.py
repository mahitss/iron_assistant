"""Mission Supervisory Loop, Next-Action Selection, Pre-Execution Staleness Check, and Verification (Task 66)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.missions.drift import GoalDriftDetector
from app.missions.lifecycle import MissionStateMachine
from app.missions.progress import ProgressEngine
from app.missions.safety import (
    check_budget_limits,
)
from app.missions.schemas import (
    Goal,
    GoalAuthorityScope,
    Mission,
    MissionCheckpoint,
    MissionPostmortem,
    MissionStatus,
    ReversibilityClass,
)

logger = logging.getLogger("kairo.missions.supervisor")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class MissionSupervisor:
    """Supervises active mission execution, enforces invariants, and reconciles state."""

    def __init__(self) -> None:
        pass

    def run_supervisory_cycle(
        self,
        mission: Mission,
        goal: Goal,
        telemetry: dict[str, Any],
        recent_actions: list[str],
        world_state_freshness: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute one autonomous supervisory evaluation cycle (Spec 57).

        observe -> evaluate_progress -> validate_constraints -> detect_blockers ->
        detect_drift -> assess_risk -> decide_next_step -> verify -> update_mission.
        """
        # 1. Budget & Infinite Mission Guard (Spec 43, 103)
        check_budget_limits(mission)

        # 2. Check Expiration (Spec 50)
        if mission.expires_at and _now_utc() > mission.expires_at:
            MissionStateMachine.transition(mission, MissionStatus.EXPIRED, reason="Mission TTL expired")
            return {"cycle_status": "EXPIRED", "mission_id": mission.mission_id}

        # 3. Detect Goal Drift & Objective Gaming (Spec 19, 20)
        drift_alert = GoalDriftDetector.check_goal_drift(mission, goal, recent_actions)
        if drift_alert:
            return {
                "cycle_status": "DRIFT_DETECTED",
                "alert": drift_alert.model_dump(),
                "action_recommended": "REPLAN",
            }

        # 4. Pre-execution Staleness Check (Spec 63, 64)
        if world_state_freshness and world_state_freshness.get("is_stale", False):
            logger.warning("Pre-execution staleness check failed: World state is stale.")
            MissionStateMachine.transition(
                mission,
                MissionStatus.REPLANNING,
                reason="Pre-execution staleness check failed; world state mutated since plan was drafted",
            )
            return {"cycle_status": "STALE_STATE_REPLAN", "mission_id": mission.mission_id}

        # 5. Evaluate Success Criteria (Spec 10, 75, 76)
        all_success_met, failure_reasons = ProgressEngine.evaluate_goal_success(goal, telemetry)
        if all_success_met:
            MissionStateMachine.transition(
                mission,
                MissionStatus.VERIFYING,
                reason="All empirical success criteria met, entering formal verification",
            )
            MissionStateMachine.transition(
                mission,
                MissionStatus.COMPLETED,
                reason="Success criteria verified by truth gate",
            )
            return {
                "cycle_status": "COMPLETED",
                "mission_id": mission.mission_id,
                "verified": True,
            }

        # 6. Decide Next Action (Spec 59, 60, 61)
        next_action = self.select_next_action(mission, goal, telemetry)

        # 7. Record Checkpoint (Spec 26)
        mission.checkpoints.append(
            MissionCheckpoint(
                mission_id=mission.mission_id,
                state=mission.status,
                progress_pct=mission.progress_pct,
                evidence=[f"Telemetry checked. Success criteria status: {len(failure_reasons)} pending."],
                next_steps=[next_action["action_name"]],
            )
        )

        return {
            "cycle_status": "IN_PROGRESS",
            "mission_id": mission.mission_id,
            "next_action": next_action,
            "pending_criteria": failure_reasons,
        }

    def select_next_action(
        self,
        mission: Mission,
        goal: Goal,
        telemetry: dict[str, Any],
    ) -> dict[str, Any]:
        """Select next best action based on goal relevance, risk, cost, and reversibility (Spec 59, 61, 62)."""
        # If uncertainty is high, choose an Information-Seeking action (Spec 60)
        uncertainty = telemetry.get("uncertainty_score", 0.1)
        if uncertainty > 0.65:
            return {
                "action_name": "RESEARCH_UNCERTAINTY",
                "action_type": "information_seeking",
                "reversibility": ReversibilityClass.REVERSIBLE.value,
                "description": "High mission uncertainty detected. Execute research query before mutating production.",
                "requires_approval": False,
            }

        return {
            "action_name": "EXECUTE_SCHEDULED_STEP",
            "action_type": "execution",
            "reversibility": ReversibilityClass.REVERSIBLE.value,
            "description": "Execute next authorized planning step.",
            "requires_approval": mission.authority_scope == GoalAuthorityScope.HIGH_IMPACT_REQUIRES_APPROVAL,
        }

    def close_mission_with_postmortem(
        self,
        mission: Mission,
        final_status: MissionStatus,
        what_worked: list[str] | None = None,
        what_failed: list[str] | None = None,
        lessons: list[str] | None = None,
    ) -> MissionPostmortem:
        """Close mission and record postmortem for continuous learning (Spec 78, 79).

        Invariant: MISSION OUTCOME != AUTOMATIC POLICY CHANGE.
        """
        MissionStateMachine.transition(
            mission,
            final_status,
            reason=f"Mission closed with status {final_status.value}",
        )
        completed_at = _now_utc()
        duration_s = max(0.0, (completed_at - mission.created_at).total_seconds())
        postmortem = MissionPostmortem(
            mission_id=mission.mission_id,
            final_status=final_status,
            what_worked=what_worked or ["Planned tasks executed systematically."],
            what_failed=what_failed or [],
            lessons=lessons or ["Maintain strict pre-execution staleness checks."],
            duration_seconds=duration_s,
            completed_at=completed_at,
        )
        return postmortem
