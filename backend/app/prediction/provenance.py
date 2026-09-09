"""Prediction Provenance, Model Versioning, Feature Snapshots, and Multi-Agent Review (Task 47)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger("kairo.prediction.provenance")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ReviewAssessment:
    """Independent multi-agent evaluation of a high-impact prediction (Spec 128-131)."""

    reviewer_agent_id: str
    is_supported: bool = True
    evidence_quality_score: float = 0.8  # 0.0 to 1.0
    alternative_scenario: Optional[str] = None
    notes: str = ""
    assessment: str = "EVIDENCE_VALID"
    critique: str = ""
    timestamp: datetime = field(default_factory=utc_now)


@dataclass
class PredictionProvenanceRecord:
    """Full lineage record supporting auditability and reproducibility (Spec 13, 172, 180, 181)."""

    prediction_id: str
    model_reference: str
    model_version: str
    feature_snapshot: Dict[str, Any]
    evidence_ids: List[str]
    created_at: datetime = field(default_factory=utc_now)
    reviews: List[ReviewAssessment] = field(default_factory=list)

    def add_review(
        self,
        reviewer_agent_id: str,
        is_supported: bool = True,
        evidence_quality: float = 0.8,
        alternative: Optional[str] = None,
        notes: str = "",
        assessment: str = "EVIDENCE_VALID",
        critique: str = "",
    ) -> ReviewAssessment:
        """Enforce Spec 128-131: Record independent agent review."""
        rev = ReviewAssessment(
            reviewer_agent_id=reviewer_agent_id,
            is_supported=is_supported,
            evidence_quality_score=evidence_quality,
            alternative_scenario=alternative,
            notes=notes or critique,
            assessment=assessment,
            critique=critique or notes,
        )
        self.reviews.append(rev)
        logger.info("Recorded review on %s by %s: assessment=%s", self.prediction_id, reviewer_agent_id, assessment)
        return rev


class ProvenanceLedger:
    """Registry maintaining full reproducibility metadata for predictions."""

    def __init__(self) -> None:
        # prediction_id -> PredictionProvenanceRecord
        self._records: Dict[str, PredictionProvenanceRecord] = {}

    def record_provenance(
        self,
        prediction_id: str,
        model_ref: str,
        model_ver: str,
        features: Dict[str, Any],
        evidence_ids: List[str],
    ) -> PredictionProvenanceRecord:
        rec = PredictionProvenanceRecord(
            prediction_id=prediction_id,
            model_reference=model_ref,
            model_version=model_ver,
            feature_snapshot=features,
            evidence_ids=evidence_ids,
        )
        self._records[prediction_id] = rec
        return rec

    def get_provenance(self, prediction_id: str) -> Optional[PredictionProvenanceRecord]:
        return self._records.get(prediction_id)
