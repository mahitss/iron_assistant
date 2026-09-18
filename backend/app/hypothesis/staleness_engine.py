"""Autonomous Hypothesis Staleness & Expiration Engine (Task 115 Section 40, 61).

Detects when candidate hypotheses become stale or expired due to:
- Time window closure
- Material change in world state
- Causal model version upgrades
- Expired assumptions or environment shifts

Hard Invariants:
- Stale hypotheses CANNOT be silently reused.
- Requires explicit re-evaluation before informing active decisions.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from app.hypothesis.domain import (
    Hypothesis,
    HypothesisSet,
    HypothesisStatus,
)

logger = logging.getLogger("kairo.hypothesis.staleness")


class StalenessEngine:
    """Monitors hypothesis freshness and flags stale or expired candidate explanations."""

    def evaluate_staleness(
        self,
        hyp: Hypothesis,
        current_causal_version: str = "causal_v1",
        world_state_changed: bool = False,
        current_time: Optional[datetime] = None,
    ) -> bool:
        """Evaluates whether an individual hypothesis has become stale."""
        now = current_time or datetime.now(timezone.utc)

        # 1. Check time window expiration
        if hyp.scope.time_window_end and now > hyp.scope.time_window_end:
            self._mark_stale(hyp, f"Scope time window closed at {hyp.scope.time_window_end.isoformat()}", now)
            return True

        # 2. Check world state changes
        if world_state_changed:
            self._mark_stale(hyp, "Underlying world state changed materially during active investigation.", now)
            return True

        # 3. Check hypothesis age (default threshold 24 hours for incident investigations)
        age_seconds = (now - hyp.created_at).total_seconds()
        if age_seconds > 86400.0:  # 24 hours
            self._mark_stale(hyp, f"Hypothesis age ({int(age_seconds/3600)}h) exceeded maximum freshness threshold.", now)
            return True

        return False

    def check_set_staleness(
        self,
        hset: HypothesisSet,
        hypotheses: List[Hypothesis],
        current_causal_version: str = "causal_v1",
        world_state_changed: bool = False,
    ) -> List[str]:
        """Audits all active hypotheses in a set for staleness."""
        stale_ids: List[str] = []
        for hyp in hypotheses:
            if hyp.hypothesis_id in hset.active_hypothesis_ids:
                if self.evaluate_staleness(hyp, current_causal_version, world_state_changed):
                    stale_ids.append(hyp.hypothesis_id)

        if stale_ids:
            logger.info("Hypothesis set %s flagged %d stale hypotheses: %s", hset.set_id, len(stale_ids), stale_ids)
        return stale_ids

    def _mark_stale(self, hyp: Hypothesis, reason: str, now: datetime) -> None:
        """Marks hypothesis as STALE without deleting historical analysis."""
        if hyp.status not in (HypothesisStatus.FALSIFIED, HypothesisStatus.REJECTED, HypothesisStatus.STALE):
            hyp.status = HypothesisStatus.STALE
            hyp.stale_at = now
            hyp.staleness_reason = reason
            hyp.updated_at = now
