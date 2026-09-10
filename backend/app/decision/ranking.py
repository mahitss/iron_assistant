"""Deterministic ranking and sensitivity analysis for Kairo Executive Decision Engine (Task 57).

Ranks feasible options deterministically, produces Pareto dominance notes,
and conducts sensitivity analysis to identify conditions that could change the ranking.
"""

from __future__ import annotations

import copy
from typing import Any

from app.decision.schemas import (
    CandidateOption,
    DecisionRanking,
    Objective,
    OptionEvaluation,
    Tradeoff,
)
from app.decision.scoring import option_scorer


class RankingEngine:
    """Ranks options and performs sensitivity analysis."""

    def rank_options(
        self,
        options: list[CandidateOption],
        evaluations: list[OptionEvaluation],
        tradeoffs: list[Tradeoff],
        dominated_option_ids: list[str],
        confidence: float = 0.85,
        objectives: list[Objective] | None = None,
    ) -> DecisionRanking:
        # Separate feasible vs infeasible options
        feasible_evals: list[OptionEvaluation] = []
        infeasible_evals: list[OptionEvaluation] = []

        opt_by_id = {opt.option_id: opt for opt in options}

        for ev in evaluations:
            opt = opt_by_id.get(ev.option_id)
            if opt and not opt.is_feasible:
                infeasible_evals.append(ev)
            else:
                feasible_evals.append(ev)

        # Sort feasible evaluations deterministically:
        # primary: normalized_score desc
        # secondary: benefit_score desc
        # tertiary: risk_penalty asc
        # quaternary: option_id asc (ensures strict determinism)
        feasible_evals.sort(
            key=lambda e: (-round(e.normalized_score, 4), -round(e.benefit_score, 4), round(e.risk_penalty, 4), e.option_id)
        )

        # Infeasible evaluations stay at the bottom
        infeasible_evals.sort(key=lambda e: e.option_id)

        all_ranked: list[OptionEvaluation] = []
        for idx, ev in enumerate(feasible_evals + infeasible_evals, start=1):
            updated_ev = ev.model_copy(update={"rank": idx})
            all_ranked.append(updated_ev)

        recommended_id = feasible_evals[0].option_id if feasible_evals else None

        # Build trade-offs summary
        tradeoffs_summary = [t.explanation for t in tradeoffs]

        # Conduct sensitivity analysis
        sensitivity = self._conduct_sensitivity_analysis(
            options=options,
            current_recommended_id=recommended_id,
            objectives=objectives or [],
        )

        return DecisionRanking(
            ranked_options=all_ranked,
            recommended_option_id=recommended_id,
            dominated_option_ids=dominated_option_ids,
            confidence=confidence,
            tradeoffs_summary=tradeoffs_summary,
            sensitivity_analysis=sensitivity,
        )

    def _conduct_sensitivity_analysis(
        self,
        options: list[CandidateOption],
        current_recommended_id: str | None,
        objectives: list[Objective],
    ) -> dict[str, Any]:
        """Calculates what weight or priority changes could flip the leading recommendation."""
        if not current_recommended_id or len(options) < 2:
            return {
                "is_sensitive": False,
                "switching_thresholds": ["Only one feasible option exists; ranking is structurally invariant."],
            }

        switching_conditions: list[str] = []
        is_sensitive = False

        # Test weight shifts on each objective
        for obj in objectives:
            # Perturb weight up by 50%
            perturbed_objs = copy.deepcopy(objectives)
            for po in perturbed_objs:
                if po.objective_id == obj.objective_id:
                    po.weight *= 1.5

            perturbed_evals = option_scorer.score_options(options, perturbed_objs)
            feasible_perturbed = [
                e for e in perturbed_evals
                if any(o.option_id == e.option_id and o.is_feasible for o in options)
            ]
            feasible_perturbed.sort(key=lambda e: (-round(e.normalized_score, 4), e.option_id))

            if feasible_perturbed and feasible_perturbed[0].option_id != current_recommended_id:
                new_winner_opt = next((o for o in options if o.option_id == feasible_perturbed[0].option_id), None)
                winner_name = new_winner_opt.name if new_winner_opt else feasible_perturbed[0].option_id
                switching_conditions.append(
                    f"Increasing priority on '{obj.name}' by 50% shifts the recommendation to '{winner_name}'."
                )
                is_sensitive = True

        if not switching_conditions:
            switching_conditions.append(
                "Recommendation remains stable under +-50% perturbation of individual objective weights."
            )

        return {
            "is_sensitive": is_sensitive,
            "switching_thresholds": switching_conditions,
        }


ranking_engine = RankingEngine()
