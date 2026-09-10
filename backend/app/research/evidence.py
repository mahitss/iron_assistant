"""Evidence extraction, strength evaluation, directness rating, and source independence linking (Task 63)."""

from __future__ import annotations

import logging

from app.research.schemas import (
    Claim,
    ClaimType,
    Evidence,
    EvidenceDirectness,
    EvidenceStrength,
    EvidenceType,
    Source,
    SourceType,
)
from app.research.sources import SourceDependencyGraph, source_dependency_graph

logger = logging.getLogger(__name__)


class EvidenceManager:
    """Manages concrete evidence items supporting or refuting claims.

    Invariant 2 & 14: Evidence is structured backing with clear strength levels, not arbitrary fake probabilities.
    """

    def __init__(self, dep_graph: SourceDependencyGraph | None = None) -> None:
        self._evidence_items: dict[str, Evidence] = {}
        self._dep_graph = dep_graph or source_dependency_graph

    def link_evidence(
        self,
        claim: Claim,
        source: Source,
        excerpt_reference: str,
        document_id: str | None = None,
        location: str = "",
        explicit_type: EvidenceType | None = None,
    ) -> Evidence:
        """Create an evidence record linking a source excerpt to a specific claim."""
        ev_type = explicit_type or self._derive_evidence_type(claim, source)
        strength = self._evaluate_evidence_strength(ev_type, source)
        directness = self._evaluate_directness(claim, ev_type)
        independence = 1.0 if source.is_primary else 0.65

        evidence = Evidence(
            claim_id=claim.claim_id,
            source_id=source.source_id,
            document_id=document_id,
            excerpt_reference=excerpt_reference,
            location=location,
            evidence_type=ev_type,
            strength=strength,
            directness=directness,
            independence_score=independence,
        )

        self._evidence_items[evidence.evidence_id] = evidence
        claim.evidence_refs.append(evidence.evidence_id)

        logger.info(
            "EVIDENCE_LINKED: evd=%s claim=%s type=%s strength=%s directness=%s",
            evidence.evidence_id,
            claim.claim_id,
            evidence.evidence_type.value,
            evidence.strength.value,
            evidence.directness.value,
        )
        return evidence

    def create_evidence(
        self,
        claim_id: str,
        source_id: str,
        excerpt_reference: str,
        location: str = "",
        evidence_type: EvidenceType = EvidenceType.PRIMARY_DOCUMENT,
        strength: EvidenceStrength = EvidenceStrength.MODERATE,
        directness: EvidenceDirectness = EvidenceDirectness.DIRECT,
        document_id: str | None = None,
    ) -> Evidence:
        """Directly create and track a structured evidence record."""
        evidence = Evidence(
            claim_id=claim_id,
            source_id=source_id,
            excerpt_reference=excerpt_reference,
            location=location,
            evidence_type=evidence_type,
            strength=strength,
            directness=directness,
            document_id=document_id,
        )
        self._evidence_items[evidence.evidence_id] = evidence
        return evidence

    def get_strength_weight(self, strength: EvidenceStrength) -> float:
        """Return structured weight for evidence strength hierarchy (Invariant 14)."""
        weights = {
            EvidenceStrength.DIRECT_MEASUREMENT: 1.0,
            EvidenceStrength.CONTROLLED_EXPERIMENT: 0.95,
            EvidenceStrength.REPRODUCED_RESULT: 0.95,
            EvidenceStrength.PRIMARY_DOCUMENT: 0.90,
            EvidenceStrength.STRONG: 0.90,
            EvidenceStrength.SECONDARY_REPORT: 0.70,
            EvidenceStrength.EXPERT_OPINION: 0.65,
            EvidenceStrength.MODERATE: 0.65,
            EvidenceStrength.MODEL_INFERENCE: 0.50,
            EvidenceStrength.WEAK: 0.40,
            EvidenceStrength.UNVERIFIED_ASSERTION: 0.20,
            EvidenceStrength.UNVERIFIED: 0.10,
        }
        return weights.get(strength, 0.50)

    def get_evidence(self, evidence_id: str) -> Evidence | None:
        """Retrieve evidence item by ID."""
        return self._evidence_items.get(evidence_id)

    def list_evidence_for_claim(self, claim_id: str) -> list[Evidence]:
        """List all evidence linked to a specific claim."""
        return [e for e in self._evidence_items.values() if e.claim_id == claim_id]

    def _derive_evidence_type(self, claim: Claim, source: Source) -> EvidenceType:
        """Derive the evidence type based on claim characteristics and source credibility."""
        if claim.claim_type == ClaimType.MEASURED:
            if source.source_type in (SourceType.DATASET, SourceType.DATABASE, SourceType.INTERNAL_SYSTEM):
                return EvidenceType.DIRECT_MEASUREMENT
            if source.source_type == SourceType.ACADEMIC_PAPER:
                return EvidenceType.CONTROLLED_EXPERIMENT
            return EvidenceType.PRIMARY_DOCUMENT

        if source.is_primary:
            return EvidenceType.PRIMARY_DOCUMENT

        if source.source_type == SourceType.NEWS:
            return EvidenceType.SECONDARY_REPORT

        if claim.claim_type == ClaimType.INFERRED:
            return EvidenceType.MODEL_INFERENCE

        if claim.claim_type in (ClaimType.OPINION, ClaimType.NORMATIVE):
            return EvidenceType.EXPERT_OPINION

        return EvidenceType.SECONDARY_REPORT

    def _evaluate_evidence_strength(self, ev_type: EvidenceType, source: Source) -> EvidenceStrength:
        """Assign evidence strength category without fabricating fake mathematical probabilities."""
        if source.is_retracted:
            return EvidenceStrength.UNVERIFIED

        if ev_type in (
            EvidenceType.DIRECT_MEASUREMENT,
            EvidenceType.CONTROLLED_EXPERIMENT,
            EvidenceType.REPRODUCED_RESULT,
        ):
            return EvidenceStrength.STRONG if source.authority_score >= 0.80 else EvidenceStrength.MODERATE

        if ev_type == EvidenceType.PRIMARY_DOCUMENT:
            return EvidenceStrength.STRONG if source.authority_score >= 0.85 else EvidenceStrength.MODERATE

        if ev_type in (EvidenceType.SECONDARY_REPORT, EvidenceType.EXPERT_OPINION):
            return EvidenceStrength.MODERATE if source.authority_score >= 0.70 else EvidenceStrength.WEAK

        return EvidenceStrength.WEAK

    def _evaluate_directness(self, claim: Claim, ev_type: EvidenceType) -> EvidenceDirectness:
        """Evaluate if evidence directly tests the claim or is circumstantial."""
        if ev_type in (
            EvidenceType.DIRECT_MEASUREMENT,
            EvidenceType.CONTROLLED_EXPERIMENT,
            EvidenceType.PRIMARY_DOCUMENT,
        ):
            return EvidenceDirectness.DIRECT
        if ev_type == EvidenceType.MODEL_INFERENCE:
            return EvidenceDirectness.INDIRECT
        return EvidenceDirectness.CIRCUMSTANTIAL


evidence_manager = EvidenceManager()
