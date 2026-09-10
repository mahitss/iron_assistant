"""Uncertainty modeling, aggregation, and anti-false-certainty controls (INVARIANTS 24, 25, 31, 102)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
import uuid

from app.metacognition.schemas import UncertaintySchema, UncertaintyType


class UncertaintyModel:
    """Manages explicit operational uncertainty states across data, models, and environments."""

    def __init__(self) -> None:
        # subject (lower) -> list of UncertaintySchema
        self._uncertainties: Dict[str, List[UncertaintySchema]] = {}

    def record_uncertainty(
        self,
        subject: str,
        uncertainty_type: UncertaintyType,
        confidence: float = 0.5,
        evidence: Optional[List[Dict[str, Any]]] = None,
        impact: str = "MEDIUM",
    ) -> UncertaintySchema:
        """INVARIANT 31: Explicitly tracks uncertainty; never converts uncertainty to certainty."""
        sub_key = subject.strip().lower()
        rec = UncertaintySchema(
            subject=subject.strip(),
            uncertainty_type=uncertainty_type,
            confidence=min(max(confidence, 0.0), 0.7),  # Uncertainty cannot have high confidence
            evidence=evidence or [],
            impact=impact,
            resolution_status="UNRESOLVED",
            identified_at=datetime.now(UTC),
        )
        self._uncertainties.setdefault(sub_key, []).append(rec)
        return rec

    def get_uncertainties(self, subject: Optional[str] = None) -> List[UncertaintySchema]:
        if subject:
            return self._uncertainties.get(subject.strip().lower(), [])
        all_recs = []
        for recs in self._uncertainties.values():
            all_recs.extend(recs)
        return all_recs

    def aggregate_agent_uncertainty(
        self,
        topic: str,
        agent_opinions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """INVARIANT 101 & 102: Multi-agent consistency: does not hide disagreement or treat consensus as proof."""
        if not agent_opinions:
            return {"topic": topic, "status": "NO_OPINIONS", "consensus": False, "uncertainty_score": 1.0}

        distinct_answers = set(str(op.get("answer", "")).strip().lower() for op in agent_opinions)
        has_disagreement = len(distinct_answers) > 1

        if has_disagreement:
            self.record_uncertainty(
                subject=topic,
                uncertainty_type=UncertaintyType.CONFLICTING_DATA,
                confidence=0.4,
                evidence=agent_opinions,
                impact="HIGH",
            )

        return {
            "topic": topic,
            "has_disagreement": has_disagreement,
            "distinct_answers_count": len(distinct_answers),
            "opinions": agent_opinions,
            "aggregate_confidence": 0.45 if has_disagreement else 0.85,
        }

    def resolve_uncertainty(self, subject: str, resolution_evidence: str) -> None:
        sub_key = subject.strip().lower()
        if sub_key in self._uncertainties:
            for u in self._uncertainties[sub_key]:
                u.resolution_status = "RESOLVED"
                u.evidence.append({"resolution": resolution_evidence, "timestamp": datetime.now(UTC).isoformat()})
