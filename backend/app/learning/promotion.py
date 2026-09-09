"""Governed strategy promotion engine for Kairo Learning Engine (Task 43)."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.learning.strategies import Strategy, StrategyStatus

logger = logging.getLogger("kairo.learning.promotion")


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class PromotionRecord:
    """Audit record of a strategy promotion or rejection (Spec 51, 135)."""

    promotion_id: str
    strategy_id: str
    from_status: StrategyStatus
    to_status: StrategyStatus
    reason: str
    approved_by: str
    timestamp: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "promotion_id": self.promotion_id,
            "strategy_id": self.strategy_id,
            "from_status": self.from_status.value,
            "to_status": self.to_status.value,
            "reason": self.reason,
            "approved_by": self.approved_by,
            "timestamp": self.timestamp.isoformat(),
        }


class StrategyPromoter:
    """Evaluates candidate strategies against promotion criteria and governance (Spec 51-53, 185)."""

    def __init__(
        self,
        min_sample_size: int = 10,
        min_verification_rate: float = 0.80,
        max_failure_rate: float = 0.15,
    ) -> None:
        self.min_sample_size = min_sample_size
        self.min_verification_rate = min_verification_rate
        self.max_failure_rate = max_failure_rate
        self._history: list[PromotionRecord] = []

    def can_promote(self, strategy: Strategy) -> tuple[bool, str]:
        """Check if strategy meets objective criteria for ACTIVE promotion."""
        if strategy.status not in [StrategyStatus.CANDIDATE, StrategyStatus.EXPERIMENTAL]:
            return False, f"Strategy status '{strategy.status.value}' is not eligible for promotion."

        if strategy.sample_size < self.min_sample_size:
            return False, f"Insufficient sample size: {strategy.sample_size} < {self.min_sample_size} required."

        if strategy.verification_rate < self.min_verification_rate:
            return False, f"Verification rate too low: {strategy.verification_rate:.1%} < {self.min_verification_rate:.1%} required."

        if strategy.failure_rate > self.max_failure_rate:
            return False, f"Failure rate too high: {strategy.failure_rate:.1%} > {self.max_failure_rate:.1%} allowed."

        return True, "Criteria satisfied for promotion."

    def promote(
        self,
        strategy: Strategy,
        approved_by: str,
        reason: str = "Empirical criteria and governance satisfied",
    ) -> tuple[bool, str, PromotionRecord | None]:
        """Promote candidate strategy to ACTIVE status with audit trail."""
        eligible, msg = self.can_promote(strategy)
        if not eligible:
            return False, msg, None

        rec = PromotionRecord(
            promotion_id=f"prm_{uuid.uuid4().hex[:10]}",
            strategy_id=strategy.strategy_id,
            from_status=strategy.status,
            to_status=StrategyStatus.ACTIVE,
            reason=reason,
            approved_by=approved_by,
        )

        strategy.status = StrategyStatus.ACTIVE
        self._history.append(rec)
        logger.info("Promoted strategy '%s' to ACTIVE by '%s'", strategy.strategy_id, approved_by)
        return True, "Strategy promoted to ACTIVE.", rec

    def get_history(self) -> list[PromotionRecord]:
        return list(self._history)
