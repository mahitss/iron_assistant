"""Recovery learning and safe remediation recommendations for Kairo Learning Engine (Task 43)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("kairo.learning.recovery")


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class RecoveryStrategyScore:
    """Empirical effectiveness record of a recovery action for a failure signature."""

    failure_signature: str
    recovery_action: str
    attempts: int = 0
    successes: int = 0
    is_safe_for_auto_retry: bool = False
    last_tested: datetime = field(default_factory=utc_now)

    @property
    def success_rate(self) -> float:
        return (self.successes / self.attempts) if self.attempts > 0 else 0.0

    def record_attempt(self, succeeded: bool) -> None:
        self.attempts += 1
        if succeeded:
            self.successes += 1
        self.last_tested = utc_now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "failure_signature": self.failure_signature,
            "recovery_action": self.recovery_action,
            "attempts": self.attempts,
            "successes": self.successes,
            "success_rate": round(self.success_rate, 3),
            "is_safe_for_auto_retry": self.is_safe_for_auto_retry,
            "last_tested": self.last_tested.isoformat(),
        }


class RecoveryLearner:
    """Learns which recovery strategies resolve failures safely (Spec 80, 81)."""

    def __init__(self) -> None:
        # (failure_signature, recovery_action) -> RecoveryStrategyScore
        self._scores: dict[tuple[str, str], RecoveryStrategyScore] = {}

    def record_recovery(
        self,
        failure_signature: str,
        recovery_action: str,
        succeeded: bool,
        is_safe_for_auto_retry: bool = False,
    ) -> RecoveryStrategyScore:
        """Record outcome of applying a recovery action to a failure."""
        key = (failure_signature.strip().lower(), recovery_action.strip())
        if key not in self._scores:
            self._scores[key] = RecoveryStrategyScore(
                failure_signature=failure_signature,
                recovery_action=recovery_action,
                is_safe_for_auto_retry=is_safe_for_auto_retry,
            )

        score = self._scores[key]
        score.record_attempt(succeeded)
        return score

    def recommend_recovery(self, failure_signature: str) -> RecoveryStrategyScore | None:
        """Recommend the highest success rate recovery strategy for a failure."""
        sig = failure_signature.strip().lower()
        candidates = [score for (s, _), score in self._scores.items() if s == sig]
        if not candidates:
            return None

        # Sort by success rate descending, then attempts descending
        candidates.sort(key=lambda c: (c.success_rate, c.attempts), reverse=True)
        return candidates[0]
