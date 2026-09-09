"""Experience domain models, ExperienceTypes, and quality weighting for Kairo Learning Engine (Task 43)."""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from app.security.redaction import ArgumentSanitizer


def utc_now() -> datetime:
    return datetime.now(UTC)


class ExperienceType(str, enum.Enum):
    """Authoritative classifications of task execution experiences (Spec 3)."""

    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILURE = "FAILURE"
    UNKNOWN = "UNKNOWN"
    RECOVERY_SUCCESS = "RECOVERY_SUCCESS"
    RECOVERY_FAILURE = "RECOVERY_FAILURE"
    USER_CORRECTION = "USER_CORRECTION"
    VERIFICATION_FAILURE = "VERIFICATION_FAILURE"
    PLAN_FAILURE = "PLAN_FAILURE"
    TOOL_FAILURE = "TOOL_FAILURE"
    MODEL_FAILURE = "MODEL_FAILURE"
    RETRIEVAL_FAILURE = "RETRIEVAL_FAILURE"


class Experience(BaseModel):
    """An empirical record of a verified or attempted task execution (Spec 2)."""

    model_config = ConfigDict(extra="ignore")

    experience_id: str = Field(default_factory=lambda: f"exp_{uuid.uuid4().hex[:12]}")
    task_id: str | None = None
    goal_type: str = "GENERAL"
    plan_type: str | None = None
    strategy: str = Field(..., description="Strategy or workflow name used")
    context_reference: str | None = None
    actions: list[Any] = Field(default_factory=list)
    observations: list[Any] = Field(default_factory=list)
    verification_result: dict[str, Any] | None = Field(default_factory=dict)
    outcome: ExperienceType = Field(default=ExperienceType.UNKNOWN)
    duration_ms: float = 0.0
    cost: float = 0.0
    retries: int = 0
    failures: list[dict[str, Any]] = Field(default_factory=list)
    scope: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)

    def model_post_init(self, __context: Any) -> None:
        if self.verification_result is None:
            self.verification_result = {}
        self.sanitize_payloads()

    def calculate_learning_weight(self) -> float:
        """Compute the learning weight of this experience (Spec 4, 5).
        
        Only verified outcomes receive strong learning weight.
        UNKNOWN or unverified outcomes produce 0.0 or weak weight.
        """
        vr = self.verification_result or {}
        is_verified = vr.get("status") == "PASS" or vr.get("is_verified") is True

        if not is_verified and self.outcome in [ExperienceType.SUCCESS, ExperienceType.PARTIAL_SUCCESS]:
            # False success or unverified success gets zero positive learning weight
            return 0.05
        elif is_verified and self.outcome == ExperienceType.SUCCESS:
            return 1.0
        elif self.outcome in [ExperienceType.VERIFICATION_FAILURE, ExperienceType.FAILURE, ExperienceType.PLAN_FAILURE]:
            return 0.95  # Strong negative learning weight
        elif self.outcome == ExperienceType.USER_CORRECTION:
            return 1.0   # User corrections have maximum weight
        elif self.outcome == ExperienceType.UNKNOWN:
            return 0.0   # Never learn "strategy works" from unknown outcome
        return 0.5

    def sanitize_payloads(self) -> Experience:
        """Recursively redact secrets and credentials from actions and observations."""
        self.actions = ArgumentSanitizer.sanitize(self.actions)
        self.observations = ArgumentSanitizer.sanitize(self.observations)
        self.failures = ArgumentSanitizer.sanitize(self.failures)
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "experience_id": self.experience_id,
            "task_id": self.task_id,
            "goal_type": self.goal_type,
            "plan_type": self.plan_type,
            "strategy": self.strategy,
            "context_reference": self.context_reference,
            "actions": self.actions,
            "observations": self.observations,
            "verification_result": self.verification_result,
            "outcome": self.outcome.value if hasattr(self.outcome, "value") else str(self.outcome),
            "duration_ms": round(self.duration_ms, 2),
            "cost": round(self.cost, 4),
            "retries": self.retries,
            "failures": self.failures,
            "scope": self.scope,
            "learning_weight": round(self.calculate_learning_weight(), 3),
            "created_at": self.created_at.isoformat(),
        }
