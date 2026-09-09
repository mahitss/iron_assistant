"""Canonical schemas, manifests, and DTOs for the Kairo Skills and Capability System."""

from datetime import UTC, datetime
from enum import Enum
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SkillSource(str, Enum):
    """Provenance and trust origin of a skill declaration."""

    BUILTIN = "BUILTIN"
    CONFIG = "CONFIG"
    MODEL_GENERATED = "MODEL_GENERATED"
    UNTRUSTED = "UNTRUSTED"


class SkillRiskLevel(str, Enum):
    """Risk classification hierarchy for skills."""

    READ_ONLY = "READ_ONLY"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    DESTRUCTIVE = "DESTRUCTIVE"

    @classmethod
    def max_risk(cls, risks: list["SkillRiskLevel"]) -> "SkillRiskLevel":
        """Determine highest risk level among a list of risks."""
        order = [cls.READ_ONLY, cls.LOW, cls.MEDIUM, cls.HIGH, cls.CRITICAL, cls.DESTRUCTIVE]
        highest = cls.READ_ONLY
        for r in risks:
            if order.index(r) > order.index(highest):
                highest = r
        return highest


class SkillCategory(str, Enum):
    """High-level category for skills discovery and classification."""

    RESEARCH = "research"
    KNOWLEDGE = "knowledge"
    DOCUMENTS = "documents"
    DEVELOPER = "developer"
    PROJECTS = "projects"
    AUTOMATION = "automation"
    BROWSER = "browser"
    VOICE = "voice"
    VISION = "vision"
    COMPUTER = "computer"


class SkillExecutionState(str, Enum):
    """Lifecycle state of a skill execution."""

    PENDING = "PENDING"
    PLANNING = "PLANNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"


class SkillHealthStatus(str, Enum):
    """Operational health status of a skill and its required dependencies."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


class ExecutionLimits(BaseModel):
    """Execution bounds enforced on a skill plan and tool sequence."""

    max_steps: int = Field(default=20, ge=1, le=50)
    timeout_seconds: int = Field(default=300, ge=5, le=1800)
    max_tool_calls: int = Field(default=50, ge=1, le=100)


class SkillManifest(BaseModel):
    """Canonical metadata declaration for a reusable Kairo skill."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., description="Stable, unique, namespaced skill identifier (e.g. 'research.web')")
    name: str = Field(..., description="Human-readable display name")
    description: str = Field(..., description="Clear explanation of the skill's purpose and capability")
    version: str = Field(default="1.0.0", description="SemVer version string (e.g. '1.0.0')")
    category: SkillCategory = Field(..., description="Category for grouping and intent matching")
    capabilities: list[str] = Field(default_factory=list, description="Associated capability gate names")
    required_tools: list[str] = Field(
        default_factory=list, description="Tools strictly required for basic function"
    )
    optional_tools: list[str] = Field(
        default_factory=list, description="Tools that enhance execution if available"
    )
    risk_level: SkillRiskLevel = Field(
        default=SkillRiskLevel.READ_ONLY, description="Maximum risk level of the skill"
    )
    permissions: list[str] = Field(default_factory=list, description="Required permission scope declarations")
    input_schema: dict[str, Any] = Field(
        default_factory=dict, description="JSON schema defining valid input arguments"
    )
    output_schema: dict[str, Any] = Field(
        default_factory=dict, description="JSON schema defining expected output structure"
    )
    execution_limits: ExecutionLimits = Field(default_factory=ExecutionLimits)
    enabled: bool = Field(default=True, description="Whether the skill is actively enabled for execution")
    source: SkillSource | str = Field(
        default=SkillSource.BUILTIN, description="Provenance of the skill definition"
    )
    project_scoped: bool = Field(
        default=False, description="Whether execution must be scoped to an active project"
    )
    device_scoped: bool = Field(
        default=False, description="Whether execution requires an active device binding"
    )
    depends_on: list[str] = Field(
        default_factory=list, description="IDs of other skills this skill composes with"
    )
    dependencies: list[str] = Field(
        default_factory=list, description="Alias for depends_on"
    )

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9_]+(\.[a-z0-9_]+)+$", v):
            raise ValueError(f"Skill ID '{v}' is invalid. Must be namespaced format (e.g. 'category.action').")
        return v

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        if not re.match(r"^\d+\.\d+\.\d+$", v):
            raise ValueError(f"Skill version '{v}' is invalid. Must be SemVer (MAJOR.MINOR.PATCH).")
        return v

    @property
    def all_tools(self) -> list[str]:
        return list(set(self.required_tools + self.optional_tools))

    @property
    def required_permissions(self) -> list[str]:
        return self.permissions

    @property
    def limits(self) -> ExecutionLimits:
        return self.execution_limits


