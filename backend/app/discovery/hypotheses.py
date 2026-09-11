"""Hypothesis Generation, Prioritization and Falsification (Task 72).

Enforces generation of competing hypotheses with explicit Popperian falsification criteria,
supporting/contradicting evidence tracking, and multi-factor ranking.
"""

import uuid
from typing import Any

from app.discovery.schemas import DiscoveryHypothesis


class HypothesisEngine:
    """Manages generation, ranking, and falsification of competing scientific hypotheses."""

    def create_hypothesis(
        self,
        description: str,
        falsification_criteria: list[str],
        supporting_evidence: list[str] | None = None,
        contradicting_evidence: list[str] | None = None,
        plausibility: float = 0.7,
        testability: float = 0.8,
        confidence: float = 0.5,
        source: str = "autonomous_discovery",
        question_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> DiscoveryHypothesis:
        """Constructs a structured hypothesis with mandatory falsification criteria."""
        if not falsification_criteria:
            raise ValueError(
                "A scientific hypothesis must define at least one explicit falsification criterion."
            )

        h_id = f"hyp_{uuid.uuid4().hex[:12]}"
        return DiscoveryHypothesis(
            hypothesis_id=h_id,
            question_id=question_id,
            description=description.strip(),
            supporting_evidence=list(supporting_evidence or []),
            contradicting_evidence=list(contradicting_evidence or []),
            falsification_criteria=list(falsification_criteria),
            confidence=max(0.0, min(1.0, float(confidence))),
            status="CANDIDATE",
            plausibility=max(0.0, min(1.0, float(plausibility))),
            testability=max(0.0, min(1.0, float(testability))),
            source=source,
            metadata=metadata or {},
        )

    def generate_competing_hypotheses(
        self,
        question: str,
        candidate_explanations: list[dict[str, Any]],
        question_id: str | None = None,
    ) -> list[DiscoveryHypothesis]:
        """Generates multiple competing hypotheses for a research question.

        Strict Principle: Never settle on a single explanation; evaluate competing alternatives.
        """
        hypotheses: list[DiscoveryHypothesis] = []
        for item in candidate_explanations:
            desc = item.get("description", "")
            falsifiers = item.get("falsification_criteria", [])
            if not falsifiers:
                # Default logical falsifier if not specified
                falsifiers = [f"Observation contradicting premise: {desc}"]
            hyp = self.create_hypothesis(
                description=desc,
                falsification_criteria=falsifiers,
                supporting_evidence=item.get("supporting_evidence", []),
                contradicting_evidence=item.get("contradicting_evidence", []),
                plausibility=float(item.get("plausibility", 0.7)),
                testability=float(item.get("testability", 0.8)),
                confidence=float(item.get("confidence", 0.5)),
                source=item.get("source", "autonomous_discovery"),
                question_id=question_id,
            )
            hypotheses.append(hyp)
        return hypotheses

    def rank_hypotheses(
        self,
        hypotheses: list[DiscoveryHypothesis],
        weight_plausibility: float = 0.35,
        weight_testability: float = 0.35,
        weight_evidence_balance: float = 0.30,
    ) -> list[DiscoveryHypothesis]:
        """Ranks competing hypotheses without arbitrary confidence inflation.

        Score combines plausibility, testability, and empirical balance
        (supporting vs contradicting evidence).
        """

        def score(h: DiscoveryHypothesis) -> float:
            support_count = len(h.supporting_evidence)
            contra_count = len(h.contradicting_evidence)
            total_ev = support_count + contra_count
            ev_balance = (support_count / total_ev) if total_ev > 0 else 0.5

            # Contradicting evidence strongly penalizes score
            penalty = 0.3 if contra_count > 0 else 0.0

            composite = (
                (h.plausibility * weight_plausibility)
                + (h.testability * weight_testability)
                + (ev_balance * weight_evidence_balance)
                - penalty
            )
            return max(0.0, min(1.0, composite))

        return sorted(hypotheses, key=score, reverse=True)

    def deduplicate_hypotheses(
        self,
        hypotheses: list[DiscoveryHypothesis],
    ) -> list[DiscoveryHypothesis]:
        """Removes duplicates when multiple agents propose identical explanations."""
        seen: set[str] = set()
        unique: list[DiscoveryHypothesis] = []
        for h in hypotheses:
            normalized = h.description.lower().strip()
            if normalized not in seen:
                seen.add(normalized)
                unique.append(h)
        return unique
