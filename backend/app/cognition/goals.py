"""Goal domain models and classifications for Kairo Cognitive Planning (Task 41)."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


class GoalType(str, Enum):
    """Authoritative Goal classifications."""

    INFORMATIONAL = "INFORMATIONAL"
    ANALYTICAL = "ANALYTICAL"
    CREATIVE = "CREATIVE"
    OPERATIONAL = "OPERATIONAL"
    MAINTENANCE = "MAINTENANCE"
    DEVELOPMENT = "DEVELOPMENT"
    AUTOMATION = "AUTOMATION"
    RESEARCH = "RESEARCH"
    MULTI_STEP = "MULTI_STEP"


class GoalPriority(str, Enum):
    """Goal execution priority."""

    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class GoalStatus(str, Enum):
    """Goal lifecycle status."""

    PENDING = "PENDING"
    PLANNING = "PLANNING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class GoalScope(BaseModel):
    """Defines the strict boundary and allowed resources for a goal."""

    model_config = ConfigDict(extra="ignore")

    user_id: str = Field(..., description="Owner user ID")
    project_id: str | None = Field(default=None, description="Scoped project workspace")
    allowed_resources: list[str] = Field(default_factory=list, description="Explicitly allowed resource paths/identifiers")
    allowed_environments: list[str] = Field(default_factory=lambda: ["development"], description="Permitted environments")
    max_duration_seconds: float = Field(default=3600.0, description="Overall goal deadline timeout in seconds")


class Goal(BaseModel):
    """Authoritative Goal object representing a structured user objective."""

    model_config = ConfigDict(extra="ignore")

    goal_id: str = Field(default_factory=lambda: f"goal_{uuid.uuid4().hex[:12]}")
    description: str = Field(..., min_length=3, description="Detailed description of objective")
    source: str = Field(default="USER", description="Source of goal (USER, SYSTEM, SCHEDULE)")
    goal_type: GoalType = Field(default=GoalType.OPERATIONAL)
    priority: GoalPriority = Field(default=GoalPriority.NORMAL)
    constraints: dict[str, Any] = Field(default_factory=dict, description="Hard & soft constraints")
    success_criteria: list[str] = Field(
        default_factory=lambda: ["Goal completed and verified with zero uncaught errors."],
        description="Measurable validation criteria",
    )
    scope: GoalScope
    status: GoalStatus = Field(default=GoalStatus.PENDING)
    created_at: datetime = Field(default_factory=utc_now)
    deadline: datetime | None = Field(default=None)

    @field_validator("success_criteria")
    @classmethod
    def validate_success_criteria(cls, v: list[str]) -> list[str]:
        if not v:
            # Enforce at least one measurable success criteria for any goal
            return ["Goal completed and verified with zero uncaught errors."]
        return [c.strip() for c in v if c.strip()]
