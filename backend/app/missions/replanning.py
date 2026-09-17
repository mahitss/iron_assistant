"""Mission Plan Versioning, Staleness Detection & Dynamic Replanning Substrate (Task 100)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.missions.schemas import (
    AssumptionStatus,
    Mission,
    MissionPlanVersion,
    MissionStatus,
)

logger = logging.getLogger("kairo.missions.replanning")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class PlanVersionManager:
    """Manages immutable plan versions, detects plan staleness, and coordinates dynamic replanning.

    Invariants:
    - Mission Control NEVER directly invents plans; it delegates to the authoritative Strategic Planner.
    - Candidate plans must be deliberated by Decision Intelligence before adoption.
    - Never silently replace a plan; all plan transitions are versioned, traced, and preserved.
    - Stale plans must be blocked from autonomous execution.
    """

    @classmethod
    def detect_plan_staleness(
        cls,
        mission: Mission,
        world_state_drifted: bool = False,
        critical_assumptions_failed: bool = False,
        capability_degraded: bool = False,
        active_situations: list[str] | None = None,
    ) -> tuple[bool, list[str]]:
        """Detect whether the current active plan is stale and unsafe to execute."""
        staleness_reasons: list[str] = []

        if world_state_drifted:
            staleness_reasons.append("World state drifted materially from plan premises")

        if critical_assumptions_failed or any(a.status == AssumptionStatus.INVALID for a in mission.assumptions):
            invalid_stmts = [a.statement for a in mission.assumptions if a.status == AssumptionStatus.INVALID]
            staleness_reasons.append(f"Critical assumptions invalidated: {', '.join(invalid_stmts[:3])}")

        if capability_degraded:
            staleness_reasons.append("Required execution capabilities degraded or revoked")

        if active_situations:
            staleness_reasons.append(f"Emergent active situations detected: {len(active_situations)}")

        is_stale = len(staleness_reasons) > 0
        return is_stale, staleness_reasons

    @classmethod
    def record_plan_version(
        cls,
        mission: Mission,
        plan_id: str,
        plan_spec: dict[str, Any],
        reason: str,
        triggering_situation_id: str | None = None,
        changed_assumptions: list[str] | None = None,
        changed_milestones: list[str] | None = None,
        decisions_linked: list[str] | None = None,
    ) -> MissionPlanVersion:
        """Create an immutable plan version record and update active plan linkage."""
        superseded = mission.active_plan_id
        new_version_number = len(mission.plan_records) + 1

        # Mark previously active plan versions as SUPERSEDED
        for pv in mission.plan_records:
            if pv.status == "ACTIVE":
                pv.status = "SUPERSEDED"

        plan_version = MissionPlanVersion(
            mission_id=mission.mission_id,
            plan_id=plan_id,
            version_number=new_version_number,
            reason=reason,
            triggering_situation_id=triggering_situation_id,
            changed_assumptions=changed_assumptions or [],
            changed_milestones=changed_milestones or [],
            superseded_plan_id=superseded,
            decisions_linked=decisions_linked or [],
            plan_spec=plan_spec,
            status="ACTIVE",
            created_at=_now_utc(),
        )

        mission.plan_records.append(plan_version)
        mission.active_plan_id = plan_id
        if plan_id not in mission.plan_versions:
            mission.plan_versions.append(plan_id)
        mission.updated_at = _now_utc()

        logger.info(
            "PLAN_VERSION_RECORDED: mission=%s plan=%s v=%d reason=%s superseded=%s",
            mission.mission_id,
            plan_id,
            new_version_number,
            reason,
            superseded,
        )
        return plan_version

    @classmethod
    def invalidate_active_plan(cls, mission: Mission, reason: str) -> None:
        """Mark the active plan version as INVALIDATED and transition mission to REPLANNING."""
        if mission.active_plan_id:
            for pv in mission.plan_records:
                if pv.plan_id == mission.active_plan_id and pv.status == "ACTIVE":
                    pv.status = "INVALIDATED"
                    logger.warning("Plan %s for mission %s marked INVALIDATED: %s", pv.plan_id, mission.mission_id, reason)

        mission.status = MissionStatus.REPLANNING
        mission.updated_at = _now_utc()
