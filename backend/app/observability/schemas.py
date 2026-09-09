"""Pydantic schemas and typed data structures for Unified Observability and System Intelligence (Task 38)."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class TraceStatus(str, Enum):
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"
    DEGRADED = "DEGRADED"


class SpanStatus(str, Enum):
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"
    DEGRADED = "DEGRADED"


class SeverityLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class IncidentSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IncidentStatus(str, Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class ConfidenceLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class DependencyHealthState(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


# ============================================================================
# Span & Trace Schemas
# ============================================================================


class SpanEvent(BaseModel):
    """An annotated lifecycle milestone or error within a span."""

    name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    attributes: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")


class ErrorEvent(BaseModel):
    """Structured error event embedded in telemetry (free of credentials)."""

    error_code: str
    error_category: str
    message: str
    retryable: bool = False
    attempt: int = 1
    dependency: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Span(BaseModel):
    """A unit of execution within a distributed trace."""

    span_id: str
    trace_id: str
    parent_span_id: str | None = None
    operation: str
    component: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    duration_ms: float | None = None
    status: SpanStatus = SpanStatus.RUNNING
    error_code: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    events: list[SpanEvent] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


class Trace(BaseModel):
    """A complete distributed execution trace across components."""

    trace_id: str
    root_operation: str
    user_id: str | None = None
    session_id: str | None = None
    task_id: str | None = None
    project_id: str | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    duration_ms: float | None = None
    status: TraceStatus = TraceStatus.RUNNING
    error_count: int = 0
    spans: list[Span] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")


class CorrelationMetadata(BaseModel):
    """Contextual correlation propagated across async calls and workers."""

    trace_id: str
    correlation_id: str
    task_id: str | None = None
    step_id: str | None = None
    operation_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    project_id: str | None = None


# ============================================================================
# Metrics Schemas
# ============================================================================


class MetricRecord(BaseModel):
    name: str
    type: str  # counter, gauge, histogram
    value: float
    labels: dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ============================================================================
# Service Map & Dependencies
# ============================================================================


class DependencyNode(BaseModel):
    name: str
    type: str  # api, task_engine, agent, tool, model, database, redis, external
    health: DependencyHealthState = DependencyHealthState.HEALTHY
    latency_p95_ms: float = 0.0
    error_rate: float = 0.0


class DependencyEdge(BaseModel):
    source: str
    target: str
    call_count: int = 0
    error_count: int = 0


class ServiceMap(BaseModel):
    nodes: list[DependencyNode] = Field(default_factory=list)
    edges: list[DependencyEdge] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ============================================================================
# Root-Cause Analysis (RCA) & Diagnostics
# ============================================================================


class RootCauseAnalysis(BaseModel):
    """Diagnostic RCA output citing observable evidence without auto-remediating."""

    id: str
    target_ref: str  # trace_id, task_id, or incident_id
    probable_root_cause: str
    evidence: list[str] = Field(default_factory=list)
    contributing_causes: list[str] = Field(default_factory=list)
    affected_components: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    recommended_next_action: str
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DiagnosticReport(BaseModel):
    """User-safe plain language diagnostic summary."""

    target_ref: str
    summary: str
    what_happened: str
    status: str
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    next_steps: str


# ============================================================================
# Incident & Anomaly Schemas
# ============================================================================


class AnomalyReport(BaseModel):
    anomaly_id: str
    metric_name: str
    component: str
    current_value: float
    baseline_value: float
    deviation_factor: float
    severity: IncidentSeverity = IncidentSeverity.MEDIUM
    evidence: str
    detected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Incident(BaseModel):
    id: str
    title: str
    severity: IncidentSeverity = IncidentSeverity.MEDIUM
    status: IncidentStatus = IncidentStatus.OPEN
    affected_components: list[str] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    root_cause: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    resolved_at: datetime | None = None
    acknowledged_by: str | None = None


# ============================================================================
# Health Score Summary
# ============================================================================


class HealthScoreSummary(BaseModel):
    """Deterministic explainable service health summary (no arbitrary AI scores)."""

    score: float  # 0.0 to 100.0
    availability_percent: float
    error_rate: float
    latency_p95_ms: float
    dependency_statuses: dict[str, str] = Field(default_factory=dict)
    overall_status: DependencyHealthState = DependencyHealthState.HEALTHY
