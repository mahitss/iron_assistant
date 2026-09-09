"""Canonical data structures and schemas for Kairo Evaluation, Benchmarking, and Quality Gates."""

from datetime import UTC, datetime
from enum import Enum
import re
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ScenarioCategory(str, Enum):
    """Evaluation scenario categories covering all Kairo sub-systems."""

    CHAT = "chat"
    ROUTING = "routing"
    TOOLS = "tools"
    SECURITY = "security"
    MEMORY = "memory"
    CONTEXT = "context"
    KNOWLEDGE = "knowledge"
    RESEARCH = "research"
    AGENTS = "agents"
    AUTOMATION = "automation"
    BROWSER = "browser"
    VOICE = "voice"
    VISION = "vision"
    COMPUTER = "computer"
    GITHUB = "github"
    PROJECTS = "projects"
    PERFORMANCE = "performance"
    RELIABILITY = "reliability"


class GradingMethod(str, Enum):
    """Grading methodology for evaluation scenarios."""

    DETERMINISTIC = "deterministic"
    RUBRIC = "rubric"
    SECURITY_BINARY = "security_binary"
    HYBRID = "hybrid"


class EvalMode(str, Enum):
    """Execution environment mode."""

    LOCAL = "LOCAL"
    CI = "CI"
    STAGING = "STAGING"


EvaluationMode = EvalMode


class EvalRunStatus(str, Enum):
    """Lifecycle status of an evaluation run."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class SecurityExpectations(BaseModel):
    """Explicit security constraints that must be verified for a scenario."""

    model_config = ConfigDict(extra="ignore")

    must_block: bool = Field(default=False, description="Whether execution must be explicitly denied")
    approval_required: bool = Field(default=False, description="Whether execution must trigger human approval")
    prohibit_prompt_injection: bool = Field(
        default=False, description="Must reject adversarial injection instructions"
    )
    prohibit_secret_leak: bool = Field(
        default=False, description="Output, telemetry, and logs must not contain secrets"
    )
    prohibit_unauthorized_scope: bool = Field(
        default=False, description="Must not access other users/projects data"
    )
    prohibit_ssrf: bool = Field(default=False, description="Must block private network / loopback access")
    emergency_stop_active: bool = Field(
        default=False, description="Whether scenario runs under active emergency stop"
    )


class EvaluationScenario(BaseModel):
    """Canonical definition of a testable evaluation benchmark scenario."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., description="Unique namespaced identifier (e.g. 'github.ci_failure.001')")
    name: str = Field(..., description="Human-readable scenario title")
    category: ScenarioCategory = Field(..., description="Scenario domain category")
    input: str | dict[str, Any] = Field(..., description="User prompt, event, or structured request input")
    context: dict[str, Any] = Field(
        default_factory=dict, description="Session, user, project, or device context"
    )
    expected_behavior: str = Field(..., description="Detailed description of what Kairo should do")
    allowed_tools: list[str] = Field(
        default_factory=list, description="Tools permitted to be invoked during execution"
    )
    forbidden_tools: list[str] = Field(
        default_factory=list, description="Tools strictly prohibited during execution"
    )
    expected_output_properties: dict[str, Any] = Field(
        default_factory=dict, description="Expected keys, types, or content substrings in response"
    )
    security_expectations: SecurityExpectations = Field(
        default_factory=SecurityExpectations, description="Specific security gates to verify"
    )
    timeout_seconds: float = Field(default=30.0, ge=1.0, le=600.0)
    grading_method: GradingMethod = Field(default=GradingMethod.DETERMINISTIC)
    tags: list[str] = Field(default_factory=list)
    dataset_version: str = Field(default="v1.0.0")
    is_holdout: bool = Field(
        default=False, description="Whether this scenario is part of the hidden holdout test set"
    )

    @field_validator("id")
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9_\-]+(\.[a-z0-9_\-]+)+$", v):
            raise ValueError(f"Scenario ID '{v}' must be namespaced format (e.g. 'github.ci_failure.001').")
        return v


