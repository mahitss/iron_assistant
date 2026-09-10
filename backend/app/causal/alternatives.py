"""Alternative Causal Hypotheses Generation and Systematic Elimination (Task 55, Prompts #27, #28, #161, #162)."""

from __future__ import annotations

from typing import Any

from app.causal.hypotheses import HypothesisManager
from app.causal.schemas import CausalEvidence, CausalHypothesis, HypothesisStatus

# Canonical failure categories per Prompt #28
STANDARD_CANDIDATE_CAUSES = [
    {"cause": "deployment", "mechanism": "New code version introduced regression or broken contract"},
    {"cause": "database_saturation", "mechanism": "Exhausted connection pool or I/O bottleneck causing query queuing"},
    {"cause": "network_failure", "mechanism": "Packet loss, DNS resolution failure, or partition between services"},
    {"cause": "traffic_spike", "mechanism": "Request rate surge exceeding ingress or worker capacity"},
    {"cause": "dependency_outage", "mechanism": "Upstream third-party API or downstream microservice failure"},
    {"cause": "configuration_error", "mechanism": "Mismatched environment flags, secret reference error, or timeout change"},
]


class AlternativeHypothesisGenerator:
    """Generates and evaluates competing causal explanations for observed system failures."""

    @staticmethod
    def generate_candidate_hypotheses(
        effect: str,
        context_clues: dict[str, Any] | None = None,
    ) -> list[CausalHypothesis]:
        """Prompt #27, #28: Generates standard competing hypotheses for an incident effect."""
        hypotheses = []
        clues = context_clues or {}

        for candidate in STANDARD_CANDIDATE_CAUSES:
            cause = candidate["cause"]
            # Base confidence 0.3 for uncorroborated candidate
            conf = 0.3
            if cause in clues.get("active_flags", []):
                conf = 0.6

            h = HypothesisManager.create_hypothesis(
                cause=cause,
                effect=effect,
                mechanism=candidate["mechanism"],
                confidence=conf,
                status=HypothesisStatus.PROPOSED,
            )
            hypotheses.append(h)

        # Cross-reference alternatives list in each hypothesis
        all_causes = [h.cause for h in hypotheses]
        for h in hypotheses:
            h.alternatives = [c for c in all_causes if c != h.cause]

        return hypotheses

    @staticmethod
    def eliminate_hypothesis_with_evidence(
        hypothesis: CausalHypothesis,
        contradicting_evidence: CausalEvidence,
        elimination_reason: str,
    ) -> dict[str, Any]:
        """Prompt #162: Mark hypotheses eliminated ONLY with empirical evidence."""
        hypothesis.status = HypothesisStatus.REJECTED
        hypothesis.evidence.append(contradicting_evidence)
        hypothesis.confidence = 0.05
        return {
            "hypothesis_id": hypothesis.hypothesis_id,
            "cause": hypothesis.cause,
            "status": "ELIMINATED",
            "evidence_id": contradicting_evidence.evidence_id,
            "reason": elimination_reason,
        }

    @staticmethod
    def generate_candidates(incident_type: str = "service_latency_increase") -> list[str]:
        """Prompt #27, #28: Return standard candidate causes as string keys."""
        return [c["cause"] for c in STANDARD_CANDIDATE_CAUSES]


CausalAlternativeGenerator = AlternativeHypothesisGenerator

