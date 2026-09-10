"""Hypothesis Ranking and Evidence Scoring Engine (Task 55, Prompts #29, #30)."""

from __future__ import annotations

from app.causal.evidence import discount_correlated_evidence
from app.causal.schemas import CausalHypothesis, EvidenceStrength, HypothesisStatus

STRENGTH_WEIGHTS: dict[EvidenceStrength, float] = {
    EvidenceStrength.CRITICAL: 1.0,
    EvidenceStrength.STRONG: 0.75,
    EvidenceStrength.MODERATE: 0.50,
    EvidenceStrength.WEAK: 0.25,
}


class HypothesisScorer:
    """Calculates evidence-based scores and ranks competing causal hypotheses."""

    @staticmethod
    def calculate_hypothesis_score(hypothesis: CausalHypothesis) -> float:
        """Computes score [0.0 - 1.0] from discounted independent evidence."""
        if not hypothesis.evidence:
            return 0.15  # Uncorroborated baseline

        discounted = discount_correlated_evidence(hypothesis.evidence)
        total_weight = 0.0

        for ev in discounted:
            w = STRENGTH_WEIGHTS.get(ev.strength, 0.25) * ev.independence
            total_weight += w

        # Non-linear asymptotic saturation: 1 - exp(-0.8 * total_weight)
        score = min(0.98, total_weight / (total_weight + 1.2))
        return round(score, 2)

    @staticmethod
    def rank_hypotheses(hypotheses: list[CausalHypothesis]) -> list[CausalHypothesis]:
        """Prompt #29: Ranks hypotheses by evidence strength and updates hypothesis confidence and status."""
        for h in hypotheses:
            if h.status != HypothesisStatus.REJECTED:
                h.confidence = HypothesisScorer.calculate_hypothesis_score(h)
                if h.confidence >= 0.85:
                    h.status = HypothesisStatus.SUPPORTED
                elif h.confidence >= 0.40:
                    h.status = HypothesisStatus.WEAKLY_SUPPORTED
                else:
                    h.status = HypothesisStatus.PROPOSED

        return sorted(hypotheses, key=lambda h: (h.status != HypothesisStatus.REJECTED, h.confidence), reverse=True)


CausalScorer = HypothesisScorer

