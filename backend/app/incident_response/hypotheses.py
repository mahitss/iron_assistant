"""Causal hypothesis lifecycle, evidence attachment, and conflict resolution (Task 61)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.incident_response.schemas import (
    CausalHypothesisItem,
    EvidenceItem,
    HypothesisStatus,
)

logger = logging.getLogger(__name__)


class HypothesisManager:
    """Tracks candidate causal explanations, evaluates supporting/contradictory evidence, and handles conflicts.

    Invariant 15-18: Multiple hypotheses are maintained; conflicting evidence is explicitly preserved.
    Invariant 20-21: Root cause is never forced; ROOT_CAUSE_UNKNOWN is a valid and safe diagnosis.
    """

    def initialize_hypotheses(
        self,
        raw_hypotheses: list[dict[str, Any]],
        affected_resources: list[str],
    ) -> list[CausalHypothesisItem]:
        """Convert situational awareness hypotheses into active incident hypotheses."""
        if not raw_hypotheses:
            return [
                CausalHypothesisItem(
                    hypothesis_id=f"hyp_{uuid.uuid4().hex[:8]}",
                    candidate_cause="ROOT_CAUSE_UNKNOWN",
                    status=HypothesisStatus.UNKNOWN,
                    confidence=0.2,
                    recommended_diagnostics=["Enable verbose diagnostic tracing", "Review recent node logs"],
                )
            ]

        results: list[CausalHypothesisItem] = []
        for raw in raw_hypotheses:
            cause = raw.get("candidate_cause", "ROOT_CAUSE_UNKNOWN")
            diagnostics = raw.get("recommended_diagnostics", [])
            conf = float(raw.get("confidence", 0.5))

            item = CausalHypothesisItem(
                hypothesis_id=f"hyp_{uuid.uuid4().hex[:8]}",
                candidate_cause=cause,
                status=HypothesisStatus.PROPOSED,
                confidence=conf,
                recommended_diagnostics=diagnostics,
            )
            results.append(item)

        return results

    def add_evidence(
        self,
        hypotheses: list[CausalHypothesisItem],
        hypothesis_id: str,
        evidence: EvidenceItem,
        is_supporting: bool,
    ) -> CausalHypothesisItem | None:
        """Attach supporting or contradictory evidence to a specific hypothesis and adjust status and confidence."""
        target: CausalHypothesisItem | None = None
        for h in hypotheses:
            if h.hypothesis_id == hypothesis_id:
                target = h
                break

        if not target:
            return None

        if is_supporting:
            target.evidence_supporting.append(evidence)
            # Support boost
            target.confidence = min(0.99, target.confidence + 0.15)
            if len(target.evidence_supporting) >= 2 and target.confidence >= 0.80:
                target.status = (
                    HypothesisStatus.VERIFIED if evidence.is_verified else HypothesisStatus.SUPPORTED
                )
            else:
                target.status = HypothesisStatus.SUPPORTED
        else:
            target.evidence_contradictory.append(evidence)
            # Contradiction penalty
            target.confidence = max(0.01, target.confidence - 0.25)
            if target.confidence < 0.30:
                target.status = HypothesisStatus.REJECTED
            else:
                target.status = HypothesisStatus.WEAKENED

        logger.info(
            "HYPOTHESIS_EVALUATED: id=%s cause='%s' is_sup=%s status=%s conf=%.2f",
            target.hypothesis_id,
            target.candidate_cause,
            is_supporting,
            target.status.value,
            target.confidence,
        )
        return target

    def diagnose_root_cause(
        self,
        hypotheses: list[CausalHypothesisItem],
    ) -> dict[str, Any]:
        """Synthesize current diagnoses, highlighting leading candidate or returning ROOT_CAUSE_UNKNOWN."""
        if not hypotheses:
            return {
                "leading_cause": "ROOT_CAUSE_UNKNOWN",
                "status": HypothesisStatus.UNKNOWN,
                "confidence": 0.0,
                "evidence_conflict_detected": False,
            }

        # Check for evidence conflict across hypotheses
        active_supported = [
            h for h in hypotheses if h.status in (HypothesisStatus.SUPPORTED, HypothesisStatus.VERIFIED)
        ]
        has_conflict = (
            len(active_supported) > 1
            and abs(active_supported[0].confidence - active_supported[1].confidence) < 0.15
        )

        # Sort by confidence descending
        sorted_hyps = sorted(hypotheses, key=lambda h: h.confidence, reverse=True)
        leading = sorted_hyps[0]

        if (
            leading.status in (HypothesisStatus.SUPPORTED, HypothesisStatus.VERIFIED)
            and leading.confidence >= 0.70
        ):
            return {
                "leading_cause": leading.candidate_cause,
                "hypothesis_id": leading.hypothesis_id,
                "status": leading.status,
                "confidence": leading.confidence,
                "evidence_conflict_detected": has_conflict,
                "supporting_evidence_count": len(leading.evidence_supporting),
            }

        # Invariant 21: No forced root cause when confidence is low or evidence is conflicting
        return {
            "leading_cause": "ROOT_CAUSE_UNKNOWN",
            "hypothesis_id": leading.hypothesis_id,
            "status": HypothesisStatus.UNKNOWN,
            "confidence": leading.confidence,
            "evidence_conflict_detected": has_conflict,
            "note": "Telemetry insufficient to conclusively determine root cause without further diagnostics.",
        }


hypothesis_manager = HypothesisManager()
