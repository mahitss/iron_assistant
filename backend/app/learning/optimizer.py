"""Multi-factor strategy optimizer and ranking engine for Kairo Learning (Task 43)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.learning.strategies import Strategy, StrategyStatus

logger = logging.getLogger("kairo.learning.optimizer")


@dataclass
class RankedStrategy:
    """A strategy evaluated and ranked with deterministic component factors."""

    strategy: Strategy
    rank_score: float  # Normalized 0.0 to 1.0
    factors: dict[str, float]
    explanation: str
    small_sample_warning: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy.to_dict(),
            "rank_score": round(self.rank_score, 3),
            "factors": {k: round(v, 3) for k, v in self.factors.items()},
            "explanation": self.explanation,
            "small_sample_warning": self.small_sample_warning,
        }


class StrategyOptimizer:
    """Ranks and optimizes execution strategies deterministically (Specs 19, 64, 65)."""

    def rank_strategies(
        self,
        strategies: list[Strategy],
        domain: str | None = None,
        prefer_minimal: bool = True,
    ) -> list[RankedStrategy]:
        """Rank candidates using deterministic components without opaque magic numbers."""
        ranked: list[RankedStrategy] = []

        for strat in strategies:
            if domain and strat.domain.strip().lower() != domain.strip().lower():
                continue

            # Compute Component Factors
            # 1. Verification rate (Spec 62: Never sacrifice verified correctness for speed)
            verif_score = strat.verification_rate

            # 2. Success rate
            success_score = strat.success_rate

            # 3. Confidence weight
            conf_weight = 1.0 if strat.confidence == "HIGH" else (0.7 if strat.confidence == "MEDIUM" else 0.4)

            # 4. Latency score (normalized: 1.0 = under 500ms, decays over 10s)
            latency_score = max(0.0, min(1.0, 1.0 - (strat.latency_ms / 10000.0)))

            # 5. Cost score (normalized: 1.0 = under $0.01, decays over $1.00)
            cost_score = max(0.0, min(1.0, 1.0 - (strat.cost / 1.0)))

            # 6. Sample size damping (Spec 50, 142: discount tiny samples)
            sample_factor = min(1.0, strat.sample_size / 20.0)

            # Weighted deterministic sum
            raw_score = (
                (verif_score * 0.35)
                + (success_score * 0.25)
                + (conf_weight * 0.15)
                + (sample_factor * 0.10)
                + (latency_score * 0.10)
                + (cost_score * 0.05)
            )

            # Small sample warning (Spec 142)
            warning = None
            if strat.sample_size < 5:
                warning = f"Evidence is limited to {strat.sample_size} execution(s)."

            explanation = (
                f"Ranked {raw_score:.2f} based on {verif_score:.0%} verification rate, "
                f"{success_score:.0%} success rate over {strat.sample_size} runs."
            )

            ranked.append(
                RankedStrategy(
                    strategy=strat,
                    rank_score=round(raw_score, 3),
                    factors={
                        "verification_rate": verif_score,
                        "success_rate": success_score,
                        "confidence": conf_weight,
                        "sample_factor": sample_factor,
                        "latency_score": latency_score,
                        "cost_score": cost_score,
                    },
                    explanation=explanation,
                    small_sample_warning=warning,
                )
            )

        # Sort descending by rank_score
        ranked.sort(key=lambda r: r.rank_score, reverse=True)
        return ranked

    def select_best_strategy(
        self,
        strategies: list[Strategy],
        domain: str | None = None,
    ) -> RankedStrategy | None:
        """Select top ranked active strategy for a given domain."""
        active_candidates = [s for s in strategies if s.status in [StrategyStatus.ACTIVE, StrategyStatus.EXPERIMENTAL]]
        ranked = self.rank_strategies(active_candidates, domain=domain)
        return ranked[0] if ranked else None