class GradingResult(BaseModel):
    """Result of grading a single scenario execution."""

    model_config = ConfigDict(extra="ignore")

    passed: bool = Field(..., description="Whether scenario passed evaluation criteria")
    score: float = Field(default=1.0, ge=0.0, le=4.0, description="Normalized score or rubric level 0-4")
    grader_name: str = Field(..., description="Identifier of the grader that scored the case")
    reason: str | None = Field(default=None, description="Detailed explanation of the pass/fail determination")
    details: dict[str, Any] = Field(default_factory=dict)
    failures: list[str] = Field(default_factory=list, description="List of specific violations or failures")


class EvaluationCaseResult(BaseModel):
    """Outcome and execution telemetry of a single evaluated scenario."""

    model_config = ConfigDict(extra="ignore")

    case_id: str
    scenario_id: str
    scenario_name: str
    category: ScenarioCategory
    passed: bool
    score: float
    duration_ms: float
    tokens_used: int = 0
    cost_usd: float = 0.0
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    actual_output: Any = None
    grading: GradingResult
    trace_sanitized: list[dict[str, Any]] = Field(default_factory=list)
    flaky: bool = False
    error: str | None = None


ScenarioResult = EvaluationCaseResult


class MetricSummary(BaseModel):
    """Aggregate metrics across an evaluation run."""

    model_config = ConfigDict(extra="ignore")

    total_scenarios: int = 0
    passed_scenarios: int = 0
    failed_scenarios: int = 0
    flaky_scenarios: int = 0
    pass_rate: float = 0.0

    # Specific Quality & Reliability Dimensions
    security_pass_rate: float = 1.0
    tool_selection_accuracy: float = 0.0
    tool_argument_accuracy: float = 0.0
    tool_efficiency: float = 0.0
    routing_accuracy: float = 0.0
    fallback_success_rate: float = 1.0
    context_precision: float = 0.0
    context_recall: float = 0.0
    memory_precision: float = 0.0
    memory_recall: float = 0.0
    knowledge_precision: float = 0.0
    citation_groundedness: float = 0.0
    agent_task_success: float = 0.0
    agent_overhead: float = 0.0
    workflow_success_rate: float = 0.0

    # Latency & Cost
    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_p99_ms: float = 0.0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0

    # Composite Non-Security Quality Score (0-100%)
    overall_quality_score: float = 0.0


class EvaluationRun(BaseModel):
    """Top-level record of an executed evaluation suite or benchmark run."""

    model_config = ConfigDict(extra="ignore")

    run_id: str
    suite_name: str
    dataset_version: str = "v1.0.0"
    kairo_version: str = "1.1.0"
    git_sha: str = "dev"
    mode: EvalMode = EvalMode.LOCAL
    status: EvalRunStatus = EvalRunStatus.PENDING
    metrics: MetricSummary = Field(default_factory=MetricSummary)
    cases: list[EvaluationCaseResult] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    duration_ms: float = 0.0
    security_gate_passed: bool = True
    release_blocked: bool = False
    block_reasons: list[str] = Field(default_factory=list)


class BaselineMetrics(BaseModel):
    """Frozen baseline metrics from a verified Kairo release."""

    model_config = ConfigDict(extra="ignore")

    version: str
    git_sha: str = "release"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metrics: MetricSummary


class BaselineDelta(BaseModel):
    """Comparison metric delta between current run and baseline."""

    model_config = ConfigDict(extra="ignore")

    metric_name: str
    current_value: float
    baseline_value: float
    delta: float
    delta_percentage: float
    status: str  # "improved", "unchanged", "regressed"
    is_blocking: bool = False


class BaselineComparisonResult(BaseModel):
    """Formal release gate evaluation against previous baseline."""

    model_config = ConfigDict(extra="ignore")

    current_version: str
    baseline_version: str
    release_blocked: bool
    security_gate_intact: bool
    deltas: list[BaselineDelta] = Field(default_factory=list)
    summary: str
    blocking_reasons: list[str] = Field(default_factory=list)

    @property
    def block_release(self) -> bool:
        return self.release_blocked

    @property
    def block_reasons(self) -> list[str]:
        return self.blocking_reasons

    @property
    def status(self) -> str:
        return "RELEASE BLOCKED" if self.release_blocked else "RELEASE APPROVED"
