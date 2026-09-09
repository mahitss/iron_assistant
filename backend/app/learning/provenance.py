"""Strategy provenance, experience lineage, and audit tracking for Kairo Learning (Task 43)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class StrategyProvenanceRecord(BaseModel):
    """Lineage tracing how a strategy was formed, validated, and updated (Spec 18)."""

    model_config = ConfigDict(extra="ignore")

    record_id: str = Field(default_factory=lambda: f"spv_{uuid.uuid4().hex[:10]}")
    strategy_id: str
    version: int
    derived_from_experiences: list[str] = Field(default_factory=list)
    validation_experiment_id: str | None = None
    approver: str = "system"
    rationale: str = "Initial registration"
    created_at: datetime = Field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "strategy_id": self.strategy_id,
            "version": self.version,
            "derived_from_experiences": self.derived_from_experiences,
            "validation_experiment_id": self.validation_experiment_id,
            "approver": self.approver,
            "rationale": self.rationale,
            "created_at": self.created_at.isoformat(),
        }
