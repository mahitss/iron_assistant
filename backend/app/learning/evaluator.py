"""Strategy evaluation and benchmark comparison for Kairo Learning Engine (Task 43)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.learning.strategies import Strategy

logger = logging.getLogger("kairo.learning.evaluator")


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class StrategyEvaluationReport:
    """Outcome of evaluating a candidate strategy against baselines and quality bars (Spec 51, 185)."""

    strategy_id: str
    is_satisfactory: bool
    verification_rate: float
    success_rate: float
    sample_size: int
    cost_delta: float
    latency_delta_ms: float
    reasons: list[str] = field(default_factory=list)
    evaluated_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "is_satisfactory": self.is_satisfactory,
            "verification_rate": round(self.verification_rate, 3),
            "success_rate": round(self.success_rate, 3),
            "sample_size": self.sample_size,
            "cost_delta": round(self.cost_delta, 4),
            "latency_delta_ms": round(self.latency_delta_ms, 2),
            "reasons": self.reasons,
            "evaluated_at": self.evaluated_at.isoformat(),
        }


class StrategyEvaluator:
    """Evaluates candidate strategies against benchmark baselines (Spec 48, 181-185)."""

    def evaluate(
        self,
        candidate: Strategy,
        baseline: Strategy | None = None,
        min_verif_threshold: float = 0.80,
    ) -> StrategyEvaluationReport:
        reasons: list[str] = []
        is_satisfactory = True

        # Check sample size
        if candidate.sample_size < 5:
            is_satisfactory = False
            reasons.append(f"Insufficient sample size ({candidate.sample_size} < 5)")

        # Check verification rate
        if candidate.verification_rate < min_verif_threshold:
            is_satisfactory = False
            reasons.append(
                f"Verification rate ({candidate.verification_rate:.1%}) below threshold ({min_verif_threshold:.1%})"
            )

        cost_delta = 0.0
        latency_delta = 0.0

        if baseline:
            cost_delta = candidate.cost - baseline.cost
            latency_delta = candidate.latency_ms - baseline.latency_ms

            # Check if candidate regressed significantly on verification
            if candidate.verification_rate < (baseline.verification_rate - 0.05):
                is_satisfactory = False
                reasons.append(
                    f"Candidate verification rate ({candidate.verification_rate:.1%}) regressed against baseline ({baseline.verification_rate:.1%})"
                )

        if is_satisfactory:
            reasons.append("Strategy satisfies evaluation benchmarks and quality thresholds.")

        return StrategyEvaluationReport(
            strategy_id=candidate.strategy_id,
            is_satisfactory=is_satisfactory,
            verification_rate=candidate.verification_rate,
            success_rate=candidate.success_rate,
            sample_size=candidate.sample_size,
            cost_delta=cost_delta,
            latency_delta_ms=latency_delta,
            reasons=reasons,
        )
