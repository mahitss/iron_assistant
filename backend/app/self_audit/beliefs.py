"""Belief Modeling, Metacognitive Self-Questioning, and Non-Destructive Revision (Task 67)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.self_audit.safety import block_self_preservation, sanitize_audit_text
from app.self_audit.schemas import (
    Belief,
    BeliefRevision,
    BeliefStatus,
)

logger = logging.getLogger("kairo.self_audit.beliefs")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class BeliefManager:
    """Manages internal system beliefs, metacognitive self-questioning, and revision lineages (Spec 7, 8, 9)."""

    def __init__(self) -> None:
        self._beliefs: dict[str, Belief] = {}
        self._revisions: dict[str, list[BeliefRevision]] = {}  # belief_id -> revisions

    def register_belief(
        self,
        subject: str,
        claim: str,
        basis: str,
        evidence: list[str] | None = None,
        confidence: float = 0.5,
        scope: dict[str, Any] | None = None,
        tenant_id: str = "default",
        provenance: dict[str, Any] | None = None,
    ) -> Belief:
        """Register a formal belief about system state or environment (Spec 7).

        Invariant: BELIEF != FACT.
        """
        clean_claim = sanitize_audit_text(claim)
        block_self_preservation(clean_claim)

        belief_id = f"blf_{uuid.uuid4().hex[:10]}"
        belief = Belief(
            belief_id=belief_id,
            subject=subject,
            claim=clean_claim,
            basis=basis,
            evidence=evidence or [],
            confidence=max(0.0, min(1.0, confidence)),
            scope=scope or {},
            status=BeliefStatus.ACTIVE,
            provenance=provenance or {"origin": "inference", "timestamp": _now_utc().isoformat()},
            tenant_id=tenant_id,
            timestamp=_now_utc(),
        )

        self._beliefs[belief_id] = belief
        self._revisions[belief_id] = []
        logger.info("BELIEF_REGISTERED: id=%s subject=%s confidence=%.2f", belief_id, subject, confidence)
        return belief

    def revise_belief(
        self,
        belief_id: str,
        new_claim: str,
        new_evidence: list[str],
        reason: str,
        new_confidence: float = 0.5,
        new_status: BeliefStatus = BeliefStatus.ACTIVE,
    ) -> tuple[Belief, BeliefRevision]:
        """Revise belief without destructive overwriting, preserving audit lineage (Spec 8)."""
        belief = self._beliefs.get(belief_id)
        if not belief:
            raise KeyError(f"Belief '{belief_id}' not found.")

        clean_new_claim = sanitize_audit_text(new_claim)
        block_self_preservation(clean_new_claim)

        revision = BeliefRevision(
            belief_id=belief.belief_id,
            previous_claim=belief.claim,
            new_claim=clean_new_claim,
            new_evidence=new_evidence,
            reason=reason,
            previous_confidence=belief.confidence,
            new_confidence=max(0.0, min(1.0, new_confidence)),
            new_status=new_status,
            timestamp=_now_utc(),
        )

        # Mutate active belief state with tracked revision
        belief.claim = clean_new_claim
        belief.evidence.extend([e for e in new_evidence if e not in belief.evidence])
        belief.confidence = revision.new_confidence
        belief.status = new_status
        belief.provenance["last_revised_at"] = revision.timestamp.isoformat()
        belief.provenance["revision_count"] = len(self._revisions[belief_id]) + 1

        self._revisions[belief_id].append(revision)
        logger.info("BELIEF_REVISED: id=%s reason=%s new_status=%s", belief_id, reason, new_status.value)
        return belief, revision

    def question_belief(self, belief_id: str, question: str) -> list[str]:
        """Subject a belief to structured metacognitive interrogation (Spec 9)."""
        belief = self._beliefs.get(belief_id)
        if not belief:
            raise KeyError(f"Belief '{belief_id}' not found.")

        belief.status = BeliefStatus.QUESTIONED
        metacognitive_questions = [
            f"Why does Kairo believe that '{belief.claim}'?",
            f"What empirical evidence directly supports '{belief.subject}'?",
            "What evidence would decisively contradict this conclusion?",
            f"What critical assumption is this belief founded upon ({belief.basis})?",
            "If the assumption is invalid, what is the failure blast radius?",
            f"Is confidence ({belief.confidence:.2f}) calibrated or overconfident?",
            f"Specific inquiry: {question}",
        ]
        return metacognitive_questions

    def check_contradictions(self, belief_id: str, incoming_evidence: list[str]) -> bool:
        """Evaluate whether incoming evidence directly contradicts the active belief."""
        belief = self._beliefs.get(belief_id)
        if not belief:
            return False

        claim_low = belief.claim.lower()
        for ev in incoming_evidence:
            ev_low = ev.lower()
            if "not " in ev_low or "contradicts" in ev_low or "failed" in ev_low or "false" in ev_low:
                if any(word in ev_low for word in claim_low.split() if len(word) > 4):
                    belief.status = BeliefStatus.CONTRADICTED
                    logger.warning("BELIEF_CONTRADICTED: id=%s evidence='%s'", belief_id, ev)
                    return True

        return False

    def mark_stale_beliefs(self, max_age_hours: float = 72.0) -> list[str]:
        """Identify beliefs that have not been re-evaluated within the time threshold (Spec 7)."""
        now = _now_utc()
        stale_ids: list[str] = []
        for b_id, belief in self._beliefs.items():
            if belief.status == BeliefStatus.ACTIVE:
                age_h = (now - belief.timestamp).total_seconds() / 3600.0
                if age_h > max_age_hours:
                    belief.status = BeliefStatus.STALE
                    stale_ids.append(b_id)
        return stale_ids

    def get_belief(self, belief_id: str) -> Belief | None:
        return self._beliefs.get(belief_id)

    def list_beliefs(self, tenant_id: str = "default") -> list[Belief]:
        return [b for b in self._beliefs.values() if b.tenant_id == tenant_id]

    def get_revisions(self, belief_id: str) -> list[BeliefRevision]:
        return self._revisions.get(belief_id, [])
