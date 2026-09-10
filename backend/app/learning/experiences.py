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
    """An empirical record of a verified or attempted task execution (Task 43 & Task 52)."""

    model_config = ConfigDict(extra="ignore")

    experience_id: str = Field(default_factory=lambda: f"exp_{uuid.uuid4().hex[:12]}")
    task_id: str | None = None
    intent_id: str | None = None
    goal_id: str | None = None
    goal_type: str = "GENERAL"
    plan_type: str | None = None
    strategy: str = "default"
    context_reference: str | None = None
    context_refs: list[str] = Field(default_factory=list)
    actions: list[Any] = Field(default_factory=list)
    observations: list[Any] = Field(default_factory=list)
    verification_result: dict[str, Any] | None = Field(default_factory=dict)
    verification: dict[str, Any] = Field(default_factory=dict)
    outcome: Any = Field(default=ExperienceType.UNKNOWN)
    duration_ms: float = 0.0
    cost: float = 0.0
    retries: int = 0
    failures: list[dict[str, Any]] = Field(default_factory=list)
    scope: dict[str, Any] = Field(default_factory=dict)
    environment: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    privacy_scope: str = "PROJECT"
    status: str = "RAW"
    source: str = "SYSTEM"
    created_at: datetime = Field(default_factory=utc_now)
    timestamp: datetime = Field(default_factory=utc_now)

    def model_post_init(self, __context: Any) -> None:
        if self.verification_result is None:
            self.verification_result = {}
        if not self.verification and self.verification_result:
            self.verification = dict(self.verification_result)
        elif self.verification and not self.verification_result:
            self.verification_result = dict(self.verification)
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
            "intent_id": self.intent_id,
            "goal_id": self.goal_id,
            "goal_type": self.goal_type,
            "plan_type": self.plan_type,
            "strategy": self.strategy,
            "context_reference": self.context_reference,
            "context_refs": self.context_refs,
            "actions": self.actions,
            "observations": self.observations,
            "verification_result": self.verification_result,
            "verification": self.verification,
            "outcome": self.outcome.value if hasattr(self.outcome, "value") else str(self.outcome),
            "duration_ms": round(self.duration_ms, 2),
            "cost": round(self.cost, 4),
            "retries": self.retries,
            "failures": self.failures,
            "scope": self.scope,
            "environment": self.environment,
            "provenance": self.provenance,
            "privacy_scope": self.privacy_scope,
            "status": self.status,
            "source": self.source,
            "learning_weight": round(self.calculate_learning_weight(), 3),
            "created_at": self.created_at.isoformat(),
            "timestamp": self.timestamp.isoformat(),
        }


class ExperienceManager:
    """Manages experience capture, status lifecycle, querying, and privacy boundaries."""

    def __init__(self) -> None:
        # experience_id -> Experience
        self._experiences: dict[str, Experience] = {}

    def capture_experience(self, exp: Experience) -> Experience:
        """INVARIANT 2, 3, 40: Captures an experience, ensures secret redaction, and indexes by ID."""
        exp.sanitize_payloads()
        self._experiences[exp.experience_id] = exp
        return exp

    def record_experience(
        self,
        task_id: str,
        actions: list[dict[str, Any]] | None = None,
        outcome: str = "SUCCESS",
        verification: dict[str, Any] | None = None,
        source: Any = "SYSTEM",
        privacy_scope: str = "PROJECT",
        **kwargs: Any,
    ) -> Experience:
        source_val = source.value if hasattr(source, "value") else str(source)
        exp = Experience(
            task_id=task_id,
            actions=actions or [],
            outcome=outcome,
            verification=verification or {},
            source=source_val,
            privacy_scope=privacy_scope,
            **kwargs,
        )
        return self.capture_experience(exp)

    def get_experience(self, experience_id: str) -> Experience | None:
        return self._experiences.get(experience_id)

    def list_experiences(
        self,
        task_id: str | None = None,
        status: Any = None,
        privacy_scope: str | None = None,
    ) -> list[Experience]:
        exps = list(self._experiences.values())
        status_val = status.value if hasattr(status, "value") else (str(status) if status else None)
        if task_id:
            exps = [e for e in exps if e.task_id == task_id]
        if status_val:
            exps = [e for e in exps if (e.status == status_val or (hasattr(e.status, "value") and e.status.value == status_val))]
        if privacy_scope:
            exps = [e for e in exps if e.privacy_scope == privacy_scope]
        return exps

    def update_status(self, experience_id: str, new_status: Any) -> Experience:
        """INVARIANT 3: Transitions experience lifecycle (RAW, EVALUATED, VALIDATED, CONSOLIDATED, REJECTED, EXPIRED)."""
        exp = self._experiences.get(experience_id)
        if not exp:
            raise ValueError(f"Experience '{experience_id}' not found.")
        exp.status = new_status.value if hasattr(new_status, "value") else str(new_status)
        return exp

    def delete_experience(self, experience_id: str) -> bool:
        """INVARIANT 174: Authorized deletion of experience."""
        if experience_id in self._experiences:
            del self._experiences[experience_id]
            return True
        return False

