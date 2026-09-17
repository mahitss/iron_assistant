"""Meta-Evaluator Engine for Kairo Strategy Engine (Task 106).

Evaluates the health, precision, poisoning resistance, and relevance of the Strategy Engine itself.
Emits findings through Task 104 if engine metrics degrade rather than silently modifying itself.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.strategy.domain import Strategy, utc_now

logger = logging.getLogger("kairo.strategy.meta_evaluator")


class StrategyEngineHealthMetrics(BaseModel):
    total_recommendations: int = 0
    useful_retrieval_count: int = 0
    irrelevant_retrieval_count: int = 0
    harmful_recommendation_count: int = 0
    stale_usage_count: int = 0
    conflicts_detected_count: int = 0
    applicability_evaluations_count: int = 0
    false_applicability_count: int = 0
    revalidation_queue_length: int = 0
    poisoning_attempts_blocked: int = 0
    health_status: str = "NOMINAL"       # NOMINAL, WARNING, DEGRADED
    emitted_findings: List[Dict[str, Any]] = Field(default_factory=list)


class MetaStrategyEvaluator:
    """Monitors the operational integrity of the Strategy Engine."""

    def __init__(self, max_stale_usage_rate: float = 0.05, max_harmful_rate: float = 0.01) -> None:
        self.max_stale_usage_rate = max_stale_usage_rate
        self.max_harmful_rate = max_harmful_rate
        self.metrics = StrategyEngineHealthMetrics()

    def record_recommendation_outcome(
        self,
        was_useful: bool,
        was_harmful: bool = False,
        was_stale: bool = False,
    ) -> None:
        """Record operational telemetry on a strategy recommendation."""
        self.metrics.total_recommendations += 1
        if was_useful:
            self.metrics.useful_retrieval_count += 1
        else:
            self.metrics.irrelevant_retrieval_count += 1

        if was_harmful:
            self.metrics.harmful_recommendation_count += 1

        if was_stale:
            self.metrics.stale_usage_count += 1

    def record_poisoning_blocked(self) -> None:
        self.metrics.poisoning_attempts_blocked += 1

    def evaluate_engine_health(self, active_strategies: List[Strategy]) -> StrategyEngineHealthMetrics:
        """Analyze engine metrics and determine if an evaluation finding must be dispatched."""
        total_rec = self.metrics.total_recommendations
        stale_count = sum(1 for s in active_strategies if s.is_stale)
        self.metrics.revalidation_queue_length = stale_count

        findings: List[Dict[str, Any]] = []
        is_degraded = False

        if total_rec >= 20:
            stale_rate = self.metrics.stale_usage_count / total_rec
            harmful_rate = self.metrics.harmful_recommendation_count / total_rec

            if stale_rate > self.max_stale_usage_rate:
                is_degraded = True
                findings.append({
                    "finding_type": "STRATEGY_ENGINE_STALE_USAGE_REGRESSION",
                    "severity": "HIGH",
                    "description": f"Stale strategy retrieval rate ({stale_rate:.2%}) exceeds tolerance ({self.max_stale_usage_rate:.2%}).",
                    "target_subsystem": "strategy_engine",
                })

            if harmful_rate > self.max_harmful_rate:
                is_degraded = True
                findings.append({
                    "finding_type": "STRATEGY_ENGINE_HARMFUL_RECOMMENDATION_REGRESSION",
                    "severity": "CRITICAL",
                    "description": f"Harmful strategy recommendation rate ({harmful_rate:.2%}) exceeds safety tolerance ({self.max_harmful_rate:.2%}).",
                    "target_subsystem": "strategy_engine",
                })

        if is_degraded:
            self.metrics.health_status = "DEGRADED"
            logger.error(f"MetaStrategyEvaluator detected engine degradation: {findings}")
        elif stale_count > 5:
            self.metrics.health_status = "WARNING"
        else:
            self.metrics.health_status = "NOMINAL"

        self.metrics.emitted_findings = findings
        return self.metrics
