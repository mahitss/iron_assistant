"""PlanStep model, StepStatus, and verification specifications for Kairo Cognitive Planning (Task 41)."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
import uuid
from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class StepStatus(str, Enum):
    """Execution status of a cognitive plan step node."""

    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"


class StepRiskLevel(str, Enum):
    """Risk tier for step actions."""

    READ = "READ"
    WRITE = "WRITE"
    DESTRUCTIVE = "DESTRUCTIVE"


class VerificationSpec(BaseModel):
    """Measurable verification requirements for an individual step."""

    model_config = ConfigDict(extra="ignore")

    check_type: str = Field(default="OUTPUT_MATCH", description="Type: STATE_CHECK, OUTPUT_MATCH, HEALTH_CHECK, DIFF_CHECK, SOURCE_QUERY, INVARIANT_CHECK")
    target: str = Field(default="", description="Target entity, endpoint, path, or metric to evaluate")
    expected: Any = Field(default=None, description="Expected outcome value, status code, or pattern")
    preconditions: list[str] = Field(default_factory=list, description="Explicit statements that must hold true before execution")
    postconditions: list[str] = Field(default_factory=list, description="Explicit conditions that must hold true after execution")
    invariants: list[str] = Field(default_factory=list, description="Invariants that must not be violated (e.g. production must stay up)")


class PlanStep(BaseModel):
    """Atomic, observable, verifiable, and recoverable step inside a plan."""

    model_config = ConfigDict(extra="ignore")

    step_id: str = Field(default_factory=lambda: f"step_{uuid.uuid4().hex[:12]}")
    plan_id: str = Field(..., description="Parent plan ID")
    sequence: int = Field(..., description="Topological sequence index")
    objective: str = Field(..., min_length=1, description="Clear statement of step objective")
    action: str = Field(..., description="Identifier of planned action/tool (e.g. git_status, test_runner)")
    dependencies: list[str] = Field(default_factory=list, description="IDs of steps that must complete before this step")
    inputs: dict[str, Any] = Field(default_factory=dict, description="Structured parameters for action")
    expected_output: dict[str, Any] = Field(default_factory=dict, description="Expected schema/output keys")
    success_criteria: list[str] = Field(default_factory=list, description="Criteria for success")
    risk: StepRiskLevel = Field(default=StepRiskLevel.READ)
    reversible: bool = Field(default=True, description="Whether this operation can be undone/reverted")
    verification: VerificationSpec = Field(default_factory=VerificationSpec)
    status: StepStatus = Field(default=StepStatus.PENDING)
    output_result: dict[str, Any] | None = Field(default=None, description="Recorded output from execution engine")
    error_message: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
