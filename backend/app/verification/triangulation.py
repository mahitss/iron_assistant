"""Source Triangulation & Cross-Verification Engine for Kairo (Task 42).

Provides multi-source cross-referencing, source independence checks,
agreement scoring, and divergence detection to prevent single-source bias
or model hallucination.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.verification.claims import Claim, TruthStatus
from app.verification.evidence import Evidence, EvidenceType

logger = logging.getLogger("kairo.verification.triangulation")


@dataclass
class TriangulationResult:
    """Outcome of triangulating evidence across multiple sources."""

    claim_id: str
    num_sources: int
    num_independent_sources: int
    agreement_ratio: float  # 0.0 to 1.0
    is_corroborated: bool
    status: TruthStatus
    discrepancies: list[str] = field(default_factory=list)
    participating_evidence_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "num_sources": self.num_sources,
            "num_independent_sources": self.num_independent_sources,
            "agreement_ratio": round(self.agreement_ratio, 3),
            "is_corroborated": self.is_corroborated,
            "status": self.status.value,
            "discrepancies": self.discrepancies,
            "participating_evidence_ids": self.participating_evidence_ids,
            "metadata": self.metadata,
            "checked_at": self.checked_at.isoformat(),
        }


class SourceTriangulator:
    """Triangulates facts and claims across independent observations and sources."""

    def __init__(self, min_independent_sources: int = 2, agreement_threshold: float = 0.66) -> None:
        self.min_independent_sources = min_independent_sources
        self.agreement_threshold = agreement_threshold

    @staticmethod
    def extract_distinct_source_origins(evidences: list[Evidence]) -> set[str]:
        """Extract set of truly independent source origins.
        
        Guards against same-source duplication (e.g. model repeating itself,
        same API endpoint called repeatedly, or same tool reporting twice).
        """
        origins = set()
        for ev in evidences:
            origin_key = f"{ev.source_type.value}:{ev.source_reference}"
            origins.add(origin_key)
        return origins

    def triangulate(self, claim: Claim, evidences: list[Evidence]) -> TriangulationResult:
        """Triangulate a claim against a collection of provided evidence pieces."""
        if not evidences:
            return TriangulationResult(
                claim_id=claim.claim_id,
                num_sources=0,
                num_independent_sources=0,
                agreement_ratio=0.0,
                is_corroborated=False,
                status=TruthStatus.UNVERIFIED,
                discrepancies=["No evidence provided for triangulation"],
                participating_evidence_ids=[],
            )

        unique_origins = self.extract_distinct_source_origins(evidences)
        num_independent = len(unique_origins)

        # Check for same-source limitation (Spec 19)
        # If all evidence comes from MODEL_INFERENCE or a single source, independence is 1
        supporting_evidences: list[Evidence] = []
        conflicting_evidences: list[Evidence] = []
        discrepancies: list[str] = []

        for ev in evidences:
            # Check reliability and content match
            obs = ev.observation
            ev_status = str(obs.get("status", "")).lower() if isinstance(obs, dict) else ""
            ev_value = obs.get("value") if isinstance(obs, dict) else str(obs)

            # Evaluate agreement with claim object/reference or truth
            claim_target = str(claim.object_ref).strip().lower() if claim.object_ref else ""
            
            # If observation signals failure/mismatch
            if ev_status in ["failed", "error", "down", "stopped", "mismatch"] and claim_target in ["ok", "success", "running", "healthy", "true"]:
                conflicting_evidences.append(ev)
                discrepancies.append(
                    f"Evidence {ev.evidence_id} ({ev.source_type.value}) reports conflict: {obs}"
                )
            elif ev_status in ["success", "ok", "healthy", "running", "true", "active"]:
                supporting_evidences.append(ev)
            elif claim_target and str(ev_value).strip().lower() == claim_target:
                supporting_evidences.append(ev)
            elif claim_target and str(ev_value).strip().lower() != claim_target and ev_value is not None:
                conflicting_evidences.append(ev)
                discrepancies.append(
                    f"Evidence {ev.evidence_id} expected '{claim_target}' but observed '{ev_value}'"
                )
            else:
                # Neutral or partially supporting
                supporting_evidences.append(ev)

        total_evaluated = len(supporting_evidences) + len(conflicting_evidences)
        agreement_ratio = (len(supporting_evidences) / total_evaluated) if total_evaluated > 0 else 0.0

        # Determine truth status under triangulation
        # Spec 34: If sources disagree: mark CONTRADICTED or UNKNOWN, never silently choose preferred answer
        if conflicting_evidences and supporting_evidences:
            if len(conflicting_evidences) >= len(supporting_evidences):
                status = TruthStatus.CONTRADICTED
            else:
                # Sources disagree with mixed weight
                status = TruthStatus.CONTRADICTED if agreement_ratio < self.agreement_threshold else TruthStatus.SUPPORTED
        elif conflicting_evidences and not supporting_evidences:
            status = TruthStatus.CONTRADICTED
        elif num_independent >= self.min_independent_sources and agreement_ratio >= self.agreement_threshold:
            status = TruthStatus.VERIFIED
        elif supporting_evidences:
            # Supported by single or dependent source, but not independently verified
            status = TruthStatus.SUPPORTED
        else:
            status = TruthStatus.UNKNOWN

        is_corroborated = (
            num_independent >= self.min_independent_sources
            and agreement_ratio >= self.agreement_threshold
            and not conflicting_evidences
        )

        return TriangulationResult(
            claim_id=claim.claim_id,
            num_sources=len(evidences),
            num_independent_sources=num_independent,
            agreement_ratio=agreement_ratio,
            is_corroborated=is_corroborated,
            status=status,
            discrepancies=discrepancies,
            participating_evidence_ids=[ev.evidence_id for ev in evidences],
            metadata={
                "supporting_count": len(supporting_evidences),
                "conflicting_count": len(conflicting_evidences),
                "unique_origins": list(unique_origins),
            },
        )
