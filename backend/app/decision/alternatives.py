"""Alternative candidate options preservation and rejection reason tracking."""

from __future__ import annotations

from pydantic import BaseModel

from app.decision.schemas import CandidateOption, OptionEvaluation


class AlternativeSummary(BaseModel):
    """Summary of an alternative option that was considered but not chosen as top recommendation."""

    option_id: str
    name: str
    rank: int
    score: float
    is_feasible: bool
    status: str  # VIABLE_ALTERNATIVE, DOMINATED, DISQUALIFIED
    rejection_reason: str | None = None
    key_tradeoff: str | None = None


class AlternativeManager:
    """Preserves alternative options and records structured rejection reasons."""

    def preserve_alternatives(
        self,
        options: list[CandidateOption],
        evaluations: list[OptionEvaluation],
        recommended_option_id: str,
        dominated_option_ids: list[str],
    ) -> list[AlternativeSummary]:
        """Summarizes all non-recommended alternatives with their rank, status, and rejection rationale."""
        eval_map = {e.option_id: e for e in evaluations}
        alternatives: list[AlternativeSummary] = []

        for opt in options:
            if opt.option_id == recommended_option_id:
                continue

            ev = eval_map.get(opt.option_id)
            rank = ev.rank if ev else 999
            score = ev.normalized_score if ev else 0.0

            if not opt.is_feasible:
                status = "DISQUALIFIED"
                reason = opt.rejection_reason or "Violated hard constraints"
            elif opt.option_id in dominated_option_ids:
                status = "DOMINATED"
                reason = "Pareto-dominated by one or more superior candidate options."
            else:
                status = "VIABLE_ALTERNATIVE"
                reason = "Lower composite score under current objective weights."

            tradeoff = opt.tradeoffs[0].explanation if opt.tradeoffs else None

            alternatives.append(
                AlternativeSummary(
                    option_id=opt.option_id,
                    name=opt.name,
                    rank=rank,
                    score=score,
                    is_feasible=opt.is_feasible,
                    status=status,
                    rejection_reason=reason,
                    key_tradeoff=tradeoff,
                )
            )

        # Sort alternatives by rank
        alternatives.sort(key=lambda x: x.rank)
        return alternatives


alternative_manager = AlternativeManager()

