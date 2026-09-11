"""Deliberation engine for Kairo Autonomous Reasoning (Task 71).

Performs:
- Competing hypothesis evaluation & scoring
- Alternative generation and tradeoff analysis
- Counterargument generation ("What could make this conclusion wrong?")
- Dissenting opinion preservation (multi-agent perspectives)
- Safe conclusion synthesis and user-facing explanations (strictly no private chain-of-thought)
"""

import logging
from typing import Any

from app.reasoning.schemas import (
    AssumptionStatus,
    ConclusionStatus,
    HypothesisStatus,
    ReasoningAlternative,
    ReasoningAssumption,
    ReasoningConclusion,
    ReasoningConfidence,
    ReasoningEvidence,
    ReasoningExplanation,
    ReasoningHypothesis,
    SubProblem,
    UncertaintyType,
)

logger = logging.getLogger(__name__)


class DeliberationEngine:
    """Core deliberator comparing hypotheses, balancing tradeoffs, and generating safe conclusions."""

    def evaluate_hypotheses(
        self,
        hypotheses: list[ReasoningHypothesis],
        evidence_pool: list[ReasoningEvidence],
    ) -> list[ReasoningHypothesis]:
        """Rank and evaluate competing hypotheses based on empirical evidence quality."""
        ev_map = {e.evidence_id: e for e in evidence_pool}

        for hyp in hypotheses:
            # Calculate independent supporting and contradicting weight
            support_groups: set[str] = set()
            support_weight = 0.0
            for eid in hyp.supporting_evidence_ids:
                if eid in ev_map:
                    ev = ev_map[eid]
                    # Check source independence
                    if ev.independence_group not in support_groups:
                        support_groups.add(ev.independence_group)
                        support_weight += ev.reliability * ev.relevance

            contradict_groups: set[str] = set()
            contradict_weight = 0.0
            for eid in hyp.contradicting_evidence_ids:
                if eid in ev_map:
                    ev = ev_map[eid]
                    if ev.independence_group not in contradict_groups:
                        contradict_groups.add(ev.independence_group)
                        contradict_weight += ev.reliability * ev.relevance

            # Assign status based on empirical weights
            if contradict_weight > 1.2 and contradict_weight > support_weight:
                hyp.status = HypothesisStatus.CONTRADICTED
                hyp.confidence = ReasoningConfidence.LOW
            elif support_weight > 1.5 and contradict_weight < 0.3:
                hyp.status = HypothesisStatus.SUPPORTED
                hyp.confidence = (
                    ReasoningConfidence.HIGH if len(support_groups) >= 2 else ReasoningConfidence.MEDIUM
                )
            elif support_weight > 0.5:
                hyp.status = HypothesisStatus.WEAKLY_SUPPORTED
                hyp.confidence = ReasoningConfidence.MEDIUM
            else:
                hyp.status = HypothesisStatus.UNRESOLVED
                hyp.confidence = ReasoningConfidence.LOW

        # Sort with highest supported first
        hypotheses.sort(
            key=lambda h: (
                h.status == HypothesisStatus.SUPPORTED,
                h.status == HypothesisStatus.WEAKLY_SUPPORTED,
                len(h.supporting_evidence_ids) - len(h.contradicting_evidence_ids),
            ),
            reverse=True,
        )
        return hypotheses

    def generate_alternatives(
        self,
        question: str,
        leading_hypotheses: list[ReasoningHypothesis],
    ) -> list[ReasoningAlternative]:
        """Generate structured alternatives and tradeoff options for actionable problems."""
        alternatives: list[ReasoningAlternative] = []

        if not leading_hypotheses:
            alternatives.append(
                ReasoningAlternative(
                    title="Gather More Evidence",
                    description="Insufficient evidence to take corrective action; collect targeted observations.",
                    risk_score=0.1,
                    cost_score=0.1,
                    time_estimate_sec=30,
                    reversibility=1.0,
                    expected_impact=0.4,
                    confidence=ReasoningConfidence.MEDIUM,
                )
            )
            return alternatives

        best = leading_hypotheses[0]
        # Alternative 1: Direct remediation
        alternatives.append(
            ReasoningAlternative(
                title=f"Direct Remediation for {best.description[:40]}",
                description=f"Address primary root cause hypothesis '{best.description}'.",
                risk_score=0.3,
                cost_score=0.4,
                time_estimate_sec=120,
                reversibility=0.7,
                expected_impact=0.85,
                confidence=best.confidence,
            )
        )

        # Alternative 2: Conservative / Rollback
        alternatives.append(
            ReasoningAlternative(
                title="Conservative Rollback / Safe Mode",
                description="Revert to last known good state or engage graceful degradation.",
                risk_score=0.15,
                cost_score=0.2,
                time_estimate_sec=60,
                reversibility=0.9,
                expected_impact=0.75,
                confidence=ReasoningConfidence.HIGH,
            )
        )

        # Alternative 3: Isolated Diagnostics
        alternatives.append(
            ReasoningAlternative(
                title="Targeted Falsification & Isolation",
                description="Run isolated validation tests to disprove secondary hypotheses.",
                risk_score=0.1,
                cost_score=0.15,
                time_estimate_sec=45,
                reversibility=1.0,
                expected_impact=0.6,
                confidence=ReasoningConfidence.MEDIUM,
            )
        )

        return alternatives

    def generate_counterarguments(
        self,
        hypothesis: ReasoningHypothesis,
        evidence_pool: list[ReasoningEvidence],
    ) -> list[str]:
        """Identify potential flaws: 'What could make this conclusion wrong?'"""
        counters: list[str] = []

        # Check for single-source dependency
        if len(hypothesis.supporting_evidence_ids) <= 1:
            counters.append(
                "Supported by only a single evidence source; vulnerable to isolated telemetry or sensor error."
            )

        # Check for contradicting items
        if hypothesis.contradicting_evidence_ids:
            counters.append(
                f"Contradicted by {len(hypothesis.contradicting_evidence_ids)} empirical observations."
            )

        # Add generic falsification challenges if unaddressed
        if hypothesis.falsification_conditions:
            for cond in hypothesis.falsification_conditions[:2]:
                counters.append(f"Unverified condition: If {cond}, hypothesis is refuted.")
        else:
            counters.append(
                "Alternative latent causes (e.g. concurrent external load or upstream dependency) not ruled out."
            )

        hypothesis.counterarguments = counters
        return counters

    def synthesize_conclusion(
        self,
        question: str,
        evaluated_hypotheses: list[ReasoningHypothesis],
        assumptions: list[ReasoningAssumption],
        evidence_pool: list[ReasoningEvidence],
        subproblem: SubProblem | None = None,
    ) -> tuple[ReasoningConclusion, ReasoningExplanation]:
        """Synthesize a structured conclusion with a safe, concise user explanation."""
        supported = [
            h
            for h in evaluated_hypotheses
            if h.status in (HypothesisStatus.SUPPORTED, HypothesisStatus.WEAKLY_SUPPORTED)
        ]
        contradicted = [h for h in evaluated_hypotheses if h.status == HypothesisStatus.CONTRADICTED]

        # Determine uncertainty state
        if not evaluated_hypotheses:
            uncertainty = UncertaintyType.UNKNOWN
            conf = ReasoningConfidence.VERY_LOW
            status = ConclusionStatus.PROVISIONAL
            summary = f"Unable to establish conclusion for '{question}': No plausible hypotheses identified."
        elif not supported and contradicted:
            uncertainty = UncertaintyType.CONFLICTING
            conf = ReasoningConfidence.LOW
            status = ConclusionStatus.REJECTED
            summary = f"All candidate explanations for '{question}' were empirically contradicted."
        elif supported:
            top = supported[0]
            uncertainty = (
                UncertaintyType.KNOWN
                if top.status == HypothesisStatus.SUPPORTED
                else UncertaintyType.UNCERTAIN
            )
            conf = top.confidence
            status = ConclusionStatus.SUPPORTED
            summary = f"Leading conclusion for '{question}': {top.description}"
        else:
            uncertainty = UncertaintyType.UNCERTAIN
            conf = ReasoningConfidence.LOW
            status = ConclusionStatus.PROVISIONAL
            summary = f"Evidence for '{question}' remains inconclusive across candidate hypotheses."

        conclusion = ReasoningConclusion(
            subproblem_id=subproblem.subproblem_id if subproblem else None,
            summary=summary,
            status=status,
            confidence=conf,
            uncertainty_state=uncertainty,
            supporting_hypothesis_ids=[h.hypothesis_id for h in supported],
            assumption_ids=[a.assumption_id for a in assumptions if a.status != AssumptionStatus.INVALIDATED],
            counterarguments_addressed=[c for h in supported for c in h.counterarguments],
            falsification_tested=any(len(h.falsification_conditions) > 0 for h in supported),
        )

        # Build user-safe concise explanation (strictly no private chain-of-thought)
        supporting_reasons = []
        for h in supported[:2]:
            ev_count = len(h.supporting_evidence_ids)
            supporting_reasons.append(
                f"Hypothesis '{h.description}' backed by {ev_count} empirical evidence sources."
            )

        assumptions_made = [f"Assumes: {a.description} (status: {a.status.value})" for a in assumptions[:3]]

        remaining_uncertainty = ""
        if uncertainty != UncertaintyType.KNOWN:
            remaining_uncertainty = (
                "Uncertainty remains due to partial evidence coverage or unverified assumptions."
            )

        explanation = ReasoningExplanation(
            conclusion_summary=summary,
            confidence=conf,
            uncertainty_state=uncertainty,
            supporting_reasons=supporting_reasons,
            counterarguments_addressed=conclusion.counterarguments_addressed[:3],
            assumptions_made=assumptions_made,
            remaining_uncertainty=remaining_uncertainty,
        )

        return conclusion, explanation

    def preserve_dissent(
        self,
        agent_hypotheses: dict[str, list[ReasoningHypothesis]],
    ) -> dict[str, Any]:
        """Aggregate multi-agent deliberation, preserving minority and dissenting perspectives."""
        tally: dict[str, list[str]] = {}
        for agent_id, hyps in agent_hypotheses.items():
            for h in hyps:
                desc = h.description
                if desc not in tally:
                    tally[desc] = []
                tally[desc].append(agent_id)

        sorted_opinions = sorted(tally.items(), key=lambda item: len(item[1]), reverse=True)
        majority = sorted_opinions[0] if sorted_opinions else ("None", [])
        dissenting = sorted_opinions[1:] if len(sorted_opinions) > 1 else []

        return {
            "majority_view": majority[0],
            "majority_agents": majority[1],
            "dissenting_views": [{"hypothesis": view, "supporters": agents} for view, agents in dissenting],
            "consensus_reached": len(sorted_opinions) == 1 or (len(majority[1]) >= 2 * len(dissenting)),
        }
