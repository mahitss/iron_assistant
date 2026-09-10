"""Structured deliberation engine for Kairo Executive Decision Engine (Task 57).

Evaluates objective fit, constraints, evidence, causal effects, simulations,
risk, tradeoffs, and uncertainty without storing raw chain-of-thought traces.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.decision.schemas import (
    CandidateOption,
    DecisionRequest,
    EvidenceSet,
    OptionEvaluation,
    RiskAssessment,
    Tradeoff,
    UncertaintyAssessment,
)


class StructuredDeliberationReport(BaseModel):
    """Structured rationale containing explicit decision factors (no private CoT)."""
    model_config = ConfigDict(extra="ignore")

    decision_id: str
    primary_factors: list[str] = Field(default_factory=list)
    key_assumptions: list[str] = Field(default_factory=list)
    causal_basis_summary: str = "No explicit causal intervention identified."
    simulation_freshness_summary: str = "No simulations associated with this decision."
    adversarial_challenge: str = ""
    clarification_required: bool = False
    clarification_prompt: str | None = None
    information_gathering_recommended: bool = False


class DeliberationEngine:
    """Orchestrates structured deliberation across multi-objective evidence."""

    def deliberate(
        self,
        request: DecisionRequest,
        options: list[CandidateOption],
        evaluations: list[OptionEvaluation],
        tradeoffs: list[Tradeoff],
        risks: list[RiskAssessment],
        evidence_set: EvidenceSet,
        uncertainty: UncertaintyAssessment,
        causal_context: dict[str, Any] | None = None,
        simulation_context: dict[str, Any] | None = None,
    ) -> StructuredDeliberationReport:
        primary_factors: list[str] = []
        key_assumptions: list[str] = []

        # 1. Evaluate objective fit factors
        top_evaluation = evaluations[0] if evaluations else None
        if top_evaluation:
            primary_factors.append(
                f"Leading option '{top_evaluation.name}' achieved highest normalized score ({top_evaluation.normalized_score:.2f}) "
                f"with net benefit {top_evaluation.benefit_score:.2f}."
            )

        # 2. Constraints factor
        feasible_count = sum(1 for o in options if o.is_feasible)
        infeasible_count = len(options) - feasible_count
        if infeasible_count > 0:
            primary_factors.append(
                f"{infeasible_count} options rejected due to hard constraint violations or feasibility blocks."
            )

        # 3. Evidence synthesis
        verified_count = sum(1 for e in evidence_set.items if e.verification_status == "VERIFIED")
        primary_factors.append(
            f"Grounding based on {len(evidence_set.items)} evidence items ({verified_count} verified, overall strength: {evidence_set.overall_strength.value})."
        )

        # 4. Causal integration
        causal_summary = "No causal graph analysis required."
        if causal_context:
            confidence = causal_context.get("confidence", "moderate")
            cause = causal_context.get("suspected_cause", "identified bottleneck")
            causal_summary = f"Causal reasoning identifies '{cause}' with {confidence} causal confidence."
            primary_factors.append(f"Causal support: {causal_summary}")

        # 5. Simulation integration
        sim_summary = "No active simulation run."
        if simulation_context:
            is_stale = simulation_context.get("is_stale", False)
            sim_id = simulation_context.get("simulation_id", "sim_current")
            if is_stale:
                sim_summary = f"Simulation '{sim_id}' marked STALE due to environment state drift."
            else:
                sim_summary = f"Simulation '{sim_id}' verifies projected blast radius and stability."
            primary_factors.append(f"Simulation status: {sim_summary}")

        # 6. Key assumptions
        if not request.deadline:
            key_assumptions.append("Assumed standard operational timeframe without immediate deadline pressure.")
        else:
            key_assumptions.append(f"Subject to hard operational deadline: {request.deadline.isoformat()}.")

        if uncertainty.assumptions_count > 0:
            key_assumptions.append("Missing quantitative metrics supplemented with qualitative heuristic baselines.")

        # 7. Adversarial challenge ("What could make this recommendation wrong?")
        adversarial_reasons: list[str] = []
        if uncertainty.stale_signals:
            adversarial_reasons.append("Environmental drift or stale simulation results could invalidate projections.")
        if any(r.exposure_score > 0.6 for r in risks):
            adversarial_reasons.append("High exposure to operational or security risks if mitigations fail.")
        if infeasible_count == len(options) - 1 and len(options) > 1:
            adversarial_reasons.append("Narrow feasibility margin: only a single option survived constraint filtering.")
        adversarial_challenge = (
            " ; ".join(adversarial_reasons)
            if adversarial_reasons
            else "Standard operational risks apply; recommendation is robust under current model boundaries."
        )

        # 8. Clarification and info gathering
        clarification_required = False
        clarification_prompt = None
        info_gathering_recommended = False

        if uncertainty.overall_uncertainty in {"HIGH", "CRITICAL"} or not uncertainty.safe_to_proceed:
            info_gathering_recommended = True

        if not request.objectives and len(options) > 1:
            clarification_required = True
            clarification_prompt = (
                "Multiple viable paths exist but no explicit priority was stated. "
                "Do you prioritize minimal cost, maximum speed, or maximal reliability?"
            )

        return StructuredDeliberationReport(
            decision_id=request.request_id,
            primary_factors=primary_factors,
            key_assumptions=key_assumptions,
            causal_basis_summary=causal_summary,
            simulation_freshness_summary=sim_summary,
            adversarial_challenge=adversarial_challenge,
            clarification_required=clarification_required,
            clarification_prompt=clarification_prompt,
            information_gathering_recommended=info_gathering_recommended,
        )


deliberation_engine = DeliberationEngine()
