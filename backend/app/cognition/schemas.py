"""Pydantic schemas and DTOs for Kairo Cognitive Planning REST API (Task 41)."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from app.cognition.alternatives import PlanAlternative
from app.cognition.evaluator import PlanValidationReport
from app.cognition.explain import PlanPreview, StepExplanation
from app.cognition.goals import GoalPriority, GoalType
from app.cognition.plans import PlanDiff, PlanRiskLevel, PlanStatus
from app.cognition.replanner import ReplanReason
from app.cognition.steps import PlanStep, StepStatus


class GoalCreateRequest(BaseModel):
    """Payload to declare a new goal."""

    model_config = ConfigDict(extra="ignore")

    description: str = Field(..., min_length=3, description="Description of the goal/objective")
    goal_type: GoalType | None = Field(default=None, description="Optional explicit classification")
    priority: GoalPriority = Field(default=GoalPriority.NORMAL)
    project_id: str | None = Field(default=None)
    constraints: dict[str, Any] = Field(default_factory=dict)
    success_criteria: list[str] = Field(default_factory=list)
    allowed_resources: list[str] = Field(default_factory=list)
    allowed_environments: list[str] = Field(default_factory=list)
    deadline: datetime | None = Field(default=None)


class GoalResponse(BaseModel):
    """Response payload representing a registered Goal."""

    model_config = ConfigDict(extra="ignore")

    goal_id: str
    description: str
    source: str
    goal_type: str
    priority: str
    status: str
    success_criteria: list[str]
    created_at: datetime
    deadline: datetime | None = None


class PlanBuildRequest(BaseModel):
    """Payload to request the planner to construct an execution plan for a goal."""

    model_config = ConfigDict(extra="ignore")

    reasoning_mode: str | None = Field(default=None, description="DIRECT, DECOMPOSITION, DIAGNOSTIC, RESEARCH, etc.")
    override_risk: PlanRiskLevel | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class PlanResponse(BaseModel):
    """Response containing a generated Plan."""

    model_config = ConfigDict(extra="ignore")

    plan_id: str
    goal_id: str
    user_id: str
    project_id: str | None = None
    version: int
    status: PlanStatus
    reasoning_mode: str
    risk: PlanRiskLevel
    steps: list[PlanStep]
    success_criteria: list[str]
    validation: PlanValidationReport
    alternatives: list[PlanAlternative] = Field(default_factory=list)
    preview: PlanPreview


class ReplanApiRequest(BaseModel):
    """Payload to trigger adaptive re-planning."""

    model_config = ConfigDict(extra="ignore")

    reason: ReplanReason
    observed_failure: str | None = None


class ReplanApiResponse(BaseModel):
    """Response containing new plan version and structural diff."""

    model_config = ConfigDict(extra="ignore")

    new_plan: PlanResponse
    diff: PlanDiff


class StepVerifyApiRequest(BaseModel):
    """Payload to verify an executed step's outcome."""

    model_config = ConfigDict(extra="ignore")

    step_id: str
    output_result: dict[str, Any] = Field(default_factory=dict)
    observed_state: dict[str, Any] = Field(default_factory=dict)


class StepVerifyApiResponse(BaseModel):
    """Response from step verification."""

    model_config = ConfigDict(extra="ignore")

    step_id: str
    verified: bool
    check_type: str
    evidence: str
    failure_reason: str | None = None
    plan_completed: bool = False
