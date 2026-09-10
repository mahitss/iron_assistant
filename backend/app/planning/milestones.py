"""Milestone state transitions, verification gates, and weighted progress (Task 58)."""

from __future__ import annotations

import logging
from datetime import datetime

from app.planning.schemas import MilestoneStatus, PlanMilestone

logger = logging.getLogger(__name__)


class MilestoneManager:
    """Manages strategic milestones representing key state transitions."""

    def create_milestone(
        self,
        name: str,
        phase_id: str | None = None,
        description: str = "",
        weight: float = 1.0,
        target_date: datetime | None = None,
        dependencies: list[str] | None = None,
        verification_criteria: list[str] | None = None,
    ) -> PlanMilestone:
        """Create a strategic milestone with defined verification criteria."""
        return PlanMilestone(
            name=name,
            phase_id=phase_id,
            description=description,
            weight=max(0.1, weight),
            target_date=target_date,
            status=MilestoneStatus.PENDING,
            dependencies=dependencies or [],
            verification_criteria=verification_criteria or [],
            is_verified=False,
        )

    def check_dependencies(
        self,
        milestone: PlanMilestone,
        reached_milestone_ids: set[str],
    ) -> tuple[bool, list[str]]:
        """Check if all prerequisite milestones have been reached."""
        unresolved = [dep for dep in milestone.dependencies if dep not in reached_milestone_ids]
        return len(unresolved) == 0, unresolved

    def verify_milestone(
        self,
        milestone: PlanMilestone,
        verification_evidence: list[str] | None = None,
        reached_milestone_ids: set[str] | None = None,
    ) -> tuple[bool, list[str]]:
        """Verify milestone completion. Requires both dependency satisfaction and verified evidence."""
        if reached_milestone_ids is not None:
            deps_ok, unresolved = self.check_dependencies(milestone, reached_milestone_ids)
            if not deps_ok:
                milestone.status = MilestoneStatus.BLOCKED
                return False, [f"Unresolved milestone dependency: {dep}" for dep in unresolved]

        evidence_set = set(verification_evidence or [])
        missing_evidence: list[str] = []

        for criterion in milestone.verification_criteria:
            if criterion not in evidence_set:
                missing_evidence.append(f"Missing verification evidence for: '{criterion}'")

        if missing_evidence:
            milestone.is_verified = False
            milestone.status = MilestoneStatus.PENDING
            return False, missing_evidence

        milestone.is_verified = True
        milestone.status = MilestoneStatus.REACHED
        logger.info("Milestone '%s' successfully verified and REACHED.", milestone.name)
        return True, []

    def evaluate_milestones_progress(self, milestones: list[PlanMilestone]) -> float:
        """Calculate weighted milestone progress percentage."""
        if not milestones:
            return 0.0

        total_weight = sum(m.weight for m in milestones)
        if total_weight <= 0.0:
            return 0.0

        reached_weight = sum(m.weight for m in milestones if m.status == MilestoneStatus.REACHED and m.is_verified)
        return round((reached_weight / total_weight) * 100.0, 2)


milestone_manager = MilestoneManager()
