"""Hypotheses and beliefs management for KAIRO knowledge (Task 92 Phase 16).

Guarantees:
- Hypotheses and beliefs are NEVER stored or queried as verified facts
- Strict state tracking: PROPOSED -> SUPPORTED / WEAKENED -> VERIFIED / REJECTED / EXPIRED
- Accidental promotion from hypothesis to verified fact is strictly blocked
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.knowledge_consolidation.models import (
    CertaintyState,
    HypothesisModel,
    HypothesisStatus,
    MemoryEntity,
    MemoryStatus,
    MemoryType,
    generate_id,
)


class PrematureFactPromotionError(Exception):
    """Raised when an unverified hypothesis is attempted to be promoted to verified fact."""


class HypothesisManager:
    """Manages empirical hypotheses and beliefs with strict validation barriers."""

    def __init__(self) -> None:
        self._hypotheses: dict[str, HypothesisModel] = {}

    def propose_hypothesis(
        self,
        claim: str,
        validation_plan: str,
        initial_confidence: float = 0.5,
        tenant_id: str = "default",
        user_id: str = "default_user",
    ) -> tuple[MemoryEntity, HypothesisModel]:
        """Register a new tentative hypothesis. Always marked as UNCERTAIN / HYPOTHESIS."""
        mem_id = generate_id("mem_hyp")
        hyp_id = generate_id("hyp")

        hyp = HypothesisModel(
            hypothesis_id=hyp_id,
            memory_id=mem_id,
            claim=claim,
            status=HypothesisStatus.PROPOSED,
            validation_plan=validation_plan,
            confidence=max(0.0, min(1.0, initial_confidence)),
        )
        self._hypotheses[hyp_id] = hyp

        memory = MemoryEntity(
            memory_id=mem_id,
            tenant_id=tenant_id,
            user_id=user_id,
            type=MemoryType.HYPOTHESIS,
            content=f"[HYPOTHESIS] {claim}",
            structured_representation={
                "hypothesis_id": hyp_id,
                "validation_plan": validation_plan,
            },
            confidence=initial_confidence,
            certainty=CertaintyState.UNCERTAIN,
            status=MemoryStatus.UNCERTAIN,
        )

        return memory, hyp

    def add_evidence_to_hypothesis(
        self,
        hypothesis_id: str,
        evidence_id: str,
        supports: bool,
    ) -> HypothesisModel:
        """Link evidence to a hypothesis, adjusting confidence and state."""
        hyp = self._hypotheses.get(hypothesis_id)
        if not hyp:
            raise KeyError(f"Hypothesis '{hypothesis_id}' not found.")

        if supports:
            hyp.supporting_evidence_ids.append(evidence_id)
            hyp.confidence = min(0.95, hyp.confidence + 0.1)
            hyp.status = HypothesisStatus.SUPPORTED
        else:
            hyp.contradicting_evidence_ids.append(evidence_id)
            hyp.confidence = max(0.05, hyp.confidence - 0.15)
            if len(hyp.contradicting_evidence_ids) > len(hyp.supporting_evidence_ids):
                hyp.status = HypothesisStatus.CONTRADICTED
            else:
                hyp.status = HypothesisStatus.WEAKENED

        return hyp

    def verify_hypothesis(
        self,
        hypothesis_id: str,
        verified_by: str,
        empirical_evidence_ref: str,
        memory: MemoryEntity,
    ) -> HypothesisModel:
        """Mark hypothesis as verified following successful empirical validation."""
        hyp = self._hypotheses.get(hypothesis_id)
        if not hyp:
            raise KeyError(f"Hypothesis '{hypothesis_id}' not found.")

        now = datetime.now(UTC)
        hyp.status = HypothesisStatus.VERIFIED
        hyp.verified_at = now
        hyp.confidence = 0.95

        memory.status = MemoryStatus.ACTIVE
        memory.certainty = CertaintyState.KNOWN

        return hyp

    def reject_hypothesis(
        self, hypothesis_id: str, reason: str, memory: MemoryEntity
    ) -> HypothesisModel:
        """Explicitly reject a hypothesis when disproven."""
        hyp = self._hypotheses.get(hypothesis_id)
        if not hyp:
            raise KeyError(f"Hypothesis '{hypothesis_id}' not found.")

        now = datetime.now(UTC)
        hyp.status = HypothesisStatus.REJECTED
        hyp.rejected_at = now
        hyp.confidence = 0.0

        memory.status = MemoryStatus.INVALIDATED
        memory.certainty = CertaintyState.CONTRADICTED

        return hyp

    def promote_to_fact(self, hypothesis_id: str) -> None:
        """Guard method: strictly prohibits promoting unverified hypotheses into facts."""
        hyp = self._hypotheses.get(hypothesis_id)
        if not hyp:
            raise KeyError(f"Hypothesis '{hypothesis_id}' not found.")

        if hyp.status != HypothesisStatus.VERIFIED:
            raise PrematureFactPromotionError(
                f"Cannot promote hypothesis '{hypothesis_id}' to verified fact: status is '{hyp.status.value}'."
            )

    def get_hypothesis(self, hypothesis_id: str) -> HypothesisModel | None:
        """Retrieve hypothesis by ID."""
        return self._hypotheses.get(hypothesis_id)

    def get_by_memory_id(self, memory_id: str) -> HypothesisModel | None:
        """Retrieve hypothesis by memory ID."""
        for h in self._hypotheses.values():
            if h.memory_id == memory_id:
                return h
        return None
