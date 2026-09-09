"""Data schemas and contracts for Kairo Autonomous Task Engine (Task 31)."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


class TaskStatus(str, Enum):
    """Authoritative states of an autonomous Task (Spec 4, 30, 64, 65)."""

    QUEUED = "QUEUED"
    PLANNING = "PLANNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    WAITING_USER = "WAITING_USER"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    REPLANNING = "REPLANNING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"
    BLOCKED = "BLOCKED"


class StepStatus(str, Enum):
    """Authoritative states of a plan step node (Spec 8)."""

    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"
    BLOCKED = "BLOCKED"


class TaskPriority(str, Enum):
    """Execution priority levels (Spec 47)."""

    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"


class TaskRiskLevel(str, Enum):
    """Risk classification of actions/steps (Spec 59, 60)."""

    READ = "READ"
    WRITE = "WRITE"
    DESTRUCTIVE = "DESTRUCTIVE"


class AutonomyLevel(str, Enum):
    """Configured bounds of autonomy (Spec 149, 150)."""

    ASSISTED = "ASSISTED"
    SUPERVISED = "SUPERVISED"
    AUTONOMOUS_READ = "AUTONOMOUS_READ"
    AUTONOMOUS_BOUNDED = "AUTONOMOUS_BOUNDED"


class FailureClassification(str, Enum):
    """Root cause classification for failures and retries (Spec 31)."""

    TRANSIENT = "TRANSIENT"
    PERMANENT = "PERMANENT"
    AUTHORIZATION = "AUTHORIZATION"
    SECURITY = "SECURITY"
    USER = "USER"
    DEPENDENCY = "DEPENDENCY"
    TIMEOUT = "TIMEOUT"
    BUDGET = "BUDGET"
    CAPABILITY = "CAPABILITY"
    VALIDATION = "VALIDATION"
    UNKNOWN = "UNKNOWN"


class ResourceType(str, Enum):
    """Declarable lockable resource types (Spec 58, 131)."""

    REPOSITORY = "REPOSITORY"
    FILE = "FILE"
    DEVICE = "DEVICE"
    WORKFLOW = "WORKFLOW"
    PROJECT = "PROJECT"


class TaskBudget(BaseModel):
    """Resource limits and runtime usage tracking (Spec 14, 15)."""

    model_config = ConfigDict(extra="ignore")

    max_steps: int = Field(default=20, ge=1, le=100)
    max_tool_calls: int = Field(default=50, ge=1, le=500)
    max_agents: int = Field(default=5, ge=1, le=20)
    max_duration_seconds: int = Field(default=1800, ge=30, le=7200)
    max_cost_usd: float = Field(default=10.0, ge=0.0)
    max_replans: int = Field(default=5, ge=0, le=20)

    # Runtime tracking
    steps_used: int = 0
    tool_calls_used: int = 0
    agents_used: int = 0
    duration_used_seconds: float = 0.0
    cost_used_usd: float = 0.0
    replans_used: int = 0

    def is_exhausted(self) -> tuple[bool, str]:
        """Check if any budget dimension is exceeded."""
        if self.steps_used > self.max_steps:
            return True, f"Step limit exhausted ({self.steps_used}/{self.max_steps})"
        if self.tool_calls_used > self.max_tool_calls:
            return True, f"Tool call limit exhausted ({self.tool_calls_used}/{self.max_tool_calls})"
        if self.agents_used > self.max_agents:
            return True, f"Agent call limit exhausted ({self.agents_used}/{self.max_agents})"
        if self.duration_used_seconds > self.max_duration_seconds:
            return True, f"Duration limit exhausted ({self.duration_used_seconds:.1f}s/{self.max_duration_seconds}s)"
        if self.cost_used_usd > self.max_cost_usd:
            return True, f"Cost limit exhausted (${self.cost_used_usd:.2f}/${self.max_cost_usd:.2f})"
        if self.replans_used > self.max_replans:
            return True, f"Replan limit exhausted ({self.replans_used}/{self.max_replans})"
        return False, ""


class TaskResource(BaseModel):
    """Resource declaration for concurrency and write serialization (Spec 58)."""

    type: ResourceType
    id: str
    mode: str = "READ"  # READ or WRITE


class VerificationCriterion(BaseModel):
    """Objective criteria required to verify task/step success (Spec 27, 28)."""

    type: str  # exit_code, file_exists, contains_text, json_schema, custom_assertion, subjective_llm
    target: str = ""
    expected_value: Any = None
    description: str = ""


class TaskStepSchema(BaseModel):
    """A single step in a task plan DAG (Spec 7, 8)."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: f"step_{uuid.uuid4().hex[:10]}")
    task_id: str
    plan_id: str
    sequence: int
    title: str
    objective: str
    skill_id: Optional[str] = None
    tool_name: Optional[str] = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)  # step IDs this step depends on
    status: StepStatus = StepStatus.PENDING
    risk_level: TaskRiskLevel = TaskRiskLevel.READ
    approval_required: bool = False
    approval_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    retry_count: int = 0
    resources: list[TaskResource] = Field(default_factory=list)
    result_reference: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TaskPlanSchema(BaseModel):
    """Versioned plan containing steps and verification contracts (Spec 6, 12)."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: f"plan_{uuid.uuid4().hex[:10]}")
    task_id: str
    version: int = 1
    plan_hash: str
    steps: list[TaskStepSchema] = Field(default_factory=list)
    verification_criteria: list[VerificationCriterion] = Field(default_factory=list)
    supersedes_plan_id: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)


class TaskResultSummary(BaseModel):
    """Structured, verifiable completion summary (Spec 89, 147)."""

    outcome: str  # COMPLETED, PARTIALLY_COMPLETED, FAILED, CANCELLED, TIMED_OUT
    summary: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    changes: list[dict[str, Any]] = Field(default_factory=list)
    verification: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


class TaskCreateRequest(BaseModel):
    """User request to initiate an autonomous task (Spec 3, 125)."""

    model_config = ConfigDict(extra="ignore")

    objective: str = Field(..., min_length=3, max_length=5000)
    project_id: Optional[str] = None
    priority: TaskPriority = TaskPriority.NORMAL
    autonomy_level: Optional[AutonomyLevel] = None
    budget: Optional[TaskBudget] = None
    deadline: Optional[datetime] = None
    dry_run: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskStepResponse(BaseModel):
    """External view of a task step."""

    id: str
    sequence: int
    title: str
    objective: str
    skill_id: Optional[str]
    tool_name: Optional[str]
    dependencies: list[str]
    status: StepStatus
    risk_level: TaskRiskLevel
    approval_required: bool
    approval_id: Optional[str]
    retry_count: int
    resources: list[TaskResource]
    error: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


class TaskResponse(BaseModel):
    """Authoritative representation of an autonomous task."""

    id: str
    user_id: str
    project_id: Optional[str]
    objective: str
    status: TaskStatus
    priority: TaskPriority
    autonomy_level: AutonomyLevel
    parent_task_id: Optional[str]
    correlation_id: str
    current_step_id: Optional[str]
    active_plan_id: Optional[str]
    plan_version: int = 1
    total_steps: int = 0
    completed_steps: int = 0
    progress_text: str = ""
    budget: TaskBudget
    metadata: dict[str, Any]
    result_summary: Optional[TaskResultSummary]
    deadline: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    steps: list[TaskStepResponse] = Field(default_factory=list)
    pending_approval: Optional[dict[str, Any]] = None
    waiting_user_question: Optional[str] = None


class TaskApprovalRequest(BaseModel):
    """Approval payload presented to user (Spec 19)."""

    task_id: str
    step_id: str
    skill_id: Optional[str] = None
    action: str
    target: str
    risk_level: TaskRiskLevel
    reason: str
    expires_at: datetime


class ApprovalActionRequest(BaseModel):
    """User response to approval request (Spec 19, 123)."""

    approved: bool
    reason: str = ""


class UserPromptResponse(BaseModel):
    """User answer when task is in WAITING_USER state (Spec 65, 123)."""

    response: str = Field(..., min_length=1, max_length=2000)


class TaskCheckpointSchema(BaseModel):
    """State checkpoint for crash resumption (Spec 38, 39)."""

    id: str
    task_id: str
    plan_version: int
    step_index: int
    state_data: dict[str, Any]
    created_at: datetime
