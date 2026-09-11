"""Hypothesis Generation and Lifecycle Engine (Task 71).

Formulates competing candidate hypotheses, tracks supporting/contradicting evidence,
attaches explicit falsification conditions, and manages status transitions.
INVARIANT: Candidate hypotheses are NEVER treated as facts.
"""

from app.reasoning.schemas import (
    HypothesisStatus,
    ReasoningConfidence,
    ReasoningEvidence,
    ReasoningHypothesis,
)


class HypothesisEngine:
    """Coordinates generation, evaluation, and falsification tracking of hypotheses."""

    @classmethod
    def generate_hypotheses(
        cls,
        *,
        question: str,
        subproblem_id: str | None = None,
        context_clues: list[str] | None = None,
    ) -> list[ReasoningHypothesis]:
        """Formulate candidate hypotheses with explicit falsification conditions."""
        q_lower = question.lower()
        hypotheses: list[ReasoningHypothesis] = []

        if any(w in q_lower for w in ["latency", "slow", "performance", "timeout"]):
            h1 = ReasoningHypothesis(
                subproblem_id=subproblem_id,
                description="Database query contention or unindexed query degradation.",
                falsification_conditions=[
                    "Database query latency and connection pool metrics remain normal during symptom window."
                ],
                counterarguments=["Recent database CPU utilization was reported under 20%."],
            )
            h2 = ReasoningHypothesis(
                subproblem_id=subproblem_id,
                description="Recent application deployment or configuration change regression.",
                falsification_conditions=[
                    "Symptoms began before deployment timestamp or continue after complete rollback."
                ],
                counterarguments=["No deployment occurred within 24 hours prior to incident."],
            )
            h3 = ReasoningHypothesis(
                subproblem_id=subproblem_id,
                description="External dependency or third-party downstream gateway outage.",
                falsification_conditions=[
                    "Third-party health checks and external latency probes show 100% success."
                ],
                counterarguments=["Internal microservices also fail without external calls."],
            )
            hypotheses.extend([h1, h2, h3])

        elif any(w in q_lower for w in ["unstable", "crash", "restart", "500"]):
            h1 = ReasoningHypothesis(
                subproblem_id=subproblem_id,
                description="Memory leak or out-of-memory (OOM) pod termination.",
                falsification_conditions=[
                    "Host/container memory stayed within safe thresholds (< 60%) at crash time."
                ],
                counterarguments=["Process exited with exit code 0 rather than SIGKILL."],
            )
            h2 = ReasoningHypothesis(
                subproblem_id=subproblem_id,
                description="Deadlock or connection exhaustion in thread/connection pool.",
                falsification_conditions=[
                    "Active thread/connection counts remained below 30% of pool limit."
                ],
                counterarguments=["Other threads continued serving requests normally."],
            )
            hypotheses.extend([h1, h2])

        else:
            h1 = ReasoningHypothesis(
                subproblem_id=subproblem_id,
                description=f"Primary factor: {question[:80]} is driven by active operational changes.",
                falsification_conditions=["No operational changes correlate with observed outcome."],
            )
            h2 = ReasoningHypothesis(
                subproblem_id=subproblem_id,
                description=f"Alternative factor: {question[:80]} is driven by external environmental shifts.",
                falsification_conditions=["External environmental variables remained strictly constant."],
            )
            hypotheses.extend([h1, h2])

        return hypotheses

    @classmethod
    def evaluate_hypothesis(
        cls,
        hypothesis: ReasoningHypothesis,
        evidence_items: list[ReasoningEvidence],
    ) -> ReasoningHypothesis:
        """Evaluate evidence against hypothesis, check falsification, and update confidence."""
        supporting = [e for e in evidence_items if e.evidence_id in hypothesis.supporting_evidence_ids]
        contradicting = [e for e in evidence_items if e.evidence_id in hypothesis.contradicting_evidence_ids]

        # Check for falsification trigger
        is_falsified = False
        for c in contradicting:
            if c.reliability >= 0.85 and c.relevance >= 0.85:
                # Strong verified contradiction
                for f_cond in hypothesis.falsification_conditions:
                    if f_cond.lower() in c.content_summary.lower() or "disprove" in c.content_summary.lower():
                        is_falsified = True
                        break

        if is_falsified:
            hypothesis.status = HypothesisStatus.DISPROVEN
            hypothesis.confidence = ReasoningConfidence.VERY_LOW
            return hypothesis

        if contradicting:
            if len(contradicting) > len(supporting):
                hypothesis.status = HypothesisStatus.CONTRADICTED
                hypothesis.confidence = ReasoningConfidence.LOW
            else:
                hypothesis.status = HypothesisStatus.WEAKLY_SUPPORTED
                hypothesis.confidence = ReasoningConfidence.LOW
        elif len(supporting) >= 2:
            hypothesis.status = HypothesisStatus.SUPPORTED
            hypothesis.confidence = ReasoningConfidence.HIGH
        elif len(supporting) == 1:
            hypothesis.status = HypothesisStatus.WEAKLY_SUPPORTED
            hypothesis.confidence = ReasoningConfidence.MEDIUM
        else:
            hypothesis.status = HypothesisStatus.CANDIDATE
            hypothesis.confidence = ReasoningConfidence.LOW

        return hypothesis

    @classmethod
    def generate_initial_hypotheses(cls, question: str) -> list[ReasoningHypothesis]:
        """Convenience alias for initial hypothesis generation."""
        return cls.generate_hypotheses(question=question)


HypothesisGenerator = HypothesisEngine
