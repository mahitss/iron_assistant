"""Autonomous Trade-Off and Degraded Mode Engine: Pareto scoring and adaptive compression (Task 77)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.orchestration.economy_schemas import (
    DegradationTier,
    TradeOffEvaluation,
)

logger = logging.getLogger(__name__)


class ResourceTradeOffEngine:
    """Evaluates multi-objective trade-offs across Quality, Latency, Cost, Risk, and Resource Usage."""

    def __init__(self) -> None:
        # Default weights for composite scoring
        self.default_weights = {
            "quality": 0.40,
            "latency": 0.15,
            "cost": 0.15,
            "risk": 0.15,
            "resource_usage": 0.15,
        }

    def evaluate_tradeoff(
        self,
        candidate_id: str,
        quality_score: float = 1.0,
        latency_ms: float = 100.0,
        financial_cost: float = 0.01,
        risk_score: float = 0.1,
        resource_usage_score: float = 0.5,
        degradation_tier: DegradationTier = DegradationTier.FULL_FIDELITY,
        custom_weights: dict[str, float] | None = None,
    ) -> TradeOffEvaluation:
        """Compute normalized composite score across 5 objectives."""
        weights = custom_weights or self.default_weights

        # Normalize metrics to [0, 1] where 1 is optimal
        norm_quality = min(1.0, max(0.0, quality_score))
        norm_latency = max(0.0, 1.0 - (latency_ms / 2000.0))  # 2000ms as baseline max
        norm_cost = max(0.0, 1.0 - (financial_cost / 0.50))     # $0.50 as baseline max
        norm_risk = max(0.0, 1.0 - min(1.0, risk_score))
        norm_resource = max(0.0, 1.0 - min(1.0, resource_usage_score))

        composite = (
            weights.get("quality", 0.4) * norm_quality
            + weights.get("latency", 0.15) * norm_latency
            + weights.get("cost", 0.15) * norm_cost
            + weights.get("risk", 0.15) * norm_risk
            + weights.get("resource_usage", 0.15) * norm_resource
        )
        composite = min(1.0, max(0.0, composite))

        rationale = (
            f"Quality: {norm_quality:.2f}, Latency: {latency_ms:.0f}ms, Cost: ${financial_cost:.4f}, "
            f"Risk: {risk_score:.2f}, Resource: {resource_usage_score:.2f} -> Composite: {composite:.3f}"
        )

        return TradeOffEvaluation(
            evaluation_id=f"ev_{uuid.uuid4().hex[:8]}",
            candidate_id=candidate_id,
            quality_score=norm_quality,
            latency_ms=latency_ms,
            financial_cost=financial_cost,
            risk_score=risk_score,
            resource_usage_score=resource_usage_score,
            composite_score=round(composite, 4),
            degradation_tier=degradation_tier,
            rationale=rationale,
        )

    def apply_degradation_strategy(
        self,
        prompt_text: str,
        tier: DegradationTier,
    ) -> tuple[str, str, float]:
        """Apply concrete prompt compression / token reduction based on degradation tier.

        Returns: (compressed_prompt, recommended_model, token_saving_fraction).
        """
        if tier == DegradationTier.FULL_FIDELITY:
            return prompt_text, "openrouter/reasoning", 0.0

        if tier == DegradationTier.MODERATE_COMPRESSION:
            # Prune extraneous whitespace / trim length by 30%
            lines = [line.strip() for line in prompt_text.splitlines() if line.strip()]
            compressed = "\n".join(lines[: max(1, int(len(lines) * 0.7))])
            return compressed, "openrouter/fast", 0.30

        if tier == DegradationTier.AGGRESSIVE_THROTTLE:
            # Aggressive compression: take only the first 40% of content
            lines = [line.strip() for line in prompt_text.splitlines() if line.strip()]
            compressed = "\n".join(lines[: max(1, int(len(lines) * 0.4))])
            return compressed, "openrouter/free", 0.60

        # EMERGENCY_MINIMAL
        summary = prompt_text[:100] + ("..." if len(prompt_text) > 100 else "")
        return f"[MINIMAL] {summary}", "system/deterministic_rule", 0.90


default_tradeoff_engine = ResourceTradeOffEngine()
