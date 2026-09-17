"""Evidence Arbitration Engine for Task 107:
Evaluates evidence items against claims, tracks lineage to prevent double-counting,
detects circular self-confirmation, and applies rigorous epistemic weighting.

Strict Invariants:
- 100 duplicate agent reports != 100 independent confirmations.
- Simulation != Reality.
- Forecast != Observation.
- Memory != Current truth.
- Contradictory evidence must NEVER be discarded.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Set, Tuple

from app.belief.domain import (
    ArbitrationOutcome,
    Claim,
    EvidenceAssessment,
    EvidenceClassification,
    EvidenceItem,
    generate_uuid,
    utc_now,
)

logger = logging.getLogger("kairo.belief.arbitration")

# Epistemic directness & baseline weight coefficients by source classification
BASE_CLASSIFICATION_WEIGHTS: Dict[EvidenceClassification, float] = {
    EvidenceClassification.DIRECT_OBSERVATION: 1.0,
    EvidenceClassification.VERIFIED_OUTCOME: 1.0,
    EvidenceClassification.INDEPENDENT_EVALUATION: 0.95,
    EvidenceClassification.TELEMETRY: 0.90,
    EvidenceClassification.EXPERIMENTAL: 0.85,
    EvidenceClassification.INFERRED: 0.65,
    EvidenceClassification.MEMORY: 0.60,
    EvidenceClassification.USER_ASSERTION: 0.50,
    EvidenceClassification.EXTERNAL_SOURCE: 0.50,
    EvidenceClassification.AGENT_REPORT: 0.45,
    EvidenceClassification.SIMULATION: 0.40,  # Simulations cannot prove real-world behavior
    EvidenceClassification.FORECAST: 0.35,    # Forecasts are prospective models, not observations
}


class EvidenceArbitrationEngine:
    """Arbitrates evidence items against claims with anti-poisoning and anti-circularity controls."""

    def __init__(self) -> None:
        # Track seen content hashes and source lineages to prevent duplicate/correlated inflation
        self._seen_content_hashes: Set[str] = set()
        self._lineage_counts: Dict[str, int] = {}  # root_source_or_derived_id -> count

    def evaluate_evidence(
        self,
        evidence: EvidenceItem,
        claim: Claim,
        historical_evidence: Optional[List[EvidenceItem]] = None,
    ) -> EvidenceAssessment:
        """Arbitrate an individual evidence item against a claim proposition."""
        hist = historical_evidence or []
        
        # 1. Check for circularity
        if self._is_circular_lineage(evidence, claim):
            logger.warning(
                "CIRCULAR_LINEAGE_DETECTED: Evidence %s derives from Claim %s lineage. Capping weight.",
                evidence.evidence_id,
                claim.claim_id,
            )
            return EvidenceAssessment(
                evidence_id=evidence.evidence_id,
                claim_id=claim.claim_id,
                outcome=ArbitrationOutcome.UNKNOWN,
                weight=0.05,
                explanation="Circular lineage detected: Evidence derives from the same proposition it attempts to validate.",
            )

        # 2. Check scope alignment
        if evidence.scope != claim.scope and evidence.scope != "SYSTEM" and claim.scope != "SYSTEM":
            # Out-of-scope evidence cannot directly arbitrate this scoped claim
            return EvidenceAssessment(
                evidence_id=evidence.evidence_id,
                claim_id=claim.claim_id,
                outcome=ArbitrationOutcome.NEUTRAL,
                weight=0.0,
                explanation=f"Scope mismatch: Evidence scope '{evidence.scope}' does not match claim scope '{claim.scope}'.",
            )

        # 3. Determine outcome (SUPPORTS, CONTRADICTS, NEUTRAL, UNKNOWN)
        outcome, outcome_reason = self._determine_outcome(evidence, claim)

        # 4. Calculate effective epistemic weight
        effective_weight = self._compute_effective_weight(evidence, hist)

        return EvidenceAssessment(
            evidence_id=evidence.evidence_id,
            claim_id=claim.claim_id,
            outcome=outcome,
            weight=effective_weight,
            explanation=outcome_reason,
            assessed_at=utc_now(),
        )

    def _determine_outcome(
        self, evidence: EvidenceItem, claim: Claim
    ) -> Tuple[ArbitrationOutcome, str]:
        """Compare evidence payload with claim subject/predicate/object."""
        content = evidence.content or {}
        
        # Look for explicit status or values in evidence payload
        ev_subject = content.get("subject", "")
        ev_predicate = content.get("predicate", "")
        
        # If subject/predicate specified in payload and don't match, check if it's general telemetry/observation
        if ev_subject and ev_subject != claim.subject:
            return ArbitrationOutcome.NEUTRAL, f"Evidence subject '{ev_subject}' does not address claim subject '{claim.subject}'."
        if ev_predicate and ev_predicate != claim.predicate:
            return ArbitrationOutcome.NEUTRAL, f"Evidence predicate '{ev_predicate}' does not address claim predicate '{claim.predicate}'."

        # Check observed value against claimed value
        observed_val = content.get("observed_value")
        if observed_val is None:
            observed_val = content.get("value")
        if observed_val is None:
            observed_val = content.get("status")

        # Explicit success/failure or boolean checks
        if observed_val is not None:
            if observed_val == claim.object_value:
                return ArbitrationOutcome.SUPPORTS, f"Observed value '{observed_val}' directly matches claimed value '{claim.object_value}'."
            else:
                return ArbitrationOutcome.CONTRADICTS, f"Observed value '{observed_val}' contradicts claimed value '{claim.object_value}'."

        # If evidence reports an error or failure condition targeting the claim
        if content.get("failed") is True or content.get("is_error") is True:
            # If claim asserted success/health/ready
            if str(claim.object_value).upper() in {"HEALTHY", "READY", "AVAILABLE", "TRUE", "PASS"}:
                return ArbitrationOutcome.CONTRADICTS, "Evidence reports error/failure for healthy proposition."

        # Fallback to textual summary inspection
        summary_lower = (evidence.summary or "").lower()
        if "timeout" in summary_lower or "failed" in summary_lower or "unhealthy" in summary_lower or "error" in summary_lower:
            if str(claim.object_value).upper() in {"HEALTHY", "READY", "AVAILABLE", "TRUE", "PASS"}:
                return ArbitrationOutcome.CONTRADICTS, f"Evidence summary indicates failure: {evidence.summary}"

        if "verified" in summary_lower or "success" in summary_lower or "ready" in summary_lower or "healthy" in summary_lower:
            if str(claim.object_value).upper() in {"HEALTHY", "READY", "AVAILABLE", "TRUE", "PASS"}:
                return ArbitrationOutcome.SUPPORTS, f"Evidence summary confirms proposition: {evidence.summary}"

        return ArbitrationOutcome.UNKNOWN, "Evidence payload does not provide unambiguous confirmation or refutation."

    def _compute_effective_weight(
        self, evidence: EvidenceItem, historical: List[EvidenceItem]
    ) -> float:
        """Compute de-duplicated, anti-poisoning weighted confidence contribution."""
        base = BASE_CLASSIFICATION_WEIGHTS.get(evidence.source_type, 0.5)
        reliability = evidence.reliability_weight

        # Anti-Poisoning & Anti-Correlated Duplication Check:
        # Check if identical content hash was seen
        if evidence.content_hash in self._seen_content_hashes:
            # Duplicate evidence content! Zero incremental weight
            return 0.0
        self._seen_content_hashes.add(evidence.content_hash)

        # Check for correlated lineage (e.g. agent citing another agent)
        if evidence.derived_from_evidence_ids:
            repetition = 1
            for k in evidence.derived_from_evidence_ids:
                cnt = self._lineage_counts.get(k, 0)
                if cnt + 1 > repetition:
                    repetition = cnt + 1
                self._lineage_counts[k] = cnt + 1
        else:
            repetition = self._lineage_counts.get(evidence.source_id, 0)
            self._lineage_counts[evidence.source_id] = repetition + 1

        self._lineage_counts[evidence.evidence_id] = repetition + 1

        # Damping factor: 1 / sqrt(repetition + 1)
        damping = 1.0 / math.sqrt(repetition + 1)
        effective = base * reliability * damping
        return max(0.0, min(1.0, round(effective, 4)))

    def _is_circular_lineage(self, evidence: EvidenceItem, claim: Claim) -> bool:
        """Detect whether evidence lineage recursively references the claim."""
        prov = claim.provenance or {}
        claim_origin_ev = prov.get("evidence_ids", [])
        if evidence.evidence_id in claim_origin_ev:
            return True
        for dev in evidence.derived_from_evidence_ids:
            if dev in claim_origin_ev:
                return True
        return False