class SkillPlanStep(BaseModel):
    """Discrete step within an executable skill plan."""

    step_number: int
    description: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    risk_level: SkillRiskLevel = Field(default=SkillRiskLevel.READ_ONLY)
    status: str = Field(default="pending", description="pending, running, completed, failed, skipped")
    output: Any | None = None
    error: str | None = None


class SkillPlan(BaseModel):
    """Structured, bounded execution plan generated for a skill."""

    plan_id: str
    skill_id: str
    goal: str
    steps: list[SkillPlanStep] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SkillResult(BaseModel):
    """Standardized output produced upon completing or terminating skill execution."""

    execution_id: str
    skill_id: str
    skill_version: str
    status: SkillExecutionState
    state: SkillExecutionState | None = None
    summary: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    plan: SkillPlan | None = None
    error: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    duration_ms: float = 0.0
    cost_estimate: float | None = None
    project_id: str | None = None
    device_id: str | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        if self.state is None:
            self.state = self.status


class SkillExecutionRecord(BaseModel):
    """Execution state tracking record for a running or completed skill."""

    execution_id: str
    skill_id: str
    skill_version: str
    status: SkillExecutionState = Field(default=SkillExecutionState.PENDING)
    summary: str = ""
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    duration_ms: float = 0.0
    project_id: str | None = None
    device_id: str | None = None
    plan: SkillPlan | None = None
    error: str | None = None
    approval_id: str | None = None
    result: SkillResult | None = None

    @property
    def state(self) -> SkillExecutionState:
        return self.status

    @state.setter
    def state(self, value: SkillExecutionState) -> None:
        self.status = value


# --- API & Execution Context Schemas ---


class SkillExecutionRequest(BaseModel):
    """Execution invocation request."""

    skill_id: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    user_id: str = "default_user"
    project_id: str | None = None
    device_id: str | None = None
    session_id: str | None = None


class SkillExecutionPlanContext(BaseModel):
    """Context for constructing a plan."""

    intent: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    project_id: str | None = None
    device_id: str | None = None


class SkillResolutionResult(BaseModel):
    """Resolution outcome containing candidate skill."""

    skill: SkillManifest
    confidence: float = 1.0
    reason: str = "Deterministic pattern match"


class SkillSummaryItem(BaseModel):
    """Public summary of a registered skill."""

    id: str
    name: str
    description: str
    version: str
    category: SkillCategory
    risk_level: SkillRiskLevel
    enabled: bool
    source: str
    health: SkillHealthStatus
    health_status: SkillHealthStatus = Field(default=SkillHealthStatus.HEALTHY)
    capabilities: list[str]
    project_scoped: bool
    device_scoped: bool


class SkillDetailResponse(BaseModel):
    """Comprehensive skill detail for inspection."""

    id: str
    name: str
    description: str
    version: str
    category: SkillCategory
    risk_level: SkillRiskLevel
    enabled: bool
    source: str
    capabilities: list[str]
    required_tools: list[str] = Field(default_factory=list)
    optional_tools: list[str] = Field(default_factory=list)
    required_permissions: list[str] = Field(default_factory=list)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    execution_limits: ExecutionLimits = Field(default_factory=ExecutionLimits)
    health: SkillHealthStatus = Field(default=SkillHealthStatus.HEALTHY)
    health_status: SkillHealthStatus = Field(default=SkillHealthStatus.HEALTHY)
    health_reason: str | None = None
    project_scoped: bool = False
    device_scoped: bool = False
    manifest: SkillManifest | None = None


class SkillExecuteRequest(BaseModel):
    """Input payload to execute a skill."""

    inputs: dict[str, Any] = Field(
        default_factory=dict, description="Skill-specific arguments validated by input_schema"
    )
    project_id: str | None = Field(default=None, description="Project context identifier if applicable")
    device_id: str | None = Field(default=None, description="Target device identifier if applicable")
    session_id: str | None = Field(default=None, description="Calling session or conversation context")


class SkillToggleRequest(BaseModel):
    """Toggle enabled status of a skill."""

    enabled: bool

