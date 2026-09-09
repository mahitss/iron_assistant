"""Confidence, uncertainty quantification, and evidence assessment for Kairo Cognitive Planning (Task 41).

Core Invariant (Spec 58): Confidence is NOT authority.
High confidence does not bypass policy, authorization, or approval gates.
"""

from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class ConfidenceLevel(str, Enum):
    """Calibrated confidence tier derived from evidence quality."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class EvidenceAssessment(BaseModel):
    """Structured assessment of evidence grounding a plan or decision."""

    model_config = ConfigDict(extra="ignore")

    confidence: ConfidenceLevel = Field(default=ConfidenceLevel.MEDIUM)
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence_sources: list[str] = Field(default_factory=list, description="IDs or URIs of verified observations/documents")
    has_unverified_assumptions: bool = Field(default=False)
    uncertainty_notes: str | None = Field(default=None)

    @classmethod
    def evaluate(
        cls,
        evidence_sources: list[str],
        unverified_assumptions_count: int = 0,
        known_state_fresh: bool = True,
    ) -> "EvidenceAssessment":
        """Deterministic computation of confidence based on evidence grounding."""
        score = 0.5
        if evidence_sources:
            score += min(0.3, len(evidence_sources) * 0.1)
        if known_state_fresh:
            score += 0.2
        if unverified_assumptions_count > 0:
            score -= min(0.4, unverified_assumptions_count * 0.15)

        score = max(0.0, min(1.0, score))

        if score >= 0.75 and unverified_assumptions_count == 0:
            level = ConfidenceLevel.HIGH
        elif score >= 0.45:
            level = ConfidenceLevel.MEDIUM
        else:
            level = ConfidenceLevel.LOW

        return cls(
            confidence=level,
            confidence_score=round(score, 2),
            evidence_sources=evidence_sources,
            has_unverified_assumptions=unverified_assumptions_count > 0,
            uncertainty_notes=f"Grounding score {score:.2f} with {len(evidence_sources)} sources and {unverified_assumptions_count} unverified assumptions.",
        )
