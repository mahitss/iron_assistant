"""Goal Alignment & Ethical Constraints Engine: evaluating actions against human and safety objectives (Task 78)."""

from __future__ import annotations

import logging
from typing import Any

from app.policy.governance_schemas import GoalAlignmentReport

logger = logging.getLogger(__name__)


class GoalAlignmentEngine:
    """Evaluates whether an autonomous action advances human intent, project objectives, and safety invariants.

    Core Axiom:
    Possible does not imply permissible.
    """

    def evaluate_alignment(
        self,
        goal: str,
        action: str,
        resource: str,
        user_intent: str | None = None,
        project_milestones: list[str] | None = None,
        is_destructive: bool = False,
        is_irreversible: bool = False,
        context: dict[str, Any] | None = None,
    ) -> GoalAlignmentReport:
        """Analyze multi-tier goal alignment and detect ethical divergence."""
        ctx = context or {}
        conflicts = []

        user_aligned = True
        project_aligned = True
        constitutional_aligned = True
        safety_aligned = True

        goal_lower = goal.lower()
        action_lower = action.lower()

        # 1. Safety Goal Alignment
        # If action bypasses limits or destroys data without explicit directive, safety goal is violated
        if is_destructive and not ("delete" in goal_lower or "cleanup" in goal_lower or "remove" in goal_lower):
            safety_aligned = False
            conflicts.append("Destructive action diverges from non-destructive user goal.")

        # 2. Ethical / Security Goal Alignment
        if any(w in action_lower for w in ["disable_firewall", "leak", "exfiltrate", "bypass_auth", "override_stop"]):
            constitutional_aligned = False
            safety_aligned = False
            conflicts.append("Action violates fundamental constitutional safety constraints.")

        # 3. Proportionality / Goal Subversion Check
        if ctx.get("excessive_cost", False):
            project_aligned = False
            conflicts.append("Action cost is disproportionate to project milestones.")

        # 4. User Authority Check
        if user_intent and "read_only" in user_intent.lower() and is_destructive:
            user_aligned = False
            conflicts.append("Action mutates state while user intent is read-only.")

        return GoalAlignmentReport(
            user_goals_aligned=user_aligned,
            project_goals_aligned=project_aligned,
            constitutional_aligned=constitutional_aligned,
            safety_aligned=safety_aligned,
            conflicts_detected=conflicts,
        )


default_goal_alignment_engine = GoalAlignmentEngine()
