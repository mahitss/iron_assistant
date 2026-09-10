"""Causal Hypothesis modeling and lifecycle tracking (Task 55, Prompts #11, #12)."""

from __future__ import annotations

import uuid

from app.causal.schemas import (
    CausalEvidence,
    CausalHypothesis,
    HypothesisStatus,
)


class HypothesisManager:
    """Manages creation, evidence binding, and status transitions of causal hypotheses."""

    @staticmethod
    def create_hypothesis(
        cause: str,
        effect: str,
        mechanism: str,
        evidence: list[CausalEvidence] | None = None,
        alternatives: list[str] | None = None,
        confidence: float = 0.5,
        status: HypothesisStatus = HypothesisStatus.PROPOSED,
    ) -> CausalHypothesis:
        hid = f"chyp_{uuid.uuid4().hex[:10]}"
        return CausalHypothesis(
            hypothesis_id=hid,
            cause=cause,
            effect=effect,
            mechanism=mechanism,
            evidence=evidence or [],
            alternatives=alternatives or [],
            confidence=round(max(0.0, min(1.0, confidence)), 2),
            status=status,
        )

    @staticmethod
    def attach_evidence(hypothesis: CausalHypothesis, evidence: CausalEvidence) -> CausalHypothesis:
        hypothesis.evidence.append(evidence)
        return hypothesis

    @staticmethod
    def update_status(hypothesis: CausalHypothesis, new_status: HypothesisStatus) -> CausalHypothesis:
        hypothesis.status = new_status
        return hypothesis


CausalHypothesisManager = HypothesisManager

