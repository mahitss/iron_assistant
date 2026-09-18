"""Freshness Engine for Task 110:
Evaluates context element freshness against timestamps, domain volatility, and expiry policies.

Strict Invariants:
- RECENCY != CORRECTNESS (Recency is tracked explicitly, but does not guarantee truth).
- Stale items may be preserved as historical context, but MUST NOT masquerade as current state.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from typing import Optional, Tuple

from app.context.working_set_domain import (
    ContextFreshness,
    FreshnessClassification,
    utc_now,
)


class FreshnessEngine:
    """Evaluates the epistemic and temporal freshness of candidate context items."""

    # Default half-life in seconds per domain volatility tier
    VOLATILITY_HALF_LIVES = {
        0.1: 86400.0 * 30,  # Static code / docs (30 days)
        0.3: 86400.0 * 7,   # User preferences / beliefs (7 days)
        0.5: 86400.0,       # Standard operational state (24 hours)
        0.8: 3600.0,        # Dynamic attention / situation (1 hour)
        1.0: 60.0,          # Live telemetry / volatile sensors (60 seconds)
    }

    @classmethod
    def evaluate_freshness(
        cls,
        source_timestamp: datetime,
        domain_volatility: float = 0.5,
        expiry_timestamp: Optional[datetime] = None,
        requested_freshness_seconds: Optional[float] = None,
    ) -> ContextFreshness:
        """Calculate staleness score and categorical classification for a context element."""
        now = utc_now()

        # Ensure timezone-awareness
        if source_timestamp.tzinfo is None:
            source_timestamp = source_timestamp.replace(tzinfo=UTC)

        age_seconds = max(0.0, (now - source_timestamp).total_seconds())

        # Check explicit expiry
        if expiry_timestamp is not None:
            if expiry_timestamp.tzinfo is None:
                expiry_timestamp = expiry_timestamp.replace(tzinfo=UTC)
            if now >= expiry_timestamp:
                return ContextFreshness(
                    classification=FreshnessClassification.EXPIRED,
                    source_timestamp=source_timestamp,
                    effective_timestamp=now,
                    expiry_timestamp=expiry_timestamp,
                    last_validated_at=now,
                    age_seconds=age_seconds,
                    domain_volatility_score=domain_volatility,
                    staleness_score=1.0,
                )

        # Estimate half-life based on volatility
        closest_tier = min(cls.VOLATILITY_HALF_LIVES.keys(), key=lambda k: abs(k - domain_volatility))
        half_life = cls.VOLATILITY_HALF_LIVES[closest_tier]

        # Exponential decay: staleness = 1.0 - (0.5 ^ (age / half_life))
        staleness = 1.0 - math.pow(0.5, (age_seconds / half_life))
        staleness = round(min(1.0, max(0.0, staleness)), 4)

        # Categorical classification
        if requested_freshness_seconds and age_seconds > requested_freshness_seconds:
            classification = FreshnessClassification.STALE
        elif staleness < 0.15:
            classification = FreshnessClassification.FRESH
        elif staleness < 0.40:
            classification = FreshnessClassification.RECENT
        elif staleness < 0.75:
            classification = FreshnessClassification.AGING
        else:
            classification = FreshnessClassification.STALE

        return ContextFreshness(
            classification=classification,
            source_timestamp=source_timestamp,
            effective_timestamp=now,
            expiry_timestamp=expiry_timestamp,
            last_validated_at=now,
            age_seconds=round(age_seconds, 2),
            domain_volatility_score=domain_volatility,
            staleness_score=staleness,
        )
