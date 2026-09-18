"""Staleness Detection and Cache Invalidation Engine for Task 114.
Detects when observation plans, candidate options, or cached evidence items become obsolete.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

from app.observation.domain import ObservationPlan, utc_now

logger = logging.getLogger("kairo.observation.staleness_engine")


class ObservationStalenessEngine:
    """Monitors observation plans for environmental drift and temporal staleness (Section 44, 58)."""

    @classmethod
    def check_staleness(
        cls,
        plan: ObservationPlan,
        current_world_state: Optional[Dict[str, Any]] = None,
        deadline_seconds: Optional[float] = None,
    ) -> Tuple[bool, str]:
        """Evaluates whether plan is stale and should be refreshed or invalidated."""
        current_world_state = current_world_state or {}

        # 1. Temporal Staleness
        age_seconds = (utc_now() - plan.created_at).total_seconds()
        if deadline_seconds and age_seconds > deadline_seconds:
            return True, f"Plan exceeded operational deadline ({age_seconds:.1f}s > {deadline_seconds:.1f}s)."

        # Default max TTL for an unexecuted plan is 300 seconds
        if age_seconds > 300.0:
            return True, f"Observation plan expired (age {age_seconds:.1f}s > 300s TTL)."

        # 2. State Drift Staleness
        target_state = current_world_state.get(plan.target_entity, {})
        if target_state.get("is_invalidated") or target_state.get("drift_detected"):
            return True, f"Target entity '{plan.target_entity}' underwent state drift in world model."

        return False, ""
