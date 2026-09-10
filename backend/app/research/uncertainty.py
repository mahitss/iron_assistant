"""Epistemic uncertainty analyzer categorizing known, unknown, uncertain, disputed, assumed, and inferred (Task 63)."""

from __future__ import annotations

import logging
from typing import Any

from app.research.schemas import (
    Claim,
    ClaimType,
    ConflictRecord,
    ConflictStatus,
    Evidence,
    EvidenceStrength,
    UncertaintyRecord,
)

logger = logging.getLogger(__name__)


class UncertaintyEngine:
    """Categorizes research findings into rigorous epistemological buckets.

    Invariant 23: Every synthesis explicitly separates what is known, unknown, uncertain,
    disputed, assumed, and inferred.
    """

    def analyze_uncertainty(
        self,
        session_id: str = "sess_default",
        claims: list[Claim] | None = None,
        evidence_list: list[Evidence] | None = None,
        conflicts: list[ConflictRecord] | None = None,
        unanswered_sub_questions: list[str] | None = None,
        *,
        hypotheses: list[Any] | None = None,
        **kwargs: Any,
    ) -> UncertaintyRecord:
        """Partition synthesized findings into distinct epistemic categories."""
        claims = claims or []
        evidence_list = evidence_list or []
        conflicts = conflicts or []
        known: list[str] = []
        uncertain: list[str] = []
        disputed: list[str] = []
        assumed: list[str] = []
        inferred: list[str] = []
        unknown: list[str] = unanswered_sub_questions or []

        # Find disputed claim IDs
        disputed_claim_ids = set()
        for cfl in conflicts:
            if cfl.status in (ConflictStatus.DETECTED, ConflictStatus.UNRESOLVED):
                disputed_claim_ids.add(cfl.claim_a_id)
                disputed_claim_ids.add(cfl.claim_b_id)
                disputed.append(f"Disputed: {cfl.description}")

        # Map evidence by claim_id
        ev_by_claim: dict[str, list[Evidence]] = {}
        for ev in evidence_list:
            if ev.claim_id not in ev_by_claim:
                ev_by_claim[ev.claim_id] = []
            ev_by_claim[ev.claim_id].append(ev)

        for claim in claims:
            if claim.claim_id in disputed_claim_ids:
                continue

            evs = ev_by_claim.get(claim.claim_id, [])

            # Categorize by claim type and evidence strength
            if claim.claim_type == ClaimType.HYPOTHETICAL or "assume" in claim.claim_text.lower():
                assumed.append(f"Assumption: {claim.claim_text}")
            elif claim.claim_type == ClaimType.INFERRED:
                inferred.append(f"Inference: {claim.claim_text}")
            elif claim.claim_type in (ClaimType.OBSERVED, ClaimType.MEASURED) or any(
                e.strength
                in (
                    EvidenceStrength.STRONG,
                    EvidenceStrength.DIRECT_MEASUREMENT,
                    EvidenceStrength.CONTROLLED_EXPERIMENT,
                    EvidenceStrength.PRIMARY_DOCUMENT,
                )
                for e in evs
            ):
                known.append(f"Verified Fact: {claim.claim_text}")
            elif any(e.strength == EvidenceStrength.MODERATE for e in evs):
                uncertain.append(f"Moderate Evidence (unreproduced): {claim.claim_text}")
            else:
                uncertain.append(f"Weak/Unverified Assertion: {claim.claim_text}")

        record = UncertaintyRecord(
            session_id=session_id,
            known=known,
            unknown=unknown,
            uncertain=uncertain,
            disputed=disputed,
            assumed=assumed,
            inferred=inferred,
        )

        logger.info(
            "UNCERTAINTY_ANALYZED: session=%s known=%d unknown=%d disputed=%d uncertain=%d",
            session_id,
            len(known),
            len(unknown),
            len(disputed),
            len(uncertain),
        )
        return record


uncertainty_engine = UncertaintyEngine()
