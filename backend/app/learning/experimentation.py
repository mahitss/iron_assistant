"""Controlled A/B canary experimentation for Kairo Learning Engine (Task 43)."""

from __future__ import annotations

import enum
import logging
import uuid
from datetime import UTC, datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger("kairo.learning.experimentation")


def utc_now() -> datetime:
    return datetime.now(UTC)


class ExperimentStatus(str, enum.Enum):
    """Lifecycle statuses of a controlled experiment (Spec 45)."""

    PLANNED = "PLANNED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


class Experiment(BaseModel):
    """A controlled A/B canary trial comparing baseline vs candidate strategy (Spec 44, 48)."""

    model_config = ConfigDict(extra="ignore")

    experiment_id: str = Field(default_factory=lambda: f"exp_{uuid.uuid4().hex[:10]}")
    name: str = Field(..., description="Descriptive name of experiment")
    domain: str = Field(default="system")
    status: ExperimentStatus = Field(default=ExperimentStatus.PLANNED)
    baseline_strategy_id: str
    candidate_strategy_id: str
    target_sample_size: int = 50
    current_sample_size: int = 0
    metrics: dict[str, Any] = Field(default_factory=lambda: {
        "baseline": {"successes": 0, "verifications": 0, "total": 0, "cost": 0.0, "latency_ms": 0.0},
        "candidate": {"successes": 0, "verifications": 0, "total": 0, "cost": 0.0, "latency_ms": 0.0},
    })
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)

    def start(self) -> None:
        self.status = ExperimentStatus.RUNNING
        self.started_at = utc_now()

    def record_trial(
        self,
        arm: str,  # "baseline" or "candidate"
        success: bool,
        verified: bool,
        latency_ms: float = 0.0,
        cost: float = 0.0,
    ) -> None:
        """Record an outcome in the designated arm."""
        if arm not in self.metrics:
            return

        m = self.metrics[arm]
        m["total"] += 1
        if success:
            m["successes"] += 1
        if verified:
            m["verifications"] += 1
        m["latency_ms"] = ((m["latency_ms"] * (m["total"] - 1)) + latency_ms) / m["total"]
        m["cost"] += cost
        self.current_sample_size += 1

        # Check completion
        if self.current_sample_size >= self.target_sample_size:
            self.status = ExperimentStatus.COMPLETED
            self.completed_at = utc_now()

    def get_comparison(self) -> dict[str, Any]:
        """Compute relative improvement or regression of candidate vs baseline."""
        b = self.metrics.get("baseline", {})
        c = self.metrics.get("candidate", {})

        b_total = max(1, b.get("total", 0))
        c_total = max(1, c.get("total", 0))

        b_verif_rate = b.get("verifications", 0) / b_total
        c_verif_rate = c.get("verifications", 0) / c_total

        return {
            "baseline_verification_rate": round(b_verif_rate, 3),
            "candidate_verification_rate": round(c_verif_rate, 3),
            "verification_improvement": round(c_verif_rate - b_verif_rate, 3),
            "is_candidate_superior": c_verif_rate >= (b_verif_rate + 0.05) and c_total >= 10,
            "has_regression": c_verif_rate < (b_verif_rate - 0.05),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "name": self.name,
            "domain": self.domain,
            "status": self.status.value if hasattr(self.status, "value") else str(self.status),
            "baseline_strategy_id": self.baseline_strategy_id,
            "candidate_strategy_id": self.candidate_strategy_id,
            "target_sample_size": self.target_sample_size,
            "current_sample_size": self.current_sample_size,
            "metrics": self.metrics,
            "comparison": self.get_comparison(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat(),
        }
