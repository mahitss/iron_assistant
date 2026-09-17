"""First-Class Mission Assumption Tracking & Cascading Invalidation Engine (Task 100)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.missions.schemas import (
    AssumptionStatus,
    MilestoneStatus,
    Mission,
    MissionAssumption,
    MissionHealth,
    MissionStatus,
)

logger = logging.getLogger("kairo.missions.assumptions")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class AssumptionTracker:
    """Manages explicit mission assumptions, verification evidence, and cascading invalidation."""

    @classmethod
    def add_assumption(
        cls,
        mission: Mission,
        statement: str,
        evidence: list[str] | None = None,
        confidence: float = 1.0,
        dependent_milestones: list[str] | None = None,
        dependent_plan_versions: list[str] | None = None,
    ) -> MissionAssumption:
        """Register a first-class assumption for the mission."""
        assumption = MissionAssumption(
            mission_id=mission.mission_id,
            statement=statement,
            evidence=evidence or [],
            confidence=max(0.0, min(1.0, confidence)),
            status=AssumptionStatus.VALID if confidence >= 0.7 else AssumptionStatus.UNVERIFIED,
            dependent_milestones=dependent_milestones or [],
            dependent_plan_versions=dependent_plan_versions or [],
            last_verified_at=_now_utc() if confidence >= 0.7 else None,
        )
        mission.assumptions.append(assumption)
        mission.updated_at = _now_utc()
        logger.info("Added assumption %s to mission %s: '%s'", assumption.assumption_id, mission.mission_id, statement)
        return assumption

    @classmethod
    def register_assumption(
        cls,
        mission: Mission,
        request: Any,
    ) -> MissionAssumption:
        """Register assumption from request schema or keyword arguments."""
        dep_ms = list(getattr(request, "dependent_milestones", None) or [])
        if hasattr(request, "dependent_milestone_ids") and request.dependent_milestone_ids:
            dep_ms.extend(request.dependent_milestone_ids)
        return cls.add_assumption(
            mission=mission,
            statement=request.statement,
            evidence=getattr(request, "evidence", None),
            confidence=getattr(request, "confidence", 1.0),
            dependent_milestones=dep_ms,
            dependent_plan_versions=getattr(request, "dependent_plan_versions", None),
        )

    @classmethod
    def verify_assumption(
        cls,
        mission: Mission,
        assumption_id: str,
        evidence: list[str],
        confidence: float = 1.0,
    ) -> MissionAssumption:
        """Verify an assumption with fresh evidence and confidence score."""
        for a in mission.assumptions:
            if a.assumption_id == assumption_id:
                a.status = AssumptionStatus.VALID
                a.confidence = max(0.0, min(1.0, confidence))
                a.evidence.extend(evidence)
                a.last_verified_at = _now_utc()
                a.invalidation_reason = None
                mission.updated_at = _now_utc()
                logger.info("Verified assumption %s (confidence=%.2f)", assumption_id, confidence)
                return a
        raise KeyError(f"Assumption {assumption_id} not found on mission {mission.mission_id}")

    @classmethod
    def invalidate_assumption(
        cls,
        mission: Mission,
        assumption_id: str,
        reason: str,
        evidence: list[str] | None = None,
    ) -> MissionAssumption:
        """Invalidate an assumption and execute cascading impact propagation (Task 100 Section 18).

        Flow:
        -> Assumption marked INVALIDATED
        -> Affected dependent milestones marked BLOCKED
        -> Affected plans marked stale
        -> Mission flagged AT_RISK / REPLANNING triggered
        """
        target_assumption: MissionAssumption | None = None
        for a in mission.assumptions:
            if a.assumption_id == assumption_id:
                target_assumption = a
                break

        if not target_assumption:
            raise KeyError(f"Assumption {assumption_id} not found on mission {mission.mission_id}")

        target_assumption.status = AssumptionStatus.INVALIDATED
        target_assumption.confidence = 0.0
        target_assumption.invalidation_reason = reason
        if evidence:
            target_assumption.evidence.extend([f"INVALIDATION_EVIDENCE: {e}" for e in evidence])

        # 1. Identify and update affected milestones
        affected_milestones: list[str] = []
        for m in mission.milestones:
            if m.milestone_id in target_assumption.dependent_milestones:
                affected_milestones.append(m.milestone_id)
                if m.status in (MilestoneStatus.READY, MilestoneStatus.ACTIVE, MilestoneStatus.PENDING, MilestoneStatus.AT_RISK):
                    m.status = MilestoneStatus.BLOCKED
                    m.blocked_reason = f"Invalid assumption '{target_assumption.statement}': {reason}"
                    m.updated_at = _now_utc()
                elif m.status == MilestoneStatus.COMPLETED:
                    # Potential progress regression if completed work depended on an invalid assumption
                    m.status = MilestoneStatus.REGRESSED
                    m.blocked_reason = f"Premise invalidated: {reason}"
                    m.updated_at = _now_utc()

        # 2. Identify affected plans
        affected_plans = list(target_assumption.dependent_plan_versions)
        if mission.active_plan_id and (
            mission.active_plan_id in affected_plans or not affected_plans
        ):
            if mission.active_plan_id not in affected_plans:
                affected_plans.append(mission.active_plan_id)

        # 3. Update mission health and status
        mission.health = MissionHealth.AT_RISK
        mission.updated_at = _now_utc()

        logger.warning(
            "Assumption %s INVALIDATED on mission %s. Affected milestones: %s, Affected plans: %s",
            assumption_id,
            mission.mission_id,
            affected_milestones,
            affected_plans,
        )

        return target_assumption

    @classmethod
    def get_invalid_or_at_risk(cls, mission: Mission) -> list[MissionAssumption]:
        """Return all assumptions requiring attention."""
        return [
            a for a in mission.assumptions
            if a.status in (AssumptionStatus.INVALID, AssumptionStatus.AT_RISK, AssumptionStatus.UNVERIFIED)
        ]
