"""Core Decision Engine orchestrator for Kairo Executive Decision Engine (Task 57).

Answers: 'What should Kairo recommend we do?' by synthesizing state, goals,
constraints, multi-objective trade-offs, evidence, causal models, simulations,
and epistemic uncertainty into ranked, explainable, traceable recommendations.
"""

from __future__ import annotations

from typing import Any

from app.decision.audit import decision_auditor
from app.decision.constraints import constraint_validator
from app.decision.decisions import decision_lifecycle_manager
from app.decision.deliberation import deliberation_engine
from app.decision.evidence import evidence_engine
from app.decision.explain import explanation_engine
from app.decision.gates import gate_evaluation_engine
from app.decision.objectives import objective_manager
from app.decision.options import option_generator
from app.decision.provenance import provenance_tracker
from app.decision.ranking import ranking_engine
from app.decision.risk import risk_engine
from app.decision.safety import sanitize_decision_input, scrub_decision_secrets
from app.decision.schemas import (
    CandidateOption,
    DecisionRecord,
    DecisionRequest,
    EvidenceItem,
)
from app.decision.scoring import option_scorer
from app.decision.tradeoffs import tradeoff_engine
from app.decision.uncertainty import uncertainty_engine


class DecisionEngine:
    """Production-grade executive decision support engine."""

    def evaluate_decision(
        self,
        request: DecisionRequest,
        candidate_options: list[CandidateOption] | None = None,
        additional_evidence: list[EvidenceItem] | None = None,
        simulations: list[dict[str, Any]] | None = None,
        causal_context: dict[str, Any] | None = None,
        memory_context: dict[str, Any] | None = None,
        is_production: bool = False,
        is_authorized: bool = True,
    ) -> DecisionRecord:
        """Executes full multi-stage deliberation and generates a traceable recommendation."""
        # 1. Defense against prompt injection and secret leakage
        sanitized_question = sanitize_decision_input(request.question)
        clean_question = scrub_decision_secrets(sanitized_question)
        request = request.model_copy(update={"question": clean_question})

        # 2. Objectives validation and normalization
        normalized_objectives = objective_manager.validate_and_normalize(request.objectives)
        request = request.model_copy(update={"objectives": normalized_objectives})

        # 3. Candidate options generation & space completeness
        provided_options = candidate_options or []
        complete_options = option_generator.ensure_option_space(
            provided_options=provided_options,
            request_intent=request.intent,
        )

        # 4. Constraints validation & feasibility pre-filtering
        validated_options, constraint_conflicts = constraint_validator.validate_options(
            options=complete_options,
            constraints=request.constraints,
        )

        # 5. Evidence synthesis & trust grading
        evidence_set = evidence_engine.build_evidence_set(
            decision_id=request.request_id,
            provided_items=additional_evidence or [],
            simulations=simulations,
            causal_inference=causal_context,
            digital_twin_state={"scope": request.context_scope, "scope_id": request.scope_id},
        )

        # 6. Multi-category risk assessment
        risks = risk_engine.assess_risks(
            options=validated_options,
            risk_tolerance=request.risk_tolerance,
        )

        # 7. Explainable multi-factor scoring
        evaluations = option_scorer.score_options(
            options=validated_options,
            objectives=normalized_objectives,
        )

        # 8. Pareto frontier & trade-off analysis
        tradeoffs, dominated_ids = tradeoff_engine.analyze_tradeoffs(
            options=validated_options,
            evaluations=evaluations,
            objectives=normalized_objectives,
        )

        # 9. Epistemic uncertainty quantification
        uncertainty = uncertainty_engine.assess_uncertainty(
            request=request,
            options=validated_options,
            evidence_set=evidence_set,
            simulations=simulations,
        )

        # 10. Deliberation report (structured decision factors, no raw CoT)
        deliberation_report = deliberation_engine.deliberate(
            request=request,
            options=validated_options,
            evaluations=evaluations,
            tradeoffs=tradeoffs,
            risks=risks,
            evidence_set=evidence_set,
            uncertainty=uncertainty,
            causal_context=causal_context,
            simulation_context=simulations[0] if simulations else None,
        )

        # 11. Deterministic ranking & sensitivity analysis
        ranking = ranking_engine.rank_options(
            options=validated_options,
            evaluations=evaluations,
            tradeoffs=tradeoffs,
            dominated_option_ids=dominated_ids,
            confidence=uncertainty.confidence,
            objectives=normalized_objectives,
        )

        # 12. Evaluate 10 decision gates
        rec_opt = next((o for o in validated_options if o.option_id == ranking.recommended_option_id), None)
        gates, approval_required = gate_evaluation_engine.evaluate_gates(
            request=request,
            leading_option=rec_opt,
            evidence_set=evidence_set,
            risks=risks,
            uncertainty=uncertainty,
            simulations=simulations,
            is_authorized=is_authorized,
            is_production=is_production,
        )

        # 13. Build faithful recommendation
        recommendation = explanation_engine.build_recommendation(
            request=request,
            ranking=ranking,
            options=validated_options,
            deliberation=deliberation_report,
            uncertainty=uncertainty,
            tradeoffs=tradeoffs,
            risks=risks,
            approval_required=approval_required,
        )

        # 14. Provenance tracking & cryptographic fingerprinting
        provenance = provenance_tracker.build_provenance_record(
            request=request,
            options=validated_options,
            ranking=ranking,
            evidence_set=evidence_set,
            risks=risks,
            causal_context=causal_context,
            simulation_context=simulations[0] if simulations else None,
            memory_context=memory_context,
        )

        # 15. Create decision record
        record = decision_lifecycle_manager.create_record(
            request=request,
            recommendation=recommendation,
            ranking=ranking,
            gates=gates,
            approval_required=approval_required,
            provenance=provenance,
        )

        # 16. Audit log
        decision_auditor.log_event(
            decision_id=record.decision_id,
            action="DECISION_EVALUATED",
            actor=request.authority,
            details={
                "recommended_option": recommendation.recommended_option_id,
                "confidence": ranking.confidence,
                "approval_required": approval_required,
                "fingerprint": provenance.get("fingerprint"),
            },
        )

        return record


decision_engine = DecisionEngine()
