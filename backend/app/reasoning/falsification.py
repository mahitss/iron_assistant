"""Falsification engine for Kairo Autonomous Reasoning (Task 71).

Implements Popperian falsification-oriented inquiry:
- Generates empirical conditions that would disprove candidate hypotheses
- Evaluates incoming evidence specifically against falsifiers
- Prioritizes information gain tests that have highest discriminatory power
"""

import logging

from app.reasoning.schemas import (
    HypothesisStatus,
    ReasoningConfidence,
    ReasoningEvidence,
    ReasoningHypothesis,
)

logger = logging.getLogger(__name__)


class FalsificationEngine:
    """Formulates and tests empirical falsification conditions against hypotheses."""

    def formulate_falsifiers(self, hypothesis: ReasoningHypothesis) -> list[str]:
        """Formulate high-value empirical conditions that would refute the hypothesis."""
        falsifiers: list[str] = []
        desc_lower = hypothesis.description.lower()

        if "deploy" in desc_lower or "release" in desc_lower:
            falsifiers.append("Anomaly or latency spike started prior to the deployment timestamp.")
            falsifiers.append(
                "Identical failure reproduces on an isolated node running the previous version."
            )
        elif "database" in desc_lower or "db" in desc_lower:
            falsifiers.append(
                "Database query execution times, connection pool, and CPU remain at normal baselines."
            )
            falsifiers.append("Error occurs on requests that make no database interactions.")
        elif "network" in desc_lower:
            falsifiers.append("Intra-cluster packet loss and latency metrics are within normal SLA limits.")
            falsifiers.append("Local loopback requests exhibit the exact same degradation.")
        elif "traffic" in desc_lower or "load" in desc_lower:
            falsifiers.append(
                "Request volume (RPS) is equal to or below historical averages during the incident window."
            )
        else:
            falsifiers.append(
                f"Empirical baseline metrics remain completely stable despite {hypothesis.description[:30]}."
            )
            falsifiers.append(
                "Counter-factual rollback or traffic diversion fails to alter the observed symptoms."
            )

        hypothesis.falsification_conditions = falsifiers
        return falsifiers

    def test_evidence_against_falsifiers(
        self,
        hypothesis: ReasoningHypothesis,
        evidence: ReasoningEvidence,
    ) -> bool:
        """Evaluate if an empirical observation triggers a falsification condition.

        Returns True if the hypothesis is refuted.
        """
        content_lower = evidence.content_summary.lower()

        for cond in hypothesis.falsification_conditions:
            cond_lower = cond.lower()

            # Check for temporal refutation (e.g. occurred before deployment)
            if "started prior" in cond_lower and ("prior" in content_lower or "before" in content_lower):
                logger.warning(
                    f"Hypothesis {hypothesis.hypothesis_id} FALSIFIED by evidence {evidence.evidence_id}: '{evidence.content_summary}'"
                )
                hypothesis.status = HypothesisStatus.DISPROVEN
                hypothesis.confidence = ReasoningConfidence.VERY_LOW
                if evidence.evidence_id not in hypothesis.contradicting_evidence_ids:
                    hypothesis.contradicting_evidence_ids.append(evidence.evidence_id)
                return True

            # Check for normal baseline refutation
            if "remain at normal" in cond_lower and (
                "normal" in content_lower or "baseline" in content_lower or "healthy" in content_lower
            ):
                logger.warning(
                    f"Hypothesis {hypothesis.hypothesis_id} FALSIFIED by baseline evidence {evidence.evidence_id}"
                )
                hypothesis.status = HypothesisStatus.DISPROVEN
                hypothesis.confidence = ReasoningConfidence.VERY_LOW
                if evidence.evidence_id not in hypothesis.contradicting_evidence_ids:
                    hypothesis.contradicting_evidence_ids.append(evidence.evidence_id)
                return True

        return False

    def rank_by_information_gain(
        self,
        hypotheses: list[ReasoningHypothesis],
    ) -> list[tuple[ReasoningHypothesis, float]]:
        """Rank hypotheses by expected information gain from falsification tests.

        Prioritizes untested hypotheses with high uncertainty or strong candidate status.
        """
        scored = []
        for hyp in hypotheses:
            if hyp.status == HypothesisStatus.DISPROVEN:
                score = 0.0
            elif hyp.status == HypothesisStatus.CANDIDATE:
                score = 0.9  # High priority to discriminate
            elif hyp.status == HypothesisStatus.WEAKLY_SUPPORTED:
                score = 0.7
            else:
                score = 0.4
            scored.append((hyp, score))

        scored.sort(key=lambda item: item[1], reverse=True)
        return scored
