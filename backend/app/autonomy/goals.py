"""Goal Definition, Persistence, and Goal Drift Protection (Task 45)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger("kairo.autonomy.goals")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class GoalDriftError(Exception):
    """Raised when an autonomous execution loop begins pursuing an objective materially divergent from authorized goal."""


@dataclass
class AutonomousGoal:
    """Persistent, immutable root mission objective (Spec 2, 5, 7)."""

    goal_id: str
    title: str
    description: str
    user_id: str
    project_id: str = "default_project"
    success_criteria: List[str] = field(default_factory=list)
    hard_constraints: List[str] = field(default_factory=list)
    scope: Dict[str, Any] = field(default_factory=dict)
    status: str = "ACTIVE"
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "title": self.title,
            "description": self.description,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "success_criteria": self.success_criteria,
            "hard_constraints": self.hard_constraints,
            "scope": self.scope,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class GoalManager:
    """Coordinates goal persistence and validates actions against goal boundaries (Spec 5, 6)."""

    def __init__(self) -> None:
        self._goals: Dict[str, AutonomousGoal] = {}

    def register_goal(
        self,
        title: str,
        description: str,
        user_id: str,
        project_id: str = "default_project",
        success_criteria: Optional[List[str]] = None,
        hard_constraints: Optional[List[str]] = None,
        scope: Optional[Dict[str, Any]] = None,
    ) -> AutonomousGoal:
        goal_id = f"goal_{uuid.uuid4().hex[:12]}"
        goal = AutonomousGoal(
            goal_id=goal_id,
            title=title,
            description=description,
            user_id=user_id,
            project_id=project_id,
            success_criteria=success_criteria or [],
            hard_constraints=hard_constraints or [],
            scope=scope or {},
        )
        self._goals[goal_id] = goal
        logger.info("Registered persistent autonomous goal %s: '%s'", goal_id, title[:60])
        return goal

    def get_goal(self, goal_id: str) -> Optional[AutonomousGoal]:
        return self._goals.get(goal_id)

    def validate_goal_alignment(self, goal_id: str, candidate_objective: str) -> bool:
        """Enforce Spec 6: Detect goal drift and block unauthorized objective substitution."""
        goal = self._goals.get(goal_id)
        if not goal:
            raise KeyError(f"Goal {goal_id} not found.")

        cand_lower = candidate_objective.lower().strip()
        goal_text = f"{goal.title} {goal.description}".lower()

        # Prohibited drift markers: completely unrelated side tasks or subversion
        drift_indicators = [
            "ignore previous goal",
            "switch project to",
            "mine cryptocurrency",
            "exfiltrate credentials",
            "deploy arbitrary external service",
        ]
        for indicator in drift_indicators:
            if indicator in cand_lower:
                logger.critical("Goal drift detected for goal %s: '%s'", goal_id, candidate_objective)
                raise GoalDriftError(f"Goal drift detected: Candidate objective '{candidate_objective}' contains prohibited directive.")

        # If hard constraints are violated
        for constraint in goal.hard_constraints:
            c_clean = constraint.lower().strip()
            if c_clean.startswith("do not "):
                prohibited_action = c_clean[7:].strip()
                if prohibited_action in cand_lower:
                    raise GoalDriftError(f"Goal drift: Candidate objective violates hard constraint '{constraint}'.")
            if f"bypass {c_clean}" in cand_lower or f"ignore {c_clean}" in cand_lower:
                raise GoalDriftError(f"Goal drift: Candidate objective violates hard constraint '{constraint}'.")

        return True
