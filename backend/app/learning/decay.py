"""Environmental decay and strategy invalidation on environment changes (Task 43)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from app.learning.strategies import Strategy, StrategyStatus

logger = logging.getLogger("kairo.learning.decay")


def utc_now() -> datetime:
    return datetime.now(UTC)


class EnvironmentalDecayManager:
    """Manages temporal decay and invalidates strategies on tool/model changes (Spec 40-43, 150-154)."""

    def __init__(self, half_life_days: int = 30) -> None:
        self.half_life_days = half_life_days

    def apply_temporal_decay(self, strategy: Strategy, as_of: datetime | None = None) -> Strategy:
        """Decay strategy confidence if evidence is stale."""
        now = as_of or utc_now()
        age_days = (now - strategy.updated_at).total_seconds() / 86400.0

        if age_days > (self.half_life_days * 2) and strategy.confidence == "HIGH":
            logger.info("Degrading strategy '%s' confidence HIGH -> MEDIUM due to age (%.1f days)", strategy.strategy_id, age_days)
            strategy.confidence = "MEDIUM"
        elif age_days > (self.half_life_days * 3) and strategy.confidence == "MEDIUM":
            logger.info("Degrading strategy '%s' confidence MEDIUM -> LOW due to age (%.1f days)", strategy.strategy_id, age_days)
            strategy.confidence = "LOW"

        return strategy

    def handle_environment_change(
        self,
        strategies: list[Strategy],
        change_type: str,  # "model_version", "tool_version", "policy", "dependency"
        affected_domain_or_tool: str,
    ) -> list[Strategy]:
        """Flag or demote affected strategies upon major environmental shift (Spec 43, 151-153)."""
        target = affected_domain_or_tool.strip().lower()
        affected: list[Strategy] = []

        for strat in strategies:
            matches_domain = strat.domain.strip().lower() == target
            matches_prereqs = any(target in str(p).lower() for p in strat.prerequisites)

            if matches_domain or matches_prereqs:
                if strat.status == StrategyStatus.ACTIVE:
                    logger.warning(
                        "Environment change '%s' on '%s': Demoting active strategy '%s' to EXPERIMENTAL for reevaluation",
                        change_type,
                        target,
                        strat.strategy_id,
                    )
                    strat.status = StrategyStatus.EXPERIMENTAL
                    strat.confidence = "LOW"
                    strat.updated_at = utc_now()
                    affected.append(strat)

        return affected
