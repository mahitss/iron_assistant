"""Alternative plan generation, trade-off analysis, and deterministic scoring for Kairo Cognitive Planning (Task 41)."""

from typing import Any
import uuid
from pydantic import BaseModel, ConfigDict, Field

from app.cognition.plans import Plan, PlanRiskLevel


class PlanAlternative(BaseModel):
    """An alternative strategy evaluated for accomplishing a goal."""

    model_config = ConfigDict(extra="ignore")

    alternative_id: str = Field(default_factory=lambda: f"alt_{uuid.uuid4().hex[:10]}")
    name: str = Field(..., description="E.g. 'Fast Path', 'Low-Risk Hardened Path'")
    strategy: str = Field(..., description="High-level description of tactical approach")
    estimated_steps: int
    risk: PlanRiskLevel
    estimated_latency_seconds: float
    estimated_cost_score: float = Field(default=0.5, ge=0.0, le=1.0)
    success_probability: float = Field(default=0.85, ge=0.0, le=1.0)
    tradeoffs: dict[str, Any] = Field(default_factory=dict)
    composite_score: float = Field(default=0.0)
    selected: bool = Field(default=False)


class AlternativeEvaluator:
    """Evaluates and scores candidate alternatives deterministically."""

    @staticmethod
    def score_alternative(alt: PlanAlternative) -> float:
        """Compute explainable composite score:
        Score = 0.40 * SuccessProbability - 0.25 * RiskPenalty - 0.20 * LatencyPenalty - 0.15 * CostScore
        Higher score indicates preferred alternative.
        """
        risk_penalties = {
            PlanRiskLevel.LOW: 0.1,
            PlanRiskLevel.MEDIUM: 0.3,
            PlanRiskLevel.HIGH: 0.7,
            PlanRiskLevel.CRITICAL: 1.0,
        }
        r_penalty = risk_penalties.get(alt.risk, 0.5)
        # Normalized latency penalty (bounded 0 to 1, with 300s as reference ceiling)
        l_penalty = min(1.0, alt.estimated_latency_seconds / 300.0)

        score = (
            0.40 * alt.success_probability
            - 0.25 * r_penalty
            - 0.20 * l_penalty
            - 0.15 * alt.estimated_cost_score
        )
        return round(max(0.0, min(1.0, score + 0.5)), 3)

    @classmethod
    def generate_alternatives(cls, goal_description: str, base_plan: Plan) -> list[PlanAlternative]:
        """Generate candidate alternatives for a goal (e.g. Fast Path vs Low-Risk Hardened Path)."""
        alt_fast = PlanAlternative(
            name="Fast Path",
            strategy="Streamlined execution with minimal intermediate checks for low-risk environments.",
            estimated_steps=max(1, len(base_plan.steps) - 1),
            risk=PlanRiskLevel.MEDIUM,
            estimated_latency_seconds=30.0,
            estimated_cost_score=0.2,
            success_probability=0.82,
            tradeoffs={"speed": "high", "verification_depth": "standard"},
        )
        alt_fast.composite_score = cls.score_alternative(alt_fast)

        alt_safe = PlanAlternative(
            name="Low-Risk Hardened Path",
            strategy="Full defensive pipeline with pre/post-condition checks, state snapshots, and independent verifications.",
            estimated_steps=len(base_plan.steps) + 1,
            risk=PlanRiskLevel.LOW,
            estimated_latency_seconds=75.0,
            estimated_cost_score=0.4,
            success_probability=0.96,
            tradeoffs={"speed": "moderate", "verification_depth": "deep", "safety": "maximum"},
        )
        alt_safe.composite_score = cls.score_alternative(alt_safe)

        # Mark the higher scoring (safer) candidate as selected by default
        if alt_safe.composite_score >= alt_fast.composite_score:
            alt_safe.selected = True
        else:
            alt_fast.selected = True

        return [alt_safe, alt_fast]
