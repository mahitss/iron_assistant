"""Failure pattern clustering and signature models for Kairo Learning Engine (Task 43)."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class FailurePattern(BaseModel):
    """Identified cluster of recurring failures with known mitigation (Spec 34)."""

    model_config = ConfigDict(extra="ignore")

    pattern_id: str = Field(default_factory=lambda: f"pat_{uuid.uuid4().hex[:10]}")
    domain: str = Field(default="system")
    signature: str = Field(..., description="Normalized error signature or regex pattern")
    frequency: int = Field(default=1, ge=1)
    affected_components: list[str] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    mitigation: str = Field(..., description="Recommended mitigation or safe recovery path")
    confidence: str = "MEDIUM"  # LOW, MEDIUM, HIGH
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def record_occurrence(self, component: str | None = None, evidence_item: dict[str, Any] | None = None) -> None:
        """Record a new observation of this failure pattern."""
        self.frequency += 1
        if component and component not in self.affected_components:
            self.affected_components.append(component)
        if evidence_item:
            self.evidence.append(evidence_item)
            if len(self.evidence) > 20:
                self.evidence.pop(0)  # Bound evidence retention

        # Adjust confidence based on frequency
        if self.frequency >= 5:
            self.confidence = "HIGH"
        elif self.frequency >= 2:
            self.confidence = "MEDIUM"
        else:
            self.confidence = "LOW"

        self.updated_at = utc_now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "domain": self.domain,
            "signature": self.signature,
            "frequency": self.frequency,
            "affected_components": self.affected_components,
            "evidence_count": len(self.evidence),
            "mitigation": self.mitigation,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class PatternClusterer:
    """Clusters error messages into common failure pattern signatures (Spec 35)."""

    @staticmethod
    def extract_signature(error_message: str) -> str:
        """Normalize error message to extract deterministic pattern signature.
        
        Removes variable hashes, timestamps, IDs, and IP addresses.
        """
        clean = error_message.strip().lower()
        # Remove UUIDs
        clean = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "<uuid>", clean)
        # Remove IPs
        clean = re.sub(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "<ip>", clean)
        # Remove numeric IDs
        clean = re.sub(r"\b\d{4,}\b", "<id>", clean)
        # Truncate length
        return clean[:120].strip()
