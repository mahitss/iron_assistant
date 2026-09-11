"""Goal Drift, Objective Drift (Goodhart's Law), and Revalidation Detector (Task 66)."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from app.missions.schemas import (
    Goal,
    GoalDriftAlert,
    Mission,
    MissionHealth,
)

logger = logging.getLogger("kairo.missions.drift")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class GoalDriftDetector:
    """Monitors mission trajectory against original authorized intent to detect drift and proxy gaming."""

    @classmethod
    def check_goal_drift(
        cls,
        mission: Mission,
        goal: Goal,
        recent_action_summaries: list[str],
    ) -> GoalDriftAlert | None:
        """Detect when execution gradually moves away from the original goal (Spec 19).

        Example: Original: reduce latency. Later: reducing costs by scaling down nodes, causing higher latency.
        """
        if not recent_action_summaries or len(recent_action_summaries) < 3:
            return None

        goal_keywords = set(re.findall(r"\b\w{4,}\b", f"{goal.title} {goal.description}".lower()))
        action_text = " ".join(recent_action_summaries).lower()
        action_keywords = set(re.findall(r"\b\w{4,}\b", action_text))

        overlap = len(goal_keywords.intersection(action_keywords))
        total = max(1, len(goal_keywords))
        similarity = overlap / total

        # If similarity dropped below 0.2 and actions pursue unrelated topics
        divergence = 1.0 - similarity
        if divergence > 0.75:
            alert = GoalDriftAlert(
                mission_id=mission.mission_id,
                goal_id=goal.goal_id,
                original_objective=goal.title,
                current_trajectory="; ".join(recent_action_summaries[-3:]),
                divergence_score=round(divergence, 2),
                trigger_reassessment=True,
            )
            mission.health = MissionHealth.DRIFTING
            logger.warning(
                "GOAL_DRIFT_DETECTED: Mission %s divergence=%.2f. Triggering reassessment.",
                mission.mission_id,
                divergence,
            )
            return alert

        return None

    @classmethod
    def detect_objective_drift(
        cls,
        mission: Mission,
        goal: Goal,
        proxy_metric: str,
        true_objective_metric: str,
        proxy_change_pct: float,
        true_objective_change_pct: float,
    ) -> GoalDriftAlert | None:
        """Enforce OBJECTIVE DRIFT & GOODHART'S LAW DEFENSE (Spec 20).

        Example: Goal is 'improve reliability'. Proxy is 'reduce incident count'.
        If incident reporting is suppressed (proxy improves by 50%), but actual system
        error rate degrades (true objective degrades by 20%), flag OBJECTIVE_DRIFT.
        """
        # When proxy appears improved but true objective is degrading or stagnant
        if proxy_change_pct > 15.0 and true_objective_change_pct < -5.0:
            alert = GoalDriftAlert(
                mission_id=mission.mission_id,
                goal_id=goal.goal_id,
                original_objective=f"True objective '{true_objective_metric}' vs proxy '{proxy_metric}'",
                current_trajectory=f"Proxy '{proxy_metric}' changed by +{proxy_change_pct:.1f}%, but true objective '{true_objective_metric}' degraded by {true_objective_change_pct:.1f}%.",
                divergence_score=0.9,
                is_objective_drift=True,
                trigger_reassessment=True,
            )
            mission.health = MissionHealth.DRIFTING
            logger.error(
                "OBJECTIVE_DRIFT_GOODHARTS_LAW: Mission %s is gaming proxy '%s' while true metric '%s' degrades.",
                mission.mission_id,
                proxy_metric,
                true_objective_metric,
            )
            return alert

        return None
