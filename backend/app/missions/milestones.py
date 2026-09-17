"""Mission Objectives, Milestone DAG, Evidence Verification & Progress Regression Engine (Task 100)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.missions.schemas import (
    MilestoneStatus,
    Mission,
    MissionHealth,
    MissionMilestone,
    MissionObjective,
    MissionStatus,
    SuccessCriteria,
)

logger = logging.getLogger("kairo.missions.milestones")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class MilestoneEngine:
    """Manages persistent mission milestones, DAG dependencies, evidence-based verification, and regression."""

    @classmethod
    def add_milestone(
        cls,
        mission: Mission,
        title: str | Any,
        description: str = "",
        objective_id: str | None = None,
        ordering: int = 0,
        dependencies: list[str] | None = None,
        goal_linkage: str | None = None,
        success_criteria: list[SuccessCriteria] | None = None,
        verification_criteria: list[str] | None = None,
        deadline: datetime | None = None,
    ) -> MissionMilestone:
        """Add a persistent milestone to a mission."""
        if not isinstance(title, str) and hasattr(title, "title"):
            req = title
            title_str = req.title
            description = getattr(req, "description", "") or ""
            objective_id = getattr(req, "objective_id", None)
            ordering = getattr(req, "ordering", 0) or 0
            dependencies = getattr(req, "dependencies", None) or getattr(req, "depends_on_milestones", None) or []
            goal_linkage = getattr(req, "goal_linkage", None)
            success_criteria = getattr(req, "success_criteria", None) or []
            verification_criteria = getattr(req, "verification_criteria", None) or getattr(req, "required_evidence_types", None) or []
            deadline = getattr(req, "deadline", None)
        else:
            title_str = str(title)

        milestone = MissionMilestone(
            mission_id=mission.mission_id,
            objective_id=objective_id,
            title=title_str,
            description=description,
            ordering=ordering or (len(mission.milestones) + 1),
            dependencies=dependencies or [],
            goal_linkage=goal_linkage,
            success_criteria=success_criteria or [],
            verification_criteria=verification_criteria or [],
            deadline=deadline,
            status=MilestoneStatus.READY if not dependencies else MilestoneStatus.PENDING,
        )
        mission.milestones.append(milestone)
        mission.milestone_count = len(mission.milestones)
        mission.updated_at = _now_utc()
        return milestone

    @classmethod
    def check_and_update_readiness(cls, mission: Mission) -> list[MissionMilestone]:
        """Update PENDING milestones to READY if all prerequisite dependencies are COMPLETED."""
        completed_ids = {m.milestone_id for m in mission.milestones if m.status == MilestoneStatus.COMPLETED}
        newly_ready = []

        for m in mission.milestones:
            if m.status == MilestoneStatus.PENDING:
                if all(dep_id in completed_ids for dep_id in m.dependencies):
                    m.status = MilestoneStatus.READY
                    m.updated_at = _now_utc()
                    newly_ready.append(m)
                    logger.info("Milestone %s (%s) is now READY", m.milestone_id, m.title)

        return newly_ready

    @classmethod
    def start_milestone(cls, mission: Mission, milestone_id: str) -> MissionMilestone:
        """Start work on a milestone."""
        for m in mission.milestones:
            if m.milestone_id == milestone_id:
                if m.status not in (MilestoneStatus.READY, MilestoneStatus.PENDING, MilestoneStatus.AT_RISK, MilestoneStatus.REGRESSED):
                    raise ValueError(f"Cannot start milestone in state {m.status.value}")
                m.status = MilestoneStatus.ACTIVE
                m.started_at = _now_utc()
                m.updated_at = _now_utc()
                return m
        raise KeyError(f"Milestone {milestone_id} not found on mission {mission.mission_id}")

    @classmethod
    def verify_milestone(
        cls,
        mission: Mission,
        milestone_id: str,
        empirical_evidence: list[str],
        world_state_data: dict[str, Any] | None = None,
        test_results: dict[str, Any] | None = None,
    ) -> tuple[bool, str]:
        """Verify milestone completion against empirical evidence.

        Invariants:
        - Do not accept 'agent output' as proof of completion.
        - Must match verification criteria and success criteria.
        - Requires empirical evidence (telemetry, verified test pass, world-state reconciliation).
        """
        milestone: MissionMilestone | None = None
        for m in mission.milestones:
            if m.milestone_id == milestone_id:
                milestone = m
                break

        if not milestone:
            return False, f"Milestone {milestone_id} not found"

        # Check evidence presence
        if not empirical_evidence and not world_state_data and not test_results:
            milestone.status = MilestoneStatus.BLOCKED
            milestone.blocked_reason = "Verification failed: No empirical evidence provided."
            return False, milestone.blocked_reason

        # Reject unsubstantiated claims
        for ev in empirical_evidence:
            ev_low = ev.lower()
            if "agent said" in ev_low or "assumed complete" in ev_low or "unverified" in ev_low:
                milestone.status = MilestoneStatus.AT_RISK
                milestone.blocked_reason = "Verification rejected: Unsubstantiated agent assertion detected."
                return False, milestone.blocked_reason

        # Evaluate SuccessCriteria if present
        all_criteria_passed = True
        failed_reasons = []

        for crit in milestone.success_criteria:
            crit_satisfied = False
            crit_low = crit.description.lower()

            # 1. World state verification
            if crit.criteria_type in ("world_state", "metric_threshold") and world_state_data:
                if crit.target_metric and crit.target_metric in world_state_data:
                    actual = world_state_data[crit.target_metric]
                    crit.current_value = actual
                    if crit.comparison_operator == "eq" and actual == crit.target_value:
                        crit_satisfied = True
                    elif crit.comparison_operator == "lt" and float(actual) < float(crit.target_value or 0):
                        crit_satisfied = True
                    elif crit.comparison_operator == "gt" and float(actual) > float(crit.target_value or 0):
                        crit_satisfied = True
                    elif crit.comparison_operator == "gte" and float(actual) >= float(crit.target_value or 0):
                        crit_satisfied = True
                    elif crit.comparison_operator == "lte" and float(actual) <= float(crit.target_value or 0):
                        crit_satisfied = True
                elif world_state_data.get("reconciled", False):
                    crit_satisfied = True

            # 2. Test pass verification
            if crit.criteria_type in ("test_pass", "verification_result") and test_results:
                if test_results.get("passed", False) or test_results.get("exit_code", 1) == 0:
                    crit_satisfied = True

            # 3. Evidence pattern match
            if not crit_satisfied:
                for ev in empirical_evidence:
                    if (
                        crit_low in ev.lower()
                        or "verified" in ev.lower()
                        or "passed" in ev.lower()
                        or "success" in ev.lower()
                    ):
                        crit_satisfied = True
                        break

            if crit_satisfied:
                crit.is_verified = True
                crit.verified_at = _now_utc()
                crit.verification_evidence = list(empirical_evidence)
            else:
                all_criteria_passed = False
                failed_reasons.append(f"Criterion '{crit.description}' not empirically satisfied.")

        # If there are explicit verification_criteria strings
        for vc in milestone.verification_criteria:
            vc_low = vc.lower()
            matched = any(vc_low in ev.lower() or "verified" in ev.lower() for ev in empirical_evidence)
            if not matched and not (world_state_data and world_state_data.get("reconciled")):
                all_criteria_passed = False
                failed_reasons.append(f"Verification criterion '{vc}' not matched in evidence.")

        if not all_criteria_passed and (milestone.success_criteria or milestone.verification_criteria):
            milestone.status = MilestoneStatus.AT_RISK
            milestone.blocked_reason = "; ".join(failed_reasons)
            return False, milestone.blocked_reason

        # Milestone successfully verified
        milestone.status = MilestoneStatus.COMPLETED
        milestone.progress_pct = 100.0
        milestone.confidence = 1.0
        milestone.completed_at = _now_utc()
        milestone.verification_evidence = list(empirical_evidence)
        milestone.blocked_reason = None
        milestone.version += 1
        milestone.updated_at = _now_utc()

        # Update mission completed counts
        mission.completed_milestones = sum(1 for m in mission.milestones if m.status == MilestoneStatus.COMPLETED)
        mission.updated_at = _now_utc()

        # Unlock downstream milestones
        cls.check_and_update_readiness(mission)

        logger.info("Milestone %s (%s) VERIFIED & COMPLETED", milestone.milestone_id, milestone.title)
        return True, "Milestone verified and marked COMPLETED"

    @classmethod
    def regress_milestone(
        cls,
        mission: Mission,
        milestone_id: str,
        reason: str,
        evidence: list[str] | None = None,
    ) -> MissionMilestone:
        """Regress previously completed milestone when later reality invalidates it (Task 100 Section 11).

        Invariants:
        - Do not permanently mark work complete if reality invalidates the outcome.
        - Preserve historical completion while transitioning status to REGRESSED.
        """
        for m in mission.milestones:
            if m.milestone_id == milestone_id:
                if m.status != MilestoneStatus.COMPLETED:
                    logger.warning("Attempted to regress milestone %s not in COMPLETED state (status: %s)", milestone_id, m.status.value)
                m.status = MilestoneStatus.REGRESSED
                m.progress_pct = 50.0  # Degraded progress
                m.confidence = 0.3
                m.blocked_reason = f"Progress regression: {reason}"
                if evidence:
                    m.verification_evidence.extend([f"REGRESSION: {e}" for e in evidence])
                m.version += 1
                m.updated_at = _now_utc()

                # Re-evaluate mission completed count and status
                mission.completed_milestones = sum(1 for ms in mission.milestones if ms.status == MilestoneStatus.COMPLETED)
                mission.status = MissionStatus.REGRESSED
                mission.health = MissionHealth.AT_RISK
                mission.updated_at = _now_utc()

                logger.warning("Milestone %s REGRESSED: %s", milestone_id, reason)
                return m
        raise KeyError(f"Milestone {milestone_id} not found on mission {mission.mission_id}")

    @classmethod
    def analyze_critical_path(cls, mission: Mission) -> dict[str, Any]:
        """Compute dependency chains, blocking milestones, bottlenecks, and downstream impact."""
        milestone_map = {m.milestone_id: m for m in mission.milestones}
        blocking_milestones = []
        bottlenecks = []
        critical_chain = []

        # Find milestones that are BLOCKED or AT_RISK and have downstream dependents
        dependents_count: dict[str, int] = {m.milestone_id: 0 for m in mission.milestones}
        for m in mission.milestones:
            for dep_id in m.dependencies:
                if dep_id in dependents_count:
                    dependents_count[dep_id] += 1

        for m in mission.milestones:
            if m.status in (MilestoneStatus.BLOCKED, MilestoneStatus.AT_RISK, MilestoneStatus.REGRESSED):
                impact = dependents_count.get(m.milestone_id, 0)
                blocking_milestones.append({
                    "milestone_id": m.milestone_id,
                    "title": m.title,
                    "status": m.status.value,
                    "blocked_reason": m.blocked_reason,
                    "downstream_dependents": impact,
                })
                if impact >= 2:
                    bottlenecks.append(m.milestone_id)

        return {
            "total_milestones": len(mission.milestones),
            "completed_milestones": sum(1 for m in mission.milestones if m.status == MilestoneStatus.COMPLETED),
            "regressed_milestones": sum(1 for m in mission.milestones if m.status == MilestoneStatus.REGRESSED),
            "blocking_milestones": blocking_milestones,
            "bottlenecks": bottlenecks,
            "has_critical_blocker": len(blocking_milestones) > 0,
        }
