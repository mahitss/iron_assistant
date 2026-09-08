"""Pydantic schemas for workflows, triggers, actions, steps, runs, and approvals."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

TriggerType = Literal["schedule", "manual", "condition"]
ScheduleInterval = Literal["once", "hourly", "daily", "weekly"]
StepType = Literal["action", "condition", "notification"]
WorkflowStatus = Literal[
    "pending",
    "running",
    "waiting_approval",
    "retrying",
    "completed",
    "failed",
    "cancelled",
    "expired",
]
ApprovalStatus = Literal["pending", "approved", "denied", "expired"]


class TriggerConfig(BaseModel):
    """Configuration defining when a workflow activates."""

    trigger_type: TriggerType = "manual"
    interval: ScheduleInterval | None = None
    time: str | None = Field(default=None, description="24-hour time string (e.g. '08:00' or '20:30')")
    day_of_week: int | None = Field(default=None, description="0=Monday, 6=Sunday for weekly schedules")
    timezone: str = Field(
        default="UTC", description="IANA timezone (e.g. 'Asia/Kolkata', 'America/New_York')"
    )
    condition: dict[str, Any] | None = Field(
        default=None, description="Condition watch definition for condition triggers"
    )


class StepDefinition(BaseModel):
    """Definition of a single step inside a workflow."""

    id: str | None = None
    type: StepType = "action"
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Configuration: for action: {'tool': '...', 'arguments': {...}}; for condition: {'field': '...', 'operator': '...', 'value': '...'}",
    )


class ActionConfig(BaseModel):
    """Sequence of steps comprising a workflow."""

    steps: list[StepDefinition] = Field(default_factory=list)


class WorkflowCreate(BaseModel):
    """Request payload to create a new user workflow."""

    name: str = Field(..., max_length=128)
    description: str = Field(default="", max_length=2000)
    trigger: TriggerConfig
    actions: ActionConfig
    enabled: bool = True


class WorkflowUpdate(BaseModel):
    """Request payload to modify an existing workflow."""

    name: str | None = Field(default=None, max_length=128)
    description: str | None = Field(default=None, max_length=2000)
    trigger: TriggerConfig | None = None
    actions: ActionConfig | None = None
    enabled: bool | None = None


class WorkflowResponse(BaseModel):
    """Response payload detailing a workflow."""

    id: str
    user_id: str
    name: str
    description: str
    enabled: bool
    trigger_type: str
    trigger_config: dict[str, Any]
    action_config: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    version: int


class StepRunResponse(BaseModel):
    """Response payload detailing execution of a workflow step."""

    id: str
    run_id: str
    step_index: int
    step_type: str
    configuration: dict[str, Any]
    status: str
    attempt_count: int
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result_summary: dict[str, Any] | None = None
    error: str | None = None


class ApprovalRequestResponse(BaseModel):
    """Response payload for human-in-the-loop approval gate."""

    id: str
    user_id: str
    run_id: str
    step_id: str | None = None
    tool_name: str
    tool_args: dict[str, Any]
    permission_level: str
    status: ApprovalStatus
    expires_at: datetime
    created_at: datetime
    decided_at: datetime | None = None


class ApprovalDecisionRequest(BaseModel):
    """Request payload to approve or deny a pending action."""

    decision: Literal["approve", "deny"]
    reason: str | None = None


class WorkflowRunResponse(BaseModel):
    """Response payload detailing an execution run."""

    id: str
    workflow_id: str
    user_id: str
    status: WorkflowStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    retry_count: int
    idempotency_key: str
    current_step: int
    created_at: datetime
    updated_at: datetime
    steps: list[StepRunResponse] = Field(default_factory=list)
    approvals: list[ApprovalRequestResponse] = Field(default_factory=list)


class NotificationResponse(BaseModel):
    """In-app alert produced by a workflow run."""

    id: str
    user_id: str
    workflow_id: str | None = None
    run_id: str | None = None
    title: str
    message: str
    level: str
    read: bool
    created_at: datetime
