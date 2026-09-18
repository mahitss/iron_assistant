"""Value-of-Information (VoI) and Marginal Gain Estimation Engine for Task 114.
Balances expected uncertainty reduction and decision improvement against compute, latency, risk, and saturation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.observation.domain import (
    DecisionSensitivity,
    InformationGap,
    InformationValueEstimate,
    InformationValueTier,
    ObservationCandidate,
    ObservationCost,
    ObservationOutcome,
    ObservationRisk,
)


class ValueOfInformationEngine:
    """Computes expected VoI and marginal value to prevent wasteful or redundant observations."""

    @classmethod
    def estimate_value(
        cls,
        candidate: ObservationCandidate,
        gap: InformationGap,
        sensitivity: DecisionSensitivity,
        existing_outcomes: Optional[List[ObservationOutcome]] = None,
    ) -> InformationValueEstimate:
        existing_outcomes = existing_outcomes or []

        # 1. Base expected decision improvement
        # High sensitivity directly scales decision improvement
        sens_multiplier = sensitivity.sensitivity_score if sensitivity.is_decision_sensitive else 0.15
        expected_decision_improvement = round(min(1.0, max(0.0, sens_multiplier * 0.95)), 2)

        # 2. Expected uncertainty reduction based on method & source trust
        method_power = {
            "CONTROLLED": 0.90,
            "ACTIVE": 0.80,
            "USER": 0.85,
            "PASSIVE": 0.65,
            "WAIT": 0.60,
        }.get(candidate.method.value, 0.50)
        expected_uncertainty_reduction = round(method_power * (0.8 if gap.severity == "CRITICAL" else 0.6), 2)

        # 3. Cost and Risk Penalties
        cost_penalty = cls._calculate_cost_penalty(candidate.cost)
        risk_penalty = cls._calculate_risk_penalty(candidate.risk)

        # 4. Marginal Value and Saturation Detection (Section 43)
        # Check if identical or equivalent source/target already reported
        redundant_count = sum(
            1 for out in existing_outcomes
            if out.source == candidate.target_source or out.data_payload.get("metric") == candidate.query_payload.get("metric")
        )
        is_redundant = redundant_count >= 2
        saturation_discount = max(0.1, 1.0 - (redundant_count * 0.45))

        marginal_value = round(
            max(0.0, (expected_decision_improvement * 0.6 + expected_uncertainty_reduction * 0.4) * saturation_discount),
            2,
        )
        if is_redundant:
            marginal_value = min(marginal_value, 0.15)

        # 5. Net Value Score: value - (cost + risk)
        net_value = round(marginal_value - (cost_penalty + risk_penalty), 2)

        # Classify Tier
        if is_redundant or net_value < 0.10:
            tier = InformationValueTier.VERY_LOW
        elif net_value < 0.30:
            tier = InformationValueTier.LOW
        elif net_value < 0.55:
            tier = InformationValueTier.MODERATE
        elif net_value < 0.75:
            tier = InformationValueTier.HIGH
        else:
            tier = InformationValueTier.VERY_HIGH

        justification = (
            f"Decision sensitivity: {sensitivity.sensitivity_score:.2f}, "
            f"Method: {candidate.method.value}, "
            f"Cost penalty: {cost_penalty:.2f}, "
            f"Risk penalty: {risk_penalty:.2f}, "
            f"Redundancy: {redundant_count} prior items."
        )

        return InformationValueEstimate(
            candidate_id=candidate.candidate_id,
            tier=tier,
            expected_decision_improvement=expected_decision_improvement,
            expected_uncertainty_reduction=expected_uncertainty_reduction,
            net_value_score=net_value,
            marginal_value=marginal_value,
            is_redundant=is_redundant,
            justification=justification,
        )

    @classmethod
    def _calculate_cost_penalty(cls, cost: ObservationCost) -> float:
        penalty = 0.0
        penalty += min(0.20, cost.compute_units * 0.05)
        penalty += min(0.20, (cost.network_latency_ms / 1000.0) * 0.05)
        penalty += min(0.25, cost.interruption_penalty * 0.15)
        if cost.privacy_impact in {"SENSITIVE", "RESTRICTED"}:
            penalty += 0.20
        return round(penalty, 2)

    @classmethod
    def _calculate_risk_penalty(cls, risk: ObservationRisk) -> float:
        penalty = 0.0
        if risk.security_risk_level in {"HIGH", "CRITICAL"}:
            penalty += 0.35
        elif risk.security_risk_level == "MEDIUM":
            penalty += 0.15
        if risk.state_mutation_risk:
            penalty += 0.50  # Heavy penalty for state mutation risk
        if risk.requires_approval:
            penalty += 0.15
        return round(penalty, 2)
