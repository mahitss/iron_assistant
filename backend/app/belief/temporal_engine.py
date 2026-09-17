"""Temporal Reasoning and Freshness Engine for Task 107.

Domain-specific TTL policies:
- CPU / resource telemetry: seconds/minutes (30s - 300s)
- Capability readiness / service health: minutes/hours (600s - 3600s)
- System architecture / topology: days/weeks (86400s - 604800s)
- Long-term strategy assumptions: months (2592000s)

Strict Invariant:
Stale != Zero confidence.
Staleness implies current evidence is insufficient to maintain confident certainty.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
import math
from typing import Dict, List, Optional, Tuple

from app.belief.domain import (
    Belief,
    BeliefStatus,
    UncertaintyType,
    utc_now,
)

logger = logging.getLogger("kairo.belief.temporal")

# Default TTL policies by subject/predicate pattern
PREDICATE_TTL_MAP: Dict[str, int] = {
    "cpu_usage": 60,
    "memory_pressure": 60,
    "latency_ms": 120,
    "telemetry": 180,
    "is_ready": 900,
    "is_available": 900,
    "health_status": 1800,
    "capability_version": 7200,
    "topology": 86400,
    "architecture": 604800,
    "strategy_performance": 2592000,
}


class TemporalFreshnessEngine:
    """Manages temporal decay, TTL policies, and staleness detection."""

    def compute_ttl_for_belief(self, subject: str, predicate: str) -> int:
        """Resolve domain-specific TTL in seconds."""
        pred_lower = predicate.lower()
        for pattern, ttl in PREDICATE_TTL_MAP.items():
            if pattern in pred_lower:
                return ttl
        if "cpu" in subject.lower() or "metric" in subject.lower():
            return 120
        if "capability" in subject.lower() or "service" in subject.lower():
            return 1800
        return 3600  # Default 1 hour fallback

    def evaluate_freshness(self, belief: Belief, as_of: Optional[datetime] = None) -> Tuple[bool, float, BeliefStatus]:
        """Evaluate whether a belief has become stale or expired.
        
        Returns:
            (is_stale, decayed_confidence, recommended_status)
        """
        now = as_of or utc_now()

        # 1. Hard expiry check
        if belief.valid_until and belief.valid_until < now:
            return True, max(0.0, belief.confidence * 0.5), BeliefStatus.EXPIRED

        # 2. Staleness based on last verification
        anchor_time = belief.last_verified_at or belief.valid_from
        elapsed_seconds = (now - anchor_time).total_seconds()
        ttl = belief.freshness_ttl_seconds or 3600

        if elapsed_seconds <= ttl:
            # Fully fresh
            return False, belief.confidence, belief.status

        # Evidence aged beyond TTL: calculate smooth exponential decay
        decay_factor = math.exp(-0.2 * (elapsed_seconds / ttl))
        decayed_conf = max(0.1, round(belief.confidence * decay_factor, 3))

        # Status transition: Stale or Revalidation Required
        if belief.status in {BeliefStatus.CONFIDENT, BeliefStatus.SUPPORTED}:
            rec_status = BeliefStatus.REVALIDATION_REQUIRED if decayed_conf >= 0.4 else BeliefStatus.STALE
        elif belief.status in {BeliefStatus.PROVISIONAL, BeliefStatus.CANDIDATE}:
            rec_status = BeliefStatus.STALE
        elif belief.status not in {BeliefStatus.EXPIRED, BeliefStatus.SUPERSEDED, BeliefStatus.REJECTED}:
            rec_status = BeliefStatus.STALE
        else:
            rec_status = belief.status

        return True, decayed_conf, rec_status

    def apply_freshness_check(self, belief: Belief) -> bool:
        """Mutate belief in-place if staleness or expiry has occurred."""
        is_stale, decayed_conf, rec_status = self.evaluate_freshness(belief)
        changed = False

        if is_stale != belief.is_stale:
            belief.is_stale = is_stale
            changed = True

        if is_stale:
            if belief.status != rec_status and belief.status not in {BeliefStatus.SUPERSEDED, BeliefStatus.REJECTED}:
                logger.info(
                    "BELIEF_STALE_TRANSITION: Belief %s aged past TTL (%ds). Status %s -> %s (conf %.2f -> %.2f)",
                    belief.belief_id,
                    belief.freshness_ttl_seconds,
                    belief.status.value,
                    rec_status.value,
                    belief.confidence,
                    decayed_conf,
                )
                belief.status = rec_status
                belief.confidence = decayed_conf
                belief.uncertainty = round(1.0 - decayed_conf, 3)
                belief.uncertainty_type = UncertaintyType.STALE
                changed = True

        return changed
