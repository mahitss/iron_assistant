"""Belief Query and Structured Explanation Engine for Task 107.

Answers:
- What does Kairo currently believe about X?
- Why does it believe it?
- What evidence supports it?
- What contradicts it?
- How fresh is that evidence?
- What uncertainty remains?
- What would change the belief?

Produces compact BeliefEvidencePack for Task 93 Context Assembler & Task 94 Decision Intelligence.
Strictly avoids dumping hidden chain-of-thought or raw unformatted history.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.belief.domain import (
    Belief,
    Claim,
    EvidenceItem,
    utc_now,
)
from app.belief.schemas import (
    BeliefEvidencePack,
    BeliefExplanationResponse,
)

logger = logging.getLogger("kairo.belief.query")


class BeliefQueryEngine:
    """Provides concise, evidence-grounded queries and explanations."""

    def explain_belief(
        self,
        belief: Belief,
        claim: Optional[Claim],
        evidence_items: List[EvidenceItem],
        contradictions: List[EvidenceItem],
    ) -> BeliefExplanationResponse:
        """Construct structured, evidence-backed explanation."""
        now = utc_now()
        anchor = belief.last_verified_at or belief.valid_from
        freshness_mins = round((now - anchor).total_seconds() / 60.0, 1)

        val_str = str(claim.object_value) if claim else "unknown"

        # Evidence summaries
        why_ev = [
            f"[{e.source_type.value}] {e.summary or 'Observed telemetry/result'} (weight: {e.reliability_weight:.2f})"
            for e in evidence_items[:5]
        ]
        if not why_ev:
            why_ev = ["No direct supporting evidence registered; initial candidate assertion."]

        # Contradiction summaries
        when_not = [
            f"[{c.source_type.value}] {c.summary or 'Contradicting observation'} (weight: {c.reliability_weight:.2f})"
            for c in contradictions[:5]
        ]
        if not when_not:
            when_not = ["Zero active contradictions observed."]

        # Limitations
        limits = []
        if belief.is_stale:
            limits.append(f"Evidence is stale ({freshness_mins} mins old; exceeded TTL {belief.freshness_ttl_seconds}s).")
        if belief.uncertainty > 0.3:
            limits.append(f"Uncertainty remaining: {belief.uncertainty_type.value} ({belief.uncertainty * 100:.1f}%).")
        if any(e.source_type.value in {"SIMULATION", "FORECAST"} for e in evidence_items):
            limits.append("Partially relies on model simulation or forecasting; not fully proven in production.")

        # Revalidation triggers
        revalidation = [
            "Receipt of contradicting telemetry or error response from the target domain.",
            f"Passage of freshness TTL ({belief.freshness_ttl_seconds}s) without confirming observation.",
            "Material drift or configuration change reported by Task 98 World-State.",
            "Degradation or limitation reported by Task 101 Self-Model.",
        ]

        return BeliefExplanationResponse(
            belief_id=belief.belief_id,
            subject=belief.subject,
            predicate=belief.predicate,
            status=belief.status,
            confidence=belief.confidence,
            uncertainty=belief.uncertainty,
            uncertainty_type=belief.uncertainty_type,
            what=f"Kairo believes that {belief.subject} {belief.predicate} is '{val_str}' with {belief.confidence * 100:.1f}% confidence.",
            when=f"Valid from {belief.valid_from.isoformat()} (last verified {freshness_mins} mins ago).",
            why_evidence=why_ev,
            when_not_contradictions=when_not,
            limitations=limits,
            last_verified=belief.last_verified_at.isoformat() if belief.last_verified_at else None,
            revalidation_triggers=revalidation,
        )

    def assemble_evidence_pack(
        self,
        belief: Belief,
        evidence_items: List[EvidenceItem],
        contradictions: List[EvidenceItem],
    ) -> BeliefEvidencePack:
        """Assemble a compact, bounded BeliefEvidencePack for Context & Decision engines."""
        now = utc_now()
        anchor = belief.last_verified_at or belief.valid_from
        freshness_sec = (now - anchor).total_seconds()

        ev_summaries = [e.summary or f"{e.source_type.value} from {e.source_id}" for e in evidence_items[:4]]
        cntr_summaries = [c.summary or f"{c.source_type.value} conflict" for c in contradictions[:4]]

        limits = []
        if belief.is_stale:
            limits.append("EVIDENCE_STALE")
        if contradictions:
            limits.append(f"CONTRADICTIONS_PRESENT({len(contradictions)})")

        return BeliefEvidencePack(
            belief_id=belief.belief_id,
            subject=belief.subject,
            predicate=belief.predicate,
            status=belief.status,
            confidence=belief.confidence,
            uncertainty=belief.uncertainty,
            uncertainty_type=belief.uncertainty_type,
            is_stale=belief.is_stale,
            freshness_seconds=round(freshness_sec, 1),
            supporting_evidence_count=len(evidence_items),
            contradicting_evidence_count=len(contradictions),
            evidence_summaries=ev_summaries,
            contradiction_summaries=cntr_summaries,
            limitations=limits,
        )
