"""Belief Revision Engine for Task 107.

Coordinates non-destructive, append-only belief revisions.
Ensures history is NEVER mutated.
Enforces anti-oscillation dampeners to prevent pathological thrashing.

Strict Invariants:
- Never overwrite past versions.
- Every revision requires an explicit RevisionReason.
- Contradictory evidence is preserved alongside supporting evidence.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.belief.domain import (
    ArbitrationOutcome,
    Belief,
    BeliefRevision,
    BeliefStatus,
    BeliefVersion,
    Claim,
    EvidenceAssessment,
    EvidenceItem,
    RevisionReason,
    UncertaintyType,
    generate_uuid,
    utc_now,
)

logger = logging.getLogger("kairo.belief.revision")


class BeliefRevisionEngine:
    """Coordinates non-destructive, versioned revisions of the belief manifold."""

    def __init__(self, materiality_threshold: float = 0.03) -> None:
        self.materiality_threshold = materiality_threshold

    def calculate_epistemic_state(
        self,
        assessments: List[EvidenceAssessment],
    ) -> Tuple[BeliefStatus, float, float, UncertaintyType]:
        """Aggregate evidence assessments into status, confidence, and uncertainty.
        
        Returns:
            (status, confidence, uncertainty, uncertainty_type)
        """
        support_weight = sum(a.weight for a in assessments if a.outcome == ArbitrationOutcome.SUPPORTS)
        contradict_weight = sum(a.weight for a in assessments if a.outcome == ArbitrationOutcome.CONTRADICTS)
        total_eval = support_weight + contradict_weight

        if total_eval <= 0.05:
            # Almost no evidence
            return BeliefStatus.CANDIDATE, 0.4, 0.6, UncertaintyType.INSUFFICIENT_EVIDENCE

        # Calculate empirical balance
        net_ratio = support_weight / (total_eval + 1e-6)

        # Check if latest assessment is a strong verified contradiction
        latest_is_strong_contradiction = (
            bool(assessments) and assessments[-1].outcome == ArbitrationOutcome.CONTRADICTS and assessments[-1].weight >= 0.8
        )

        # 1. Active contradiction check
        if (contradict_weight > 0.6 and net_ratio < 0.35) or latest_is_strong_contradiction:
            conf = max(0.1, round(net_ratio * 0.3, 3))
            return BeliefStatus.CONTRADICTED, conf, round(1.0 - conf, 3), UncertaintyType.CONFLICTED

        # 2. Contested check (substantial evidence on both sides)
        if support_weight >= 0.4 and contradict_weight >= 0.3:
            conf = 0.5
            return BeliefStatus.CONTESTED, conf, 0.5, UncertaintyType.CONFLICTED

        # 3. High confidence check (multiple strong supporting, zero strong contradictions)
        if support_weight >= 1.6 and contradict_weight < 0.15:
            conf = min(0.98, round(0.7 + 0.1 * min(support_weight, 2.8), 3))
            return BeliefStatus.CONFIDENT, conf, round(1.0 - conf, 3), UncertaintyType.NONE

        # 4. Standard supported check
        if support_weight >= 0.8 and contradict_weight < 0.25:
            conf = min(0.85, round(0.55 + 0.15 * min(support_weight, 2.0), 3))
            return BeliefStatus.SUPPORTED, conf, round(1.0 - conf, 3), UncertaintyType.NONE

        # 5. Provisional check
        conf = max(0.3, min(0.65, round(net_ratio * 0.7, 3)))
        return BeliefStatus.PROVISIONAL, conf, round(1.0 - conf, 3), UncertaintyType.UNVERIFIED

    def revise_belief_with_evidence(
        self,
        belief: Belief,
        new_evidence: EvidenceItem,
        assessment: EvidenceAssessment,
        all_assessments: List[EvidenceAssessment],
        reason: RevisionReason = RevisionReason.NEW_EVIDENCE,
        notes: str = "",
    ) -> Optional[Tuple[Belief, BeliefVersion, BeliefRevision]]:
        """Perform non-destructive revision if evidence represents a material epistemic change.
        
        Returns:
            (revised_belief, minted_version, revision_record) or None if below materiality threshold.
        """
        # Calculate new status & confidence
        new_status, new_conf, new_uncert, uncert_type = self.calculate_epistemic_state(all_assessments)

        # Anti-Oscillation / Materiality Check
        conf_delta = abs(new_conf - belief.confidence)
        status_changed = new_status != belief.status

        if not status_changed and conf_delta < self.materiality_threshold:
            # Immaterial change - update evidence link without minting a noisy new version
            if assessment.outcome == ArbitrationOutcome.SUPPORTS:
                if new_evidence.evidence_id not in belief.evidence_ids:
                    belief.evidence_ids.append(new_evidence.evidence_id)
            elif assessment.outcome == ArbitrationOutcome.CONTRADICTS:
                if new_evidence.evidence_id not in belief.contradiction_evidence_ids:
                    belief.contradiction_evidence_ids.append(new_evidence.evidence_id)
            belief.updated_at = utc_now()
            return None

        # Record prior version before revision
        prior_version_num = belief.current_version
        prior_status = belief.status
        prior_conf = belief.confidence

        # Increment version number
        new_version_num = prior_version_num + 1

        # Track evidence IDs
        support_ids = list(belief.evidence_ids)
        contradict_ids = list(belief.contradiction_evidence_ids)

        if assessment.outcome == ArbitrationOutcome.SUPPORTS and new_evidence.evidence_id not in support_ids:
            support_ids.append(new_evidence.evidence_id)
        elif assessment.outcome == ArbitrationOutcome.CONTRADICTS and new_evidence.evidence_id not in contradict_ids:
            contradict_ids.append(new_evidence.evidence_id)

        # Mint immutable BeliefVersion
        version_record = BeliefVersion(
            version_id=generate_uuid("blfv"),
            belief_id=belief.belief_id,
            version_number=new_version_num,
            status=new_status,
            confidence=new_conf,
            uncertainty=new_uncert,
            uncertainty_type=uncert_type,
            claim_id=belief.claim_id,
            evidence_ids=support_ids,
            contradiction_evidence_ids=contradict_ids,
            revision_reason=reason,
            revision_notes=notes or assessment.explanation,
            created_at=utc_now(),
        )

        # Create audit revision record
        revision_record = BeliefRevision(
            revision_id=generate_uuid("brev"),
            belief_id=belief.belief_id,
            prior_version_number=prior_version_num,
            new_version_number=new_version_num,
            prior_status=prior_status,
            new_status=new_status,
            prior_confidence=prior_conf,
            new_confidence=new_conf,
            reason=reason,
            evidence_id_trigger=new_evidence.evidence_id,
            notes=notes or f"Confidence adjusted from {prior_conf:.2f} to {new_conf:.2f}",
            timestamp=utc_now(),
        )

        # Mutate current belief object
        belief.current_version = new_version_num
        belief.status = new_status
        belief.confidence = new_conf
        belief.uncertainty = new_uncert
        belief.uncertainty_type = uncert_type
        belief.evidence_ids = support_ids
        belief.contradiction_evidence_ids = contradict_ids
        belief.last_evaluated_at = utc_now()
        if new_status in {BeliefStatus.CONFIDENT, BeliefStatus.SUPPORTED}:
            belief.last_verified_at = utc_now()
            belief.is_stale = False
        belief.updated_at = utc_now()

        logger.info(
            "BELIEF_REVISED: id=%s v%d -> v%d [%s -> %s] conf=%.2f -> %.2f reason=%s",
            belief.belief_id,
            prior_version_num,
            new_version_num,
            prior_status.value,
            new_status.value,
            prior_conf,
            new_conf,
            reason.value,
        )

        return belief, version_record, revision_record
