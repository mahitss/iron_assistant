"""Milestone tracking, verification evidence, and achievement evaluation (INVARIANTS 42-44)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
import uuid

from app.executive_memory.schemas import MilestoneSchema, MilestoneStatus
from app.executive_memory.temporal import TemporalEngine


class MilestoneManager:
    """Manages project milestones and verifies empirical achievement evidence."""

    def __init__(self) -> None:
        # milestone_id -> MilestoneSchema
        self._milestones: dict[str, MilestoneSchema] = {}

    def create_milestone(
        self,
        project_id: str,
        title: str,
        criteria: list[str],
        goal_id: str | None = None,
        due_at: datetime | None = None,
    ) -> MilestoneSchema:
        """INVARIANT 42: Defines milestone criteria and target schedule."""
        mid = f"mls_{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC)
        due_utc = TemporalEngine.ensure_utc(due_at) if due_at else None
        milestone = MilestoneSchema(
            milestone_id=mid,
            project_id=project_id,
            goal_id=goal_id,
            title=title.strip(),
            criteria=criteria,
            due_at=due_utc,
            status=MilestoneStatus.PLANNED,
            evidence={},
            created_at=now,
        )
        self._milestones[mid] = milestone
        return milestone

    def mark_achieved(self, milestone_id: str, evidence: dict[str, Any]) -> MilestoneSchema:
        """INVARIANT 44: Milestone completion requires evidence where appropriate."""
        if not evidence:
            raise ValueError("INVARIANT 44: Milestone completion requires empirical proof or verification telemetry.")

        m = self._milestones.get(milestone_id)
        if not m:
            raise ValueError(f"Milestone '{milestone_id}' not found.")

        m.status = MilestoneStatus.ACHIEVED
        m.evidence = evidence
        m.achieved_at = datetime.now(UTC)
        return m

    def list_milestones(self, project_id: str | None = None) -> list[MilestoneSchema]:
        results = list(self._milestones.values())
        if project_id:
            results = [m for m in results if m.project_id == project_id]
        return results
