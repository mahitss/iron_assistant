"""Epistemic uncertainty modeling and calibration tracking for simulations."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.simulation.schemas import AssumptionImpact, ScenarioAssumption


class UncertaintyProfile(BaseModel):
    """Structured uncertainty representation for a simulation."""

    overall_confidence: float = 1.0  # 0.0 to 1.0
    epistemic_uncertainty_level: str = "LOW"  # LOW, MEDIUM, HIGH, VERY_HIGH
    missing_data_fields: list[str] = Field(default_factory=list)
    critical_assumptions_count: int = 0
    topology_completeness: float = 1.0
    has_unknowns: bool = False
    disclaimer: str = (
        "Simulation outputs represent hypothetical projections, not observed facts. "
        "Confidence is constrained by assumption validity and topology completeness."
    )


class UncertaintyQuantifier:
    """Calculates overall simulation confidence based on assumptions, topology, and missing data."""

    def quantify_uncertainty(
        self,
        assumptions: list[ScenarioAssumption],
        topology_completeness: float = 1.0,
        missing_data: list[str] | None = None,
    ) -> UncertaintyProfile:
        """Derives calibrated confidence score and uncertainty profile."""
        missing = missing_data or []
        base_conf = 0.95

        # Factor 1: Critical assumptions
        critical_count = sum(1 for a in assumptions if a.impact == AssumptionImpact.CRITICAL)
        high_count = sum(1 for a in assumptions if a.impact == AssumptionImpact.HIGH)
        unknown_assumptions = sum(1 for a in assumptions if a.assumption_type.value == "UNKNOWN")

        # Penalties
        conf_penalty = (critical_count * 0.15) + (high_count * 0.08) + (unknown_assumptions * 0.12)
        conf_penalty += (1.0 - topology_completeness) * 0.25
        conf_penalty += min(len(missing) * 0.05, 0.20)

        final_conf = max(0.10, round(base_conf - conf_penalty, 3))

        if final_conf >= 0.85:
            level = "LOW"
        elif final_conf >= 0.65:
            level = "MEDIUM"
        elif final_conf >= 0.40:
            level = "HIGH"
        else:
            level = "VERY_HIGH"

        return UncertaintyProfile(
            overall_confidence=final_conf,
            epistemic_uncertainty_level=level,
            missing_data_fields=missing,
            critical_assumptions_count=critical_count,
            topology_completeness=topology_completeness,
            has_unknowns=unknown_assumptions > 0 or len(missing) > 0,
        )
