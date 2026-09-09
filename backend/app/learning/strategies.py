"""Strategy models, lifecycle statuses, and provenance tracking for Kairo Learning Engine (Task 43)."""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class StrategyStatus(str, enum.Enum):
    """Lifecycle states of an execution or planning strategy (Spec 14)."""

    CANDIDATE = "CANDIDATE"          # Proposed improvement under evaluation
    EXPERIMENTAL = "EXPERIMENTAL"    # Running in controlled canary or sandbox
    ACTIVE = "ACTIVE"                # Promoted for production planning/execution
    DEPRECATED = "DEPRECATED"        # Outdated or superseded by a newer version
    BLOCKED = "BLOCKED"              # Prohibited due to safety/policy violations
    ROLLED_BACK = "ROLLED_BACK"      # Demoted following detected regressions


class Strategy(BaseModel):
    """An execution or planning strategy supported by empirical evidence (Spec 13)."""

    model_config = ConfigDict(extra="ignore")

    strategy_id: str = Field(default_factory=lambda: f"strat_{uuid.uuid4().hex[:10]}")
    domain: str = Field(..., description="Scope domain: coding, deployment, research, browser, etc.")
    description: str = Field(..., description="Clear explanation of strategy mechanics")
    version: int = Field(default=1, ge=1)
    prerequisites: list[str] = Field(default_factory=list)
    expected_outcome: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    failure_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    verification_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    latency_ms: float = 0.0
    cost: float = 0.0
    confidence: str = "MEDIUM"  # LOW, MEDIUM, HIGH
    status: StrategyStatus = Field(default=StrategyStatus.CANDIDATE)
    scope: dict[str, Any] = Field(default_factory=dict)
    sample_size: int = 0
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def record_execution(
        self,
        was_successful: bool,
        was_verified: bool,
        duration_ms: float = 0.0,
        cost: float = 0.0,
    ) -> None:
        """Update empirical metrics upon a new verified task outcome."""
        n = self.sample_size
        new_n = n + 1
        self.sample_size = new_n

        # Incremental moving average
        self.success_rate = ((self.success_rate * n) + (1.0 if was_successful else 0.0)) / new_n
        self.failure_rate = 1.0 - self.success_rate
        self.verification_rate = ((self.verification_rate * n) + (1.0 if was_verified else 0.0)) / new_n
        self.latency_ms = ((self.latency_ms * n) + duration_ms) / new_n
        self.cost = ((self.cost * n) + cost) / new_n
        self.updated_at = utc_now()

        # Update confidence based on sample size and verification rate
        if new_n >= 30 and self.verification_rate >= 0.85:
            self.confidence = "HIGH"
        elif new_n >= 10:
            self.confidence = "MEDIUM"
        else:
            self.confidence = "LOW"

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "domain": self.domain,
            "description": self.description,
            "version": self.version,
            "prerequisites": self.prerequisites,
            "expected_outcome": self.expected_outcome,
            "evidence": self.evidence,
            "success_rate": round(self.success_rate, 3),
            "failure_rate": round(self.failure_rate, 3),
            "verification_rate": round(self.verification_rate, 3),
            "latency_ms": round(self.latency_ms, 2),
            "cost": round(self.cost, 4),
            "confidence": self.confidence,
            "status": self.status.value if hasattr(self.status, "value") else str(self.status),
            "scope": self.scope,
            "sample_size": self.sample_size,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
