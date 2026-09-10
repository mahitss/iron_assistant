"""Goal continuity, causal link tracing, and qualitative progress synthesis (INVARIANTS 45-48)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.executive_memory.schemas import QualitativeProgress


class GoalContinuityManager:
    """Connects goals to tasks, decisions, and outcomes with qualitative progress synthesis."""

    def __init__(self) -> None:
        # goal_id -> goal dict
        self._goals: dict[str, dict[str, Any]] = {}
        # goal_id -> list of task_ids
        self._goal_tasks: dict[str, list[str]] = {}
        # goal_id -> list of decision_ids
        self._goal_decisions: dict[str, list[str]] = {}
        # goal_id -> list of outcome_ids
        self._goal_outcomes: dict[str, list[str]] = {}

    def create_goal(
        self,
        title: str,
        success_criteria: str | list[str] | None = None,
        project_id: str | None = None,
        goal_id: str | None = None,
    ) -> dict[str, Any]:
        """Creates and registers a project goal."""
        import uuid
        gid = goal_id or f"goal_{uuid.uuid4().hex[:12]}"
        criteria = [success_criteria] if isinstance(success_criteria, str) else (success_criteria or [])
        now = datetime.now(UTC)
        record = {
            "goal_id": gid,
            "title": title,
            "project_id": project_id,
            "target_criteria": criteria,
            "progress": QualitativeProgress.NOT_STARTED,
            "created_at": now.isoformat(),
        }
        self._goals[gid] = record
        return record

    def register_goal(
        self,
        goal_id: str,
        title: str,
        project_id: str | None = None,
        target_criteria: list[str] | None = None,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        record = {
            "goal_id": goal_id,
            "title": title,
            "project_id": project_id,
            "target_criteria": target_criteria or [],
            "progress": QualitativeProgress.NOT_STARTED,
            "created_at": now.isoformat(),
        }
        self._goals[goal_id] = record
        return record

    def estimate_progress(self, goal_id: str) -> QualitativeProgress:
        """INVARIANT 46-48: Estimates qualitative progress without fake percentages."""
        goal = self._goals.get(goal_id)
        if not goal:
            return QualitativeProgress.UNKNOWN
        return goal.get("progress", QualitativeProgress.NOT_STARTED)

    def update_progress(
        self,
        goal_id: str,
        qualitative_progress: QualitativeProgress,
        evidence: str | None = None,
    ) -> dict[str, Any]:
        """INVARIANT 48: Explicit qualitative progress update backed by evidence."""
        goal = self._goals.get(goal_id)
        if not goal:
            raise KeyError(f"Goal '{goal_id}' not found.")
        goal["progress"] = qualitative_progress
        if evidence:
            goal["progress_evidence"] = evidence
        return goal

    def link_goal_components(
        self,
        goal_id: str,
        task_id: str | None = None,
        decision_id: str | None = None,
        outcome_id: str | None = None,
    ) -> None:
        """INVARIANT 45: Connects Goal -> Tasks -> Decisions -> Outcomes."""
        if task_id:
            self._goal_tasks.setdefault(goal_id, []).append(task_id)
        if decision_id:
            self._goal_decisions.setdefault(goal_id, []).append(decision_id)
        if outcome_id:
            self._goal_outcomes.setdefault(goal_id, []).append(outcome_id)

    def estimate_qualitative_progress(
        self,
        goal_id: str,
        completed_tasks_count: int = 0,
        total_tasks_count: int = 0,
        is_blocked: bool = False,
    ) -> QualitativeProgress:
        """INVARIANT 47 & 48: Returns qualitative progress enum instead of fabricated percentages."""
        if is_blocked:
            return QualitativeProgress.BLOCKED
        if total_tasks_count == 0:
            return QualitativeProgress.NOT_STARTED
        if completed_tasks_count == 0:
            return QualitativeProgress.EARLY
        if completed_tasks_count == total_tasks_count:
            return QualitativeProgress.COMPLETE
        ratio = completed_tasks_count / total_tasks_count
        if ratio >= 0.8:
            return QualitativeProgress.NEAR_COMPLETE
        return QualitativeProgress.IN_PROGRESS

    def get_goal_trace(self, goal_id: str) -> dict[str, Any]:
        """Traces the complete goal causal lineage."""
        return {
            "goal": self._goals.get(goal_id),
            "tasks": self._goal_tasks.get(goal_id, []),
            "decisions": self._goal_decisions.get(goal_id, []),
            "outcomes": self._goal_outcomes.get(goal_id, []),
        }
