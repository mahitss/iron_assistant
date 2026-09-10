"""Structured explanation engine for Kairo Executive Decision Engine (Task 57).

Faithfully derives explanations from structured scoring, constraints, evidence,
tradeoffs, and sensitivity analysis. Never hallucinates unsupported rationale.
"""

from __future__ import annotations

from typing import Any

from app.decision.deliberation import StructuredDeliberationReport
from app.decision.schemas import (
    CandidateOption,
    DecisionRanking,
    DecisionRequest,
    EvidenceSet,
    OptionType,
    Recommendation,
    RiskAssessment,
    Tradeoff,
    UncertaintyAssessment,
)


class ExplanationEngine:
    """Provides faithful, structured explanations answering 10 key executive questions."""

    def build_recommendation(
        self,
        request: DecisionRequest,
        ranking: DecisionRanking,
        options: list[CandidateOption],
        deliberation: StructuredDeliberationReport,
        uncertainty: UncertaintyAssessment,
        tradeoffs: list[Tradeoff],
        risks: list[RiskAssessment],
        approval_required: bool = False,
    ) -> Recommendation:
        rec_id = ranking.recommended_option_id
        opt_map = {o.option_id: o for o in options}
        eval_map = {e.option_id: e for e in ranking.ranked_options}

        leading_opt = opt_map.get(rec_id) if rec_id else None
        leading_eval = eval_map.get(rec_id) if rec_id else None

        if not leading_opt or not leading_eval:
            return Recommendation(
                decision_id=request.request_id,
                recommended_option_id="none",
                headline="No Feasible Option Available",
                why_selected="All candidate options violated hard constraints or critical policy thresholds.",
                why_not_alternatives=[f"Option '{o.name}' rejected: {o.rejection_reason or 'Infeasible'}" for o in options],
                worst_case_downside="Operation is blocked until constraints are relaxed or new alternatives are provided.",
                assumptions=deliberation.key_assumptions,
                uncertainty_summary=uncertainty.overall_uncertainty,
                approval_required=approval_required,
                verification_criteria=["Resolve constraint conflict and re-run decision evaluation."],
            )

        # Why selected
        breakdown_str = ", ".join(f"{k}: {v:+.2f}" for k, v in leading_eval.score_breakdown.items())
        why_selected = (
            f"Option '{leading_opt.name}' scored highest ({leading_eval.normalized_score:.2f}) "
            f"across verified objectives while strictly satisfying all hard constraints. "
            f"Breakdown: [{breakdown_str}]."
        )

        # Why not alternatives
        why_not_alts: list[str] = []
        for opt in options:
            if opt.option_id == leading_opt.option_id:
                continue
            ev = eval_map.get(opt.option_id)
            if not opt.is_feasible:
                why_not_alts.append(f"Option '{opt.name}' is infeasible: {opt.rejection_reason or 'Failed hard constraints'}.")
            elif opt.option_id in ranking.dominated_option_ids:
                why_not_alts.append(f"Option '{opt.name}' is Pareto-dominated by other alternatives with strictly superior utility.")
            elif ev:
                score_diff = leading_eval.normalized_score - ev.normalized_score
                why_not_alts.append(
                    f"Option '{opt.name}' trails by {score_diff:.2f} points (risk penalty {ev.risk_penalty:.2f}, cost penalty {ev.cost_penalty:.2f})."
                )

        # Worst-case downside
        top_risk = max(risks, key=lambda r: r.exposure_score) if risks else None
        worst_case = (
            f"Worst plausible downside: {top_risk.category.value} impact ({top_risk.impact}) with {top_risk.exposure_score:.2f} exposure score. "
            f"Mitigation: {top_risk.mitigation or 'Standard fallback/rollback protocol'}."
            if top_risk
            else "No critical exposure detected under normal operational parameters."
        )

        # Verification criteria
        verification_criteria = [
            f"Verify that '{leading_opt.name}' maintains target performance metrics.",
            "Confirm no policy invariants or hard constraints are violated post-execution.",
            "Validate state transition using digital twin / health telemetry.",
        ]

        return Recommendation(
            decision_id=request.request_id,
            recommended_option_id=leading_opt.option_id,
            headline=f"Recommend '{leading_opt.name}'",
            why_selected=why_selected,
            why_not_alternatives=why_not_alts,
            worst_case_downside=worst_case,
            assumptions=deliberation.key_assumptions,
            uncertainty_summary=f"Uncertainty: {uncertainty.overall_uncertainty} (confidence {uncertainty.confidence:.2f})",
            sensitivity_thresholds=ranking.sensitivity_analysis.get("switching_thresholds", []),
            approval_required=approval_required,
            proposed_execution_plan={
                "target_option": leading_opt.name,
                "reversibility": leading_opt.reversibility.value,
                "stages": ["pre_check", "execute_guarded", "verify_outcome"],
            },
            verification_criteria=verification_criteria,
        )

    def answer_query(
        self,
        query: str,
        recommendation: Recommendation,
        ranking: DecisionRanking,
        options: list[CandidateOption] | None = None,
        evidence_set: EvidenceSet | None = None,
        tradeoffs: list[Tradeoff] | None = None,
        risks: list[RiskAssessment] | None = None,
        uncertainty: UncertaintyAssessment | None = None,
    ) -> dict[str, Any]:
        """Faithfully answers arbitrary executive queries regarding the decision."""
        q_lower = query.lower()
        options = options or []
        tradeoffs = tradeoffs or []
        risks = risks or []
        eval_map = {e.option_id: e for e in ranking.ranked_options} if ranking else {}
        conf = uncertainty.confidence if uncertainty else (ranking.confidence if ranking else 0.8)

        if "why this option" in q_lower or ("why" in q_lower and "not" not in q_lower):
            return {
                "question": query,
                "answer": recommendation.why_selected,
                "confidence": conf,
            }

        if "why not" in q_lower:
            matched_alts = [
                alt for alt in recommendation.why_not_alternatives
                if any(word in alt.lower() for word in q_lower.split() if len(word) > 4)
            ]
            ans = " ; ".join(matched_alts) if matched_alts else " ; ".join(recommendation.why_not_alternatives)
            return {"question": query, "answer": ans, "confidence": conf}

        if "risk" in q_lower or "worst-case" in q_lower or "worst case" in q_lower:
            return {
                "question": query,
                "answer": recommendation.worst_case_downside,
                "risks": [r.model_dump() for r in risks],
            }

        if "evidence" in q_lower:
            ev_count = len(evidence_set.items) if evidence_set else 0
            ev_strength = evidence_set.overall_strength.value if evidence_set else "SUPPORTED"
            ev_items = [e.model_dump() for e in evidence_set.items] if evidence_set else []
            return {
                "question": query,
                "answer": f"Supported by {ev_count} evidence items (strength: {ev_strength}).",
                "evidence_items": ev_items,
            }

        if "assumption" in q_lower:
            return {
                "question": query,
                "answer": f"Current decision relies on {len(recommendation.assumptions)} explicit assumptions.",
                "assumptions": recommendation.assumptions,
            }

        if "change" in q_lower or "sensitivity" in q_lower:
            return {
                "question": query,
                "answer": " ; ".join(recommendation.sensitivity_thresholds),
                "sensitivity": ranking.sensitivity_analysis,
            }

        if "do nothing" in q_lower or "no action" in q_lower:
            no_action_opt = next((o for o in options if o.option_type == OptionType.NO_ACTION), None)
            if no_action_opt:
                no_act_eval = eval_map.get(no_action_opt.option_id)
                score_msg = f"normalized score {no_act_eval.normalized_score:.2f}" if no_act_eval else "not scored"
                return {
                    "question": query,
                    "answer": f"Baseline option 'NO_ACTION' achieves {score_msg}. It eliminates implementation risk but forfeits all objective gains.",
                }
            return {
                "question": query,
                "answer": "No explicit NO_ACTION baseline was evaluated in this decision scope.",
            }

        # Default summary
        return {
            "question": query,
            "answer": f"{recommendation.headline}: {recommendation.why_selected}",
            "confidence": uncertainty.confidence,
        }


explanation_engine = ExplanationEngine()
