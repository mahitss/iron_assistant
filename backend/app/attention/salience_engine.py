"""Structured 15-Dimensional Salience Computation Engine (Task 109, Spec 5).

Does NOT reduce all dimensions into one lossy opaque number.
Preserves component values while generating an explainable composite routing score.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import UTC, datetime

from app.attention.domain import AttentionScore, gen_attn_id


def utc_now() -> datetime:
    return datetime.now(UTC)


class SalienceEngine:
    """Computes fine-grained multi-dimensional salience for attention candidates."""

    @staticmethod
    def calculate_deadline_pressure(deadline: Optional[datetime], current_time: Optional[datetime] = None) -> float:
        """Calculates non-linear deadline pressure in [0.0, 1.0]."""
        if not deadline:
            return 0.0
        now = current_time or utc_now()
        remaining_sec = (deadline - now).total_seconds()
        if remaining_sec <= 0:
            return 1.0
        elif remaining_sec < 300:  # < 5 minutes
            return 0.95
        elif remaining_sec < 1800:  # < 30 minutes
            return 0.85
        elif remaining_sec < 3600:  # < 1 hour
            return 0.70
        elif remaining_sec < 86400:  # < 1 day
            return max(0.2, round(1.0 - (remaining_sec / 86400.0), 3))
        return 0.1

    @classmethod
    def evaluate(
        cls,
        *,
        importance: float = 0.5,
        urgency: float = 0.5,
        risk: float = 0.3,
        deadline: Optional[datetime] = None,
        user_relevance: float = 0.5,
        mission_relevance: float = 0.5,
        novelty: float = 0.0,
        change_magnitude: float = 0.0,
        dependency_impact: float = 0.0,
        uncertainty: float = 0.2,
        irreversibility: float = 0.0,
        external_impact: float = 0.0,
        resource_cost: float = 0.2,
        interruption_cost: float = 0.2,
        confidence: float = 0.8,
        is_adversarial_dampened: bool = False,
    ) -> AttentionScore:
        """Computes structured 15-dimensional score and explainable attribution."""
        deadline_pressure = cls.calculate_deadline_pressure(deadline)

        # Dampen unverified untrusted urgency if flagged by firewall
        eff_urgency = urgency * 0.3 if is_adversarial_dampened else urgency
        eff_importance = importance * 0.4 if is_adversarial_dampened else importance

        factors: List[str] = []
        if eff_urgency >= 0.7:
            factors.append(f"High urgency ({eff_urgency:.2f})")
        if eff_importance >= 0.7:
            factors.append(f"High importance ({eff_importance:.2f})")
        if risk >= 0.6:
            factors.append(f"Elevated risk ({risk:.2f})")
        if deadline_pressure >= 0.7:
            factors.append(f"Imminent deadline pressure ({deadline_pressure:.2f})")
        if mission_relevance >= 0.7:
            factors.append(f"Strong mission alignment ({mission_relevance:.2f})")
        if user_relevance >= 0.7:
            factors.append(f"Direct user relevance ({user_relevance:.2f})")
        if dependency_impact >= 0.6:
            factors.append(f"Critical dependency blocking ({dependency_impact:.2f})")
        if is_adversarial_dampened:
            factors.append("Untrusted external urgency dampened by firewall")

        # Explainable composite salience for ordering in priority queues:
        # Weighted blend giving high weight to risk, urgency, importance, and mission relevance,
        # with penalization for excessive resource cost and interruption switching cost.
        raw_composite = (
            (eff_importance * 0.20)
            + (eff_urgency * 0.18)
            + (risk * 0.16)
            + (deadline_pressure * 0.12)
            + (mission_relevance * 0.12)
            + (user_relevance * 0.10)
            + (dependency_impact * 0.08)
            + (novelty * 0.04)
        )
        # Cost moderation: reduce slightly if interruption/resource costs are high
        cost_moderator = 1.0 - (0.15 * interruption_cost + 0.10 * resource_cost)
        composite = max(0.0, min(1.0, round(raw_composite * cost_moderator, 4)))

        explanation = (
            "; ".join(factors)
            if factors
            else f"Standard attention level (composite={composite:.2f}, conf={confidence:.2f})"
        )

        return AttentionScore(
            importance=round(eff_importance, 4),
            urgency=round(eff_urgency, 4),
            risk=round(risk, 4),
            deadline_pressure=round(deadline_pressure, 4),
            user_relevance=round(user_relevance, 4),
            mission_relevance=round(mission_relevance, 4),
            novelty=round(novelty, 4),
            change_magnitude=round(change_magnitude, 4),
            dependency_impact=round(dependency_impact, 4),
            uncertainty=round(uncertainty, 4),
            irreversibility=round(irreversibility, 4),
            external_impact=round(external_impact, 4),
            resource_cost=round(resource_cost, 4),
            interruption_cost=round(interruption_cost, 4),
            confidence=round(confidence, 4),
            composite_salience=composite,
            contributing_factors=factors,
            explanation=explanation,
        )
