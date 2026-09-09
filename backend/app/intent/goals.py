"""User Goal Modeling, Desired State Definition, and Success Criteria Extraction (Task 48)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from app.intent.schemas import GoalStatus, UrgencyLevel

logger = logging.getLogger("kairo.intent.goals")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Goal:
    """Represents a desired user outcome, strictly distinct from execution tasks (Spec 9, 10).
    
    CRITICAL INVARIANT (Spec 10):
    Goal: desired outcome (e.g., 'Website load time < 2 seconds').
    Task: specific execution step (e.g., 'Optimize image compression').
    Do not confuse them!
    """

    description: str
    intent_id: str
    goal_id: str = field(default_factory=lambda: f"goal_{uuid.uuid4().hex[:10]}")
    desired_state: Dict[str, Any] = field(default_factory=dict)
    success_criteria: List[Dict[str, Any]] = field(default_factory=list)
    objectives: List[Dict[str, Any]] = field(default_factory=list)
    scope: Dict[str, Any] = field(default_factory=dict)
    constraints: List[Dict[str, Any]] = field(default_factory=list)
    priority: UrgencyLevel = UrgencyLevel.NORMAL
    deadline: Optional[datetime] = None
    owner: str = "user"
    status: GoalStatus = GoalStatus.ACTIVE
    version: int = 1
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def update_status(self, status: GoalStatus) -> None:
        self.status = status
        self.updated_at = utc_now()
        logger.info("Goal %s status updated to %s", self.goal_id, status.value)

    def update_description(self, new_description: str) -> None:
        self.description = new_description
        self.version += 1
        self.updated_at = utc_now()
        logger.info("Goal %s description updated (v%d): %s", self.goal_id, self.version, new_description)

    def mark_achieved(self) -> None:
        self.status = GoalStatus.ACHIEVED
        self.updated_at = utc_now()
        logger.info("Goal %s marked as ACHIEVED: %s", self.goal_id, self.description)

    def mark_blocked(self, reason: str) -> None:
        self.status = GoalStatus.BLOCKED
        self.updated_at = utc_now()
        logger.warning("Goal %s BLOCKED: %s", self.goal_id, reason)

    def cancel(self, reason: Optional[str] = None) -> None:
        self.status = GoalStatus.CANCELLED
        self.updated_at = utc_now()
        logger.info("Goal %s CANCELLED: %s", self.goal_id, reason or "User requested cancellation")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "intent_id": self.intent_id,
            "description": self.description,
            "desired_state": self.desired_state,
            "success_criteria": self.success_criteria,
            "objectives": self.objectives,
            "scope": self.scope,
            "constraints": self.constraints,
            "priority": self.priority.value if hasattr(self.priority, "value") else str(self.priority),
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "owner": self.owner,
            "status": self.status.value if hasattr(self.status, "value") else str(self.status),
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class GoalManager:
    """Maintains active user goals and enforces the Goal vs Task abstraction boundary (Spec 9, 10, 72, 73)."""

    def __init__(self) -> None:
        # goal_id -> Goal
        self._goals: Dict[str, Goal] = {}

    def create_goal(
        self,
        intent_id: str,
        description: str,
        desired_state: Optional[Dict[str, Any]] = None,
        success_criteria: Optional[List[Dict[str, Any]]] = None,
        scope: Optional[Dict[str, Any]] = None,
        constraints: Optional[List[Dict[str, Any]]] = None,
        priority: UrgencyLevel = UrgencyLevel.NORMAL,
        deadline: Optional[Any] = None,
        owner: str = "user",
    ) -> Goal:
        gid = f"goal_{uuid.uuid4().hex[:10]}"
        parsed_deadline = None
        if isinstance(deadline, datetime):
            parsed_deadline = deadline
        elif isinstance(deadline, str) and deadline.strip():
            try:
                parsed_deadline = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
            except Exception:
                parsed_deadline = None

        g = Goal(
            goal_id=gid,
            intent_id=intent_id,
            description=description,
            desired_state=desired_state or {},
            success_criteria=success_criteria or [],
            scope=scope or {},
            constraints=constraints or [],
            priority=priority,
            deadline=parsed_deadline,
            owner=owner,
            status=GoalStatus.ACTIVE,
        )
        self._goals[gid] = g
        logger.info("Created Goal %s: '%s' (owner=%s, priority=%s)", gid, description, owner, priority.value)
        return g

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        return self._goals.get(goal_id)

    def list_goals(
        self,
        user_id: Optional[str] = None,
        owner: Optional[str] = None,
        status: Optional[GoalStatus] = None,
    ) -> List[Goal]:
        res = list(self._goals.values())
        target_owner = owner or user_id
        if target_owner:
            res = [g for g in res if g.owner == target_owner]
        if status:
            res = [g for g in res if g.status == status]
        return res

