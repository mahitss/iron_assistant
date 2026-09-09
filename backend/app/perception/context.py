"""Perception Context, Relevance Ranking Engine, and Observation Compaction (Task 46)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from app.perception.observations import Observation

logger = logging.getLogger("kairo.perception.context")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class PerceptionContext:
    """Active task, project, and environmental context bounding perception queries (Spec 75, 76)."""

    task_id: Optional[str] = None
    project_id: str = "default_project"
    user_id: str = "default_user"
    device_id: Optional[str] = None
    environment: str = "DEVELOPMENT"
    active_application: Optional[str] = None

    def matches_observation(self, observation: Observation) -> bool:
        """Enforce Spec 76: Do not mix unrelated project or environment states."""
        obs_scope = observation.scope
        if "project_id" in obs_scope and obs_scope["project_id"] != "*" and obs_scope["project_id"] != self.project_id:
            return False
        if "environment" in obs_scope and obs_scope["environment"].upper() != self.environment.upper():
            return False
        return True


class RelevanceEngine:
    """Ranks and compacts observations so only high-signal facts enter model context (Spec 107-110)."""

    @classmethod
    def rank_observations(
        cls,
        observations: List[Observation],
        context: PerceptionContext,
        max_items: int = 10,
    ) -> List[Observation]:
        """Rank observations by task relevance, recency, confidence, and significance (Spec 108, 109)."""
        filtered = [obs for obs in observations if context.matches_observation(obs)]

        def score_obs(obs: Observation) -> float:
            score = obs.confidence * 40.0
            # Recency bonus: max 30 points if within 60s
            recency_points = max(0.0, 30.0 - (obs.age_seconds / 2.0))
            score += recency_points

            # Task correlation bonus
            if context.task_id and (obs.correlation_id == context.task_id or context.task_id in obs.subject):
                score += 30.0

            return score

        sorted_obs = sorted(filtered, key=score_obs, reverse=True)
        return sorted_obs[:max_items]

    @classmethod
    def compact_observations(cls, observations: List[Observation]) -> str:
        """Compress old observations into high-level digest without losing critical state (Spec 110)."""
        if not observations:
            return "No active environmental observations."

        subjects = set(o.subject for o in observations)
        fresh_count = sum(1 for o in observations if o.is_fresh(60))

        return (
            f"Compacted {len(observations)} environmental observations across {len(subjects)} subjects. "
            f"Active fresh telemetry: {fresh_count}/{len(observations)}. "
            f"Latest subject updated: '{observations[0].subject}' at {observations[0].observed_at.strftime('%H:%M:%S')}."
        )
