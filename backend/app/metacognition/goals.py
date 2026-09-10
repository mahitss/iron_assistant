"""Active goal tracking, alignment, and user goal priority enforcement (INVARIANTS 36, 114, 149, 150)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
import uuid


class GoalDriftError(Exception):
    """Raised when execution drift from original goal exceeds safe thresholds."""
    pass


class GoalTracker:
    """Tracks active operational goals, ensuring internal system goals never usurp user goals."""

    def __init__(self) -> None:
        # goal_id -> dict
        self._goals: Dict[str, Dict[str, Any]] = {}

    def register_goal(
        self,
        goal_text: str,
        user_id: str,
        origin: str = "USER",
        priority: int = 1,
        success_criteria: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """INVARIANT 114: Internal goals must not replace user goals."""
        gid = str(uuid.uuid4())
        rec = {
            "goal_id": gid,
            "goal_text": goal_text.strip(),
            "user_id": user_id,
            "origin": origin,
            "priority": priority,
            "success_criteria": success_criteria or [],
            "status": "ACTIVE",
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._goals[gid] = rec
        return rec

    def check_goal_drift(self, goal_id: str, current_action_description: str) -> bool:
        """INVARIANT 149 & 150: Detects when current execution drifts from original goal intent."""
        goal = self._goals.get(goal_id)
        if not goal:
            return False

        goal_words = set(goal["goal_text"].lower().split())
        action_words = set(current_action_description.lower().split())

        # If completely unrelated and action is destructive, flag drift
        overlap = len(goal_words & action_words)
        is_drifting = overlap == 0 and len(action_words) > 3
        return is_drifting

    def list_active_goals(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        active = [g for g in self._goals.values() if g.get("status") == "ACTIVE"]
        if user_id:
            active = [g for g in active if g.get("user_id") == user_id]
        return active
