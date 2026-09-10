"""Root-Cause Analysis Engine, Causal Chains, and Multi-Factor Modeling (Task 55, Prompts #31-#40, #164, #186-#190)."""

from __future__ import annotations

import uuid

from app.causal.safety import CausalSafetyGuard
from app.causal.schemas import (
    CausalEvidence,
    CausalHypothesis,
    EvidenceStrength,
    RootCauseAnalysis,
    RootCauseChain,
    RootCauseStatus,
)


class RootCauseAnalyzer:
    """Performs rigorous root-cause analysis distinguishing primary triggers, mechanisms, and contributing factors."""

    @staticmethod
    def initialize_analysis(
        incident_id: str,
        candidate_causes: list[str] | None = None,
        evidence: list[CausalEvidence] | None = None,
        symptom: str | None = None,
    ) -> RootCauseAnalysis:
        aid = f"rca_{uuid.uuid4().hex[:10]}"
        cands = list(candidate_causes) if candidate_causes else []
        return RootCauseAnalysis(
            analysis_id=aid,
            incident_id=incident_id,
            candidate_causes=cands,
            evidence=evidence or [],
            eliminated_causes=[],
            surviving_causes=list(cands),
            root_cause=None,
            contributing_factors=[],
            causal_chain=None,
            is_necessary=False,
            is_sufficient=False,
            confidence=0.2,
            status=RootCauseStatus.INVESTIGATING,
        )

    create_analysis = initialize_analysis


    @staticmethod
    def build_causal_chain(
        underlying_condition: str,
        trigger: str,
        mechanism: str,
        symptom: str,
        impact: str,
    ) -> RootCauseChain:
        """Prompt #34, #189: Chains underlying condition -> trigger -> mechanism -> symptom -> impact."""
        return RootCauseChain(
            underlying_condition=underlying_condition,
            trigger=trigger,
            mechanism=mechanism,
            symptom=symptom,
            impact=impact,
        )

    @staticmethod
    def evaluate_root_cause(
        analysis: RootCauseAnalysis,
        hypotheses: list[CausalHypothesis] | None = None,
        ranked_hypotheses: list[CausalHypothesis] | None = None,
        require_verification: bool = False,
    ) -> RootCauseAnalysis:
        """Evaluates surviving hypotheses and determines likely or verified root cause."""
        # Prompt #164: Never invent a root cause when evidence is insufficient
        candidate_list = hypotheses or ranked_hypotheses or []
        if not candidate_list:
            analysis.root_cause = None
            analysis.status = RootCauseStatus.UNKNOWN
            analysis.confidence = 0.0
            return analysis

        sorted_hypo = sorted(candidate_list, key=lambda h: h.confidence, reverse=True)
        top = sorted_hypo[0]


        # Check for verified vs likely
        has_critical_evidence = any(
            ev.strength == EvidenceStrength.CRITICAL for ev in top.evidence
        )

        analysis.surviving_causes = [h.cause for h in sorted_hypo if h.confidence >= 0.40]
        analysis.contributing_factors = [h.cause for h in sorted_hypo[1:] if h.confidence >= 0.35]

        if top.confidence >= 0.85 and has_critical_evidence:
            analysis.root_cause = top.cause
            analysis.status = RootCauseStatus.VERIFIED
            analysis.confidence = top.confidence
        elif top.confidence >= 0.60:
            analysis.root_cause = top.cause
            analysis.status = RootCauseStatus.LIKELY  # Prompt #33: LIKELY remains distinct from VERIFIED
            analysis.confidence = top.confidence
        elif top.confidence >= 0.35:
            analysis.root_cause = top.cause
            analysis.status = RootCauseStatus.SUPPORTED
            analysis.confidence = top.confidence
        else:
            # Prompt #163: Unknown cause is valid
            analysis.root_cause = None
            analysis.status = RootCauseStatus.UNKNOWN
            analysis.confidence = top.confidence

        # If verification was asserted or required, enforce safety guard
        if require_verification:
            CausalSafetyGuard.validate_root_cause_claim(
                root_cause=analysis.root_cause,
                is_verified=True,
                evidence_list=top.evidence,
            )

        return analysis

    update_with_ranked_hypotheses = evaluate_root_cause


RootCauseAnalysisEngine = RootCauseAnalyzer


