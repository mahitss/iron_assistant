"""Automated regression detection and rollback engine for Kairo Learning Engine (Task 43)."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.learning.strategies import Strategy, StrategyStatus

logger = logging.getLogger("kairo.learning.rollback")


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class RollbackRecord:
    """Audit record of an emergency or automated strategy rollback (Spec 54, 118)."""

    rollback_id: str
    strategy_id: str
    prior_status: StrategyStatus
    trigger_reason: str
    rolled_back_by: str
    timestamp: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rollback_id": self.rollback_id,
            "strategy_id": self.strategy_id,
            "prior_status": self.prior_status.value,
            "trigger_reason": self.trigger_reason,
            "rolled_back_by": self.rolled_back_by,
            "timestamp": self.timestamp.isoformat(),
        }


class StrategyRollbacker:
    """Monitors active strategies and triggers instant rollbacks upon regression (Spec 54, 118)."""

    def __init__(
        self,
        min_verification_floor: float = 0.70,
        max_failure_ceiling: float = 0.25,
    ) -> None:
        self.min_verification_floor = min_verification_floor
        self.max_failure_ceiling = max_failure_ceiling
        self._records: list[RollbackRecord] = []

    def check_regression(self, strategy: Strategy) -> tuple[bool, str]:
        """Detect if an active or experimental strategy has regressed."""
        if strategy.sample_size < 5:
            return False, "Insufficient samples to declare regression."

        if strategy.verification_rate < self.min_verification_floor:
            return True, f"Verification rate ({strategy.verification_rate:.1%}) dropped below floor ({self.min_verification_floor:.1%})."

        if strategy.failure_rate > self.max_failure_ceiling:
            return True, f"Failure rate ({strategy.failure_rate:.1%}) exceeded ceiling ({self.max_failure_ceiling:.1%})."

        return False, "Strategy within healthy operating parameters."

    def rollback(
        self,
        strategy: Strategy,
        rolled_back_by: str = "automated_regression_guard",
        reason: str | None = None,
    ) -> tuple[bool, str, RollbackRecord]:
        """Demote strategy to ROLLED_BACK with audit record."""
        trigger_reason = reason or "Verification drop or failure spike detected."

        rec = RollbackRecord(
            rollback_id=f"rb_{uuid.uuid4().hex[:10]}",
            strategy_id=strategy.strategy_id,
            prior_status=strategy.status,
            trigger_reason=trigger_reason,
            rolled_back_by=rolled_back_by,
        )

        strategy.status = StrategyStatus.ROLLED_BACK
        self._records.append(rec)
        logger.warning(
            "ROLLED BACK strategy '%s' from '%s'. Reason: %s",
            strategy.strategy_id,
            rec.prior_status.value,
            trigger_reason,
        )
        return True, "Strategy rolled back successfully.", rec

    def get_records(self) -> list[RollbackRecord]:
        return list(self._records)
