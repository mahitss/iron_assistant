"""Risk Evaluation Engine for Kairo Attention (Task 70).

Risk strongly influences attention:
- probability of failure / harm
- impact severity
- blast radius
- irreversibility
- security sensitivity
- uncertainty interaction (high uncertainty + high potential impact = high investigation priority,
  but uncertainty is NOT proof of danger).
"""


class RiskEvaluator:
    """Computes explainable risk scores for attention candidates."""

    WEIGHT_PROBABILITY = 0.25
    WEIGHT_IMPACT = 0.35
    WEIGHT_BLAST_RADIUS = 0.20
    WEIGHT_SECURITY_SENSITIVITY = 0.20

    @classmethod
    def evaluate(
        cls,
        *,
        probability: float = 0.3,
        potential_impact: float = 0.5,
        blast_radius: float = 0.2,
        security_sensitivity: float = 0.0,
        uncertainty: float = 0.2,
        is_irreversible: bool = False,
        explicit_risk: float | None = None,
    ) -> tuple[float, str, dict[str, float]]:
        """Evaluate risk profile.

        Returns:
            (risk_score [0.0 - 1.0], risk_tier, breakdown)
        """
        prob = max(0.0, min(1.0, probability))
        impact = max(0.0, min(1.0, potential_impact))
        blast = max(0.0, min(1.0, blast_radius))
        sec = max(0.0, min(1.0, security_sensitivity))
        unc = max(0.0, min(1.0, uncertainty))

        # Base risk: probability * impact modulated by blast radius and security
        base_risk = (
            cls.WEIGHT_PROBABILITY * prob
            + cls.WEIGHT_IMPACT * impact
            + cls.WEIGHT_BLAST_RADIUS * blast
            + cls.WEIGHT_SECURITY_SENSITIVITY * sec
        )

        # Irreversibility multiplier
        if is_irreversible:
            base_risk = min(1.0, base_risk * 1.25)

        # Uncertainty handling:
        # High uncertainty increases investigation priority (information gain),
        # but NEVER converts into artificial confirmed risk/danger.
        investigation_factor = round(unc * 0.15, 3)

        if explicit_risk is not None:
            clamped_explicit = max(0.0, min(1.0, explicit_risk))
            final_risk = max(base_risk, clamped_explicit)
        else:
            final_risk = base_risk

        final_risk = round(max(0.0, min(1.0, final_risk)), 3)

        if final_risk >= 0.85:
            tier = "CRITICAL"
        elif final_risk >= 0.70:
            tier = "HIGH"
        elif final_risk >= 0.40:
            tier = "MEDIUM"
        else:
            tier = "LOW"

        breakdown = {
            "probability": round(prob, 3),
            "potential_impact": round(impact, 3),
            "blast_radius": round(blast, 3),
            "security_sensitivity": round(sec, 3),
            "uncertainty_investigation_factor": investigation_factor,
            "irreversible_multiplier": 1.25 if is_irreversible else 1.0,
            "computed_risk": final_risk,
        }

        return final_risk, tier, breakdown
