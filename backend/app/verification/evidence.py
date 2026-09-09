"""Evidence domain models, 15 EvidenceTypes, reliability scoring, and source independence rules (Task 42)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class EvidenceType(str, Enum):
    """Authoritative source categories of empirical evidence (Spec 14)."""

    DIRECT_OBSERVATION = "DIRECT_OBSERVATION"
    TOOL_RESULT = "TOOL_RESULT"
    DATABASE_STATE = "DATABASE_STATE"
    API_RESPONSE = "API_RESPONSE"
    TEST_RESULT = "TEST_RESULT"
    FILE_CONTENT = "FILE_CONTENT"
    GIT_STATE = "GIT_STATE"
    DEPLOYMENT_STATE = "DEPLOYMENT_STATE"
    HEALTH_CHECK = "HEALTH_CHECK"
    USER_INPUT = "USER_INPUT"
    DOCUMENT = "DOCUMENT"
    WEB_SOURCE = "WEB_SOURCE"
    MEMORY_REFERENCE = "MEMORY_REFERENCE"
    WORLD_MODEL = "WORLD_MODEL"
    MODEL_INFERENCE = "MODEL_INFERENCE"


class Evidence(BaseModel):
    """An empirical observation or artifact supporting or refuting claims (Spec 13)."""

    model_config = ConfigDict(extra="ignore")

    evidence_id: str = Field(default_factory=lambda: f"evd_{uuid.uuid4().hex[:12]}")
    user_id: str = "default_user"
    project_id: str | None = None
    source_type: EvidenceType
    source_reference: str = Field(..., description="URI, tool name, commit SHA, endpoint, or document ID")
    observation: dict[str, Any] = Field(default_factory=dict, description="Structured factual payload")
    observed_at: datetime = Field(default_factory=utc_now)
    retrieved_at: datetime = Field(default_factory=utc_now)
    provenance: str = Field(default="system", description="Origin pipeline or actor")
    reliability: float = Field(default=0.8, ge=0.0, le=1.0)
    freshness_seconds: float = Field(default=300.0, description="Validity TTL in seconds")
    checksum: str | None = Field(default=None, description="Cryptographic SHA256 or hash where applicable")
    scope: dict[str, Any] = Field(default_factory=dict)

    def is_fresh(self, as_of: datetime | None = None) -> bool:
        """Check if this evidence is within its freshness window."""
        ref_time = as_of or utc_now()
        age = (ref_time - self.observed_at).total_seconds()
        return age <= self.freshness_seconds

    def calculate_reliability(self) -> float:
        """Calculate source-specific reliability score (Spec 15)."""
        return self.compute_default_reliability(self.source_type)

    def freshness_score(self, as_of: datetime | None = None) -> float:
        """Calculate decay score between 0.0 and 1.0."""
        ref_time = as_of or utc_now()
        age = max(0.0, (ref_time - self.observed_at).total_seconds())
        if self.freshness_seconds <= 0:
            return 0.0
        return max(0.0, min(1.0, 1.0 - (age / self.freshness_seconds)))

    @classmethod
    def compute_default_reliability(cls, source_type: EvidenceType) -> float:
        """Domain-specific baseline reliability tiers (Spec 15)."""
        tier_map = {
            EvidenceType.HEALTH_CHECK: 0.95,
            EvidenceType.DATABASE_STATE: 0.95,
            EvidenceType.DIRECT_OBSERVATION: 0.95,
            EvidenceType.TEST_RESULT: 0.90,
            EvidenceType.GIT_STATE: 0.90,
            EvidenceType.DEPLOYMENT_STATE: 0.90,
            EvidenceType.FILE_CONTENT: 0.85,
            EvidenceType.API_RESPONSE: 0.80,
            EvidenceType.TOOL_RESULT: 0.75,
            EvidenceType.WORLD_MODEL: 0.75,
            EvidenceType.DOCUMENT: 0.70,
            EvidenceType.USER_INPUT: 0.60,
            EvidenceType.WEB_SOURCE: 0.50,
            EvidenceType.MEMORY_REFERENCE: 0.50,
            EvidenceType.MODEL_INFERENCE: 0.30,  # Model claims are lowest initial reliability
        }
        return tier_map.get(source_type, 0.5)

    @classmethod
    def are_sources_independent(cls, ev1: "Evidence", ev2: "Evidence") -> bool:
        """Enforce Same-Source Limitation (Spec 19):
        Repeated assertions from the same model, tool, or endpoint do NOT constitute independent verification.
        """
        if ev1.source_type == EvidenceType.MODEL_INFERENCE and ev2.source_type == EvidenceType.MODEL_INFERENCE:
            return False
        if ev1.source_reference == ev2.source_reference and ev1.source_type == ev2.source_type:
            return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "source_type": self.source_type.value,
            "source_reference": self.source_reference,
            "observation": self.observation,
            "observed_at": self.observed_at.isoformat(),
            "retrieved_at": self.retrieved_at.isoformat(),
            "provenance": self.provenance,
            "reliability": self.calculate_reliability(),
            "freshness_seconds": self.freshness_seconds,
            "checksum": self.checksum,
            "scope": self.scope,
        }
