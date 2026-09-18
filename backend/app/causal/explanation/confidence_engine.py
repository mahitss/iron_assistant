"""Confidence & Quality Assessment Engine for Task 112:
Calculates multi-dimensional causal confidence and explanation quality without single-score opacity.

Strict Invariants:
- NO OPAQUE SINGLE SCORES
- SIMULATION CANNOT SERVE AS EMPIRICAL REALITY (Discounted)
- FORECAST CANNOT SERVE AS OBSERVATION (Discounted)
- CONTRADICTORY EVIDENCE MUST IMPOSE A DIRECT PENALTY
"""

from __future__ import annotations

from typing import List, Tuple

from app.causal.explanation.domain import (
    CausalAlternative,
    CausalConfidenceBreakdown,
    CausalLink,
    EvidenceClassification,
    ExplanationEvidence,
    ExplanationQualityAssessment,
)

# Epistemic directness weights matching Task 107
EPISTEMIC_WEIGHTS = {
    EvidenceClassification.DIRECT: 1.0,
    EvidenceClassification.DERIVED: 0.85,
    EvidenceClassification.HISTORICAL: 0.70,
    EvidenceClassification.USER_REPORTED: 0.50,
    EvidenceClassification.AGENT_REPORTED: 0.45,
    EvidenceClassification.SIMULATION: 0.40,  # Cannot prove real-world behavior
    EvidenceClassification.PREDICTIVE: 0.35,  # Prospective models != observation
    EvidenceClassification.INDIRECT: 0.60,
    EvidenceClassification.UNVERIFIED: 0.30,
}


class CausalConfidenceEngine:
    """Evaluates multi-dimensional causal confidence and assesses explanation quality."""

    @classmethod
    def evaluate_confidence(
        cls,
        links: List[CausalLink],
        evidence_items: List[ExplanationEvidence],
        is_temporally_valid: bool = True,
        is_cause_unknown: bool = False,
    ) -> CausalConfidenceBreakdown:
        """Calculates decomposed confidence across temporal, mechanistic, and empirical axes."""
        if is_cause_unknown or not links:
            return CausalConfidenceBreakdown(
                temporal_fit=0.5 if is_temporally_valid else 0.0,
                mechanism_fit=0.0,
                evidence_strength=0.0,
                evidence_independence=1.0,
                contradiction_penalty=0.0,
                uncertainty_score=1.0,
                observational_completeness=0.1,
                composite_confidence=0.0,
            )

        # 1. Temporal fit
        temporal_fit = 1.0 if is_temporally_valid else 0.0

        # 2. Mechanism fit: based on completeness and causal nature of proposed links
        from app.causal.explanation.domain import CausalRelationshipRole
        has_direct_causal_role = any(
            l.relationship_role in (
                CausalRelationshipRole.DIRECT_CAUSE,
                CausalRelationshipRole.CONTRIBUTING_CAUSE,
                CausalRelationshipRole.TRIGGER,
                CausalRelationshipRole.UPSTREAM_CAUSE,
            )
            for l in links
        )
        if not has_direct_causal_role:
            mechanism_fit = 0.2
        else:
            has_mechanisms = all(bool(l.mechanism and l.mechanism != "Unknown") for l in links)
            mechanism_fit = 0.9 if has_mechanisms else 0.4

        # 3. Evidence strength and independence
        if evidence_items:
            # Weighted average based on epistemic classifications
            weights = [EPISTEMIC_WEIGHTS.get(ev.classification, 0.5) * ev.weight for ev in evidence_items]
            avg_strength = sum(weights) / len(weights)
            # Check source diversity for independence
            unique_sources = len(set(ev.source_subsystem for ev in evidence_items))
            independence = min(1.0, 0.5 + (unique_sources * 0.15))
            # Contradictions
            contradictions = [ev for ev in evidence_items if ev.is_contradiction]
            contradiction_penalty = min(1.0, len(contradictions) * 0.3)
        else:
            avg_strength = 0.3
            independence = 1.0
            contradiction_penalty = 0.0

        observational_completeness = min(1.0, len(evidence_items) * 0.25) if evidence_items else 0.2

        return CausalConfidenceBreakdown.calculate_composite(
            temporal_fit=temporal_fit,
            mechanism_fit=mechanism_fit,
            evidence_strength=avg_strength,
            evidence_independence=independence,
            contradiction_penalty=contradiction_penalty,
            observational_completeness=observational_completeness,
        )

    @classmethod
    def evaluate_quality(
        cls,
        confidence: CausalConfidenceBreakdown,
        links: List[CausalLink],
        alternatives: List[CausalAlternative],
        evidence_items: List[ExplanationEvidence],
    ) -> ExplanationQualityAssessment:
        """Assesses explanation quality across coverage, alternatives, and calibration."""
        evidence_coverage = min(1.0, len(evidence_items) * 0.2)
        causal_support = confidence.composite_confidence
        temporal_consistency = confidence.temporal_fit
        mechanism_completeness = confidence.mechanism_fit
        alternative_coverage = min(1.0, len(alternatives) * 0.5)
        contradiction_visibility = 1.0  # We explicitly surface contradictions
        uncertainty_calibrated = 1.0 if (confidence.uncertainty_score + confidence.composite_confidence == 1.0) else 0.8

        overall = round(
            (
                evidence_coverage * 0.2
                + causal_support * 0.25
                + temporal_consistency * 0.15
                + mechanism_completeness * 0.15
                + alternative_coverage * 0.15
                + uncertainty_calibrated * 0.10
            ),
            3,
        )

        return ExplanationQualityAssessment(
            evidence_coverage=evidence_coverage,
            causal_support=causal_support,
            temporal_consistency=temporal_consistency,
            mechanism_completeness=mechanism_completeness,
            alternative_coverage=alternative_coverage,
            contradiction_visibility=contradiction_visibility,
            uncertainty_calibration=uncertainty_calibrated,
            overall_quality=overall,
        )
