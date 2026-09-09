"""Pydantic schemas and enums for Kairo Resilience, Fault-Tolerance, and Recovery (Task 37)."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
import uuid
from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


def generate_uuid(prefix: str = "") -> str:
    u = uuid.uuid4().hex
    return f"{prefix}_{u[:12]}" if prefix else str(uuid.uuid4())


# ==============================================================================
# Enums
# ==============================================================================

class FailureCategory(str, Enum):
    """Deterministic failure classification categories."""
    TRANSIENT = "TRANSIENT"
    TIMEOUT = "TIMEOUT"
    RATE_LIMITED = "RATE_LIMITED"
    UNAVAILABLE = "UNAVAILABLE"
    AUTHENTICATION = "AUTHENTICATION"
    AUTHORIZATION = "AUTHORIZATION"
    VALIDATION = "VALIDATION"
    DEPENDENCY = "DEPENDENCY"
    CONFLICT = "CONFLICT"
    STALE_STATE = "STALE_STATE"
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"
    PERMANENT = "PERMANENT"
    UNKNOWN = "UNKNOWN"


class FailureSeverity(str, Enum):
    """Deterministic failure severities."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class RecoveryState(str, Enum):
    """Task recovery and resilience lifecycle states."""
    RECOVERING = "RECOVERING"
    RESUMABLE = "RESUMABLE"
    WAITING = "WAITING"
    WAITING_DEPENDENCY = "WAITING_DEPENDENCY"
    WAITING_DEVICE = "WAITING_DEVICE"
    WAITING_USER = "WAITING_USER"
    UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"
    DEGRADED = "DEGRADED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    QUARANTINED = "QUARANTINED"


class DependencyHealth(str, Enum):
    """Health status for external or internal dependencies."""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


class SideEffectType(str, Enum):
    """Classification of tool/skill side-effect boundaries."""
    READ_ONLY = "READ_ONLY"
    IDEMPOTENT_WRITE = "IDEMPOTENT_WRITE"
    NON_IDEMPOTENT_WRITE = "NON_IDEMPOTENT_WRITE"


class OutcomeState(str, Enum):
    """Result of authoritative outcome reconciliation."""
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    IN_PROGRESS = "IN_PROGRESS"
    UNKNOWN = "UNKNOWN"


# ==============================================================================
# Failure Model
# ==============================================================================

class Failure(BaseModel):
    """Sanitized failure descriptor containing zero secrets or sensitive tokens."""
    model_config = ConfigDict(extra="ignore")

    failure_id: str = Field(default_factory=lambda: generate_uuid("fail"))
    category: FailureCategory
    code: str
    operation: str
    component: str
    retryable: bool
    severity: FailureSeverity = FailureSeverity.MEDIUM
    occurred_at: datetime = Field(default_factory=utc_now)
    correlation_id: str | None = None
    cause: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ==============================================================================
# Retry & Backoff Models
# ==============================================================================

class RetryPolicy(BaseModel):
    """Bounded retry policy with exponential backoff and jitter configuration."""
    model_config = ConfigDict(extra="ignore")

    max_attempts: int = Field(default=3, ge=1, le=10)
    initial_delay: float = Field(default=1.0, ge=0.01)
    max_delay: float = Field(default=30.0, ge=1.0)
    multiplier: float = Field(default=2.0, ge=1.0)
    jitter: bool = True
    retryable_failures: list[FailureCategory] = Field(
        default_factory=lambda: [
            FailureCategory.TRANSIENT,
            FailureCategory.TIMEOUT,
            FailureCategory.RATE_LIMITED,
            FailureCategory.UNAVAILABLE,
            FailureCategory.RESOURCE_EXHAUSTED,
        ]
    )
    respect_retry_after: bool = True


class RetryBudget(BaseModel):
    """Retry budget tracker per-operation, per-task, and per-provider."""
    model_config = ConfigDict(extra="ignore")

    max_retries_per_op: int = 3
    max_retries_per_task: int = 10
    max_retries_per_provider: int = 30
    current_op_retries: int = 0
    current_task_retries: int = 0
    current_provider_retries: int = 0

    def can_retry_op(self) -> bool:
        return self.current_op_retries < self.max_retries_per_op

    def can_retry_task(self) -> bool:
        return self.current_task_retries < self.max_retries_per_task

    def can_retry_provider(self) -> bool:
        return self.current_provider_retries < self.max_retries_per_provider

    def can_retry(self) -> bool:
        return self.can_retry_op() and self.can_retry_task() and self.can_retry_provider()

    def record_retry(self) -> None:
        self.current_op_retries += 1
        self.current_task_retries += 1
        self.current_provider_retries += 1


# ==============================================================================
# Idempotency Models
# ==============================================================================

class IdempotencyRecord(BaseModel):
    """Record tracking deduplicated execution of side-effecting operations."""
    model_config = ConfigDict(from_attributes=True)

    idempotency_key: str
    operation: str
    user_id: str | None = None
    task_id: str | None = None
    status: str = "STARTED"  # STARTED, COMPLETED, FAILED
    result_reference: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime


# ==============================================================================
# Lease & Fencing Models
# ==============================================================================

class TaskLease(BaseModel):
    """Worker execution lease with monotonic fencing token."""
    model_config = ConfigDict(from_attributes=True)

    task_id: str
    worker_id: str
    fencing_token: int = 1
    acquired_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime
    heartbeat_at: datetime = Field(default_factory=utc_now)


# ==============================================================================
# Checkpoint Models
# ==============================================================================

class TaskCheckpoint(BaseModel):
    """Transactional, versioned task state checkpoint."""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: generate_uuid("ckpt"))
    task_id: str
    step_id: str | None = None
    version: int = 1
    state_json: dict[str, Any] = Field(default_factory=dict)
    policy_version: int | None = None
    is_valid: bool = True
    created_at: datetime = Field(default_factory=utc_now)


# ==============================================================================
# Circuit Breaker Models
# ==============================================================================

class CircuitBreakerConfig(BaseModel):
    """Configuration for a scoped circuit breaker."""
    failure_threshold: int = 5
    recovery_threshold: int = 2
    cooldown_seconds: float = 30.0


class CircuitBreakerStatus(BaseModel):
    """Current state and probe counters for a circuit breaker."""
    model_config = ConfigDict(from_attributes=True)

    circuit_id: str
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_at: datetime | None = None
    opened_at: datetime | None = None
    updated_at: datetime = Field(default_factory=utc_now)


# ==============================================================================
# Quarantine & Health Models
# ==============================================================================

class QuarantineRecord(BaseModel):
    """Record of a quarantined poison task."""
    model_config = ConfigDict(from_attributes=True)

    task_id: str
    reason: str
    failure_count: int = 1
    quarantined_by: str | None = None
    status: str = "QUARANTINED"
    quarantined_at: datetime = Field(default_factory=utc_now)
    released_at: datetime | None = None


class DependencyHealthReport(BaseModel):
    """Real-time health status of a system dependency."""
    dependency: str
    status: DependencyHealth
    latency_ms: float = 0.0
    details: str | None = None
    checked_at: datetime = Field(default_factory=utc_now)


class SystemReliabilityDashboard(BaseModel):
    """Summary metrics and health for system reliability dashboard."""
    dependencies: list[DependencyHealthReport] = Field(default_factory=list)
    circuits: list[CircuitBreakerStatus] = Field(default_factory=list)
    active_leases: int = 0
    quarantined_tasks_count: int = 0
    total_retries: int = 0
    retry_success_rate: float = 1.0
    recovery_success_rate: float = 1.0
    stuck_tasks_detected: int = 0
