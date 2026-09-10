"""Transparent, explainable, normalized scoring for candidate decision options."""

from __future__ import annotations

from app.decision.objectives import ObjectiveManager
from app.decision.schemas import CandidateOption, Objective, OptionEvaluation, ReversibilityLevel


class OptionScorer:
    """Computes transparent, explainable scores combining objective alignment, reversibility, risk, and cost."""

    def __init__(self) -> None:
        self._obj_manager = ObjectiveManager()

    def evaluate_option(
        self,
        option: CandidateOption,
        objectives: list[Objective],
    ) -> OptionEvaluation:
        """Calculates multi-dimensional score with granular breakdown."""
        # 1. Check feasibility
        if not option.is_feasible:
            return OptionEvaluation(
                option_id=option.option_id,
                name=option.name,
                raw_score=0.0,
                normalized_score=0.0,
                rank=999,
                benefit_score=0.0,
                risk_penalty=1.0,
                cost_penalty=0.0,
                complexity_penalty=0.0,
                reversibility_bonus=0.0,
                score_breakdown={"disqualified": 1.0},
                explanation=f"Option disqualified: {option.rejection_reason or 'Failed hard constraints'}.",
            )

        # 2. Objective alignment (0.0 to 1.0)
        alignment = self._obj_manager.calculate_alignment(option.metrics, objectives)

        # 3. Reversibility bonus
        rev_bonus = 0.15 if option.reversibility == ReversibilityLevel.REVERSIBLE else (
            0.05 if option.reversibility == ReversibilityLevel.PARTIALLY_REVERSIBLE else 0.0
        )

        # 4. Risk penalty
        risk_val = option.metrics.get("risk", 0.3)
        risk_penalty = round(min(0.4, risk_val * 0.5), 3)

        # 5. Cost penalty
        cost_val = option.metrics.get("cost", 10.0)
        cost_penalty = round(min(0.3, (cost_val / 100.0) * 0.3), 3)

        # 6. Raw score
        raw = round(alignment + rev_bonus - risk_penalty - cost_penalty, 3)
        raw_bounded = max(0.05, min(1.0, raw))

        breakdown = {
            "objective_alignment": alignment,
            "reversibility_bonus": rev_bonus,
            "risk_penalty": -risk_penalty,
            "cost_penalty": -cost_penalty,
        }

        explanation = (
            f"Composite score {raw_bounded:.2f}: alignment={alignment:.2f}, "
            f"reversibility bonus=+{rev_bonus:.2f}, risk penalty=-{risk_penalty:.2f}, cost penalty=-{cost_penalty:.2f}."
        )

        return OptionEvaluation(
            option_id=option.option_id,
            name=option.name,
            raw_score=raw_bounded,
            normalized_score=raw_bounded,
            benefit_score=alignment,
            risk_penalty=risk_penalty,
            cost_penalty=cost_penalty,
            complexity_penalty=0.0,
            reversibility_bonus=rev_bonus,
            score_breakdown=breakdown,
            explanation=explanation,
        )

    def normalize_scores(self, evaluations: list[OptionEvaluation]) -> list[OptionEvaluation]:
        """Normalizes scores relative to highest feasible score."""
        max_raw = max((e.raw_score for e in evaluations if e.raw_score > 0.0), default=1.0)
        for e in evaluations:
            if e.raw_score > 0.0:
                e.normalized_score = round(e.raw_score / max_raw, 3)
        return evaluations

    def score_options(
        self,
        options: list[CandidateOption],
        objectives: list[Objective],
    ) -> list[OptionEvaluation]:
        """Scores and normalizes all candidate options."""
        evals = [self.evaluate_option(opt, objectives) for opt in options]
        return self.normalize_scores(evals)


option_scorer = OptionScorer()

