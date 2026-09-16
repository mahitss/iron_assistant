"""Domain models, contracts, and lifecycle state machines for Task 95 Execution Governance.

Enforces:
- Non-negotiable cognitive axioms:
  REQUESTED ACTION != STARTED ACTION != COMPLETED ACTION != SUCCESSFUL OUTCOME != VERIFIED OUTCOME
  UNKNOWN != SUCCESS != FAILURE
  CANCELLATION != NOTHING HAPPENED
  ROLLBACK IS AN ACTION
  EMERGENCY STOP ALWAYS WINS
- 22 rigid transaction lifecycle states and auditable transitions
- Strongly-typed ActionTransaction and Preflight validation models
- Observation capture and Post-condition verification contracts
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _uuid_hex(prefix: str, length: int = 12) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:length]}"


class TransactionStatus(str, Enum):
    """Rigid operational lifecycle states of an Action Transaction."""
    CREATED = "CREATED"
    PREPARING = "PREPARING"
    PREFLIGHT = "PREFLIGHT"
    BLOCKED = "BLOCKED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    AUTHORIZED = "AUTHORIZED"
    ALLOCATED = "ALLOCATED"
    READY = "READY"
    EXECUTING = "EXECUTING"
    PAUSED = "PAUSED"
    OBSERVING = "OBSERVING"
    VERIFYING = "VERIFYING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    ROLLING_BACK = "ROLLING_BACK"
    ROLLED_BACK = "ROLLED_BACK"
    RECOVERING = "RECOVERING"
    RECOVERED = "RECOVERED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    SUPERSEDED = "SUPERSEDED"


# Legal State Machine Transitions (Phase 2)
ALLOWED_TRANSACTION_TRANSITIONS: dict[TransactionStatus, set[TransactionStatus]] = {
    TransactionStatus.CREATED: {
        TransactionStatus.PREPARING,
        TransactionStatus.CANCELLED,
        TransactionStatus.SUPERSEDED,
    },
    TransactionStatus.PREPARING: {
        TransactionStatus.PREFLIGHT,
        TransactionStatus.BLOCKED,
        TransactionStatus.CANCELLED,
    },
    TransactionStatus.PREFLIGHT: {
        TransactionStatus.BLOCKED,
        TransactionStatus.AWAITING_APPROVAL,
        TransactionStatus.AUTHORIZED,
        TransactionStatus.CANCELLED,
        TransactionStatus.SUPERSEDED,
    },
    TransactionStatus.BLOCKED: {
        TransactionStatus.PREFLIGHT,  # Retry pre-flight if unblocked
        TransactionStatus.CANCELLED,
        TransactionStatus.SUPERSEDED,
    },
    TransactionStatus.AWAITING_APPROVAL: {
        TransactionStatus.AUTHORIZED,
        TransactionStatus.BLOCKED,
        TransactionStatus.CANCELLED,
        TransactionStatus.EXPIRED,
    },
    TransactionStatus.AUTHORIZED: {
        TransactionStatus.ALLOCATED,
        TransactionStatus.BLOCKED,
        TransactionStatus.CANCELLED,
    },
    TransactionStatus.ALLOCATED: {
        TransactionStatus.READY,
        TransactionStatus.BLOCKED,
        TransactionStatus.CANCELLED,
    },
    TransactionStatus.READY: {
        TransactionStatus.EXECUTING,
        TransactionStatus.EXPIRED,
        TransactionStatus.CANCELLED,
        TransactionStatus.BLOCKED,
    },
    TransactionStatus.EXECUTING: {
        TransactionStatus.PAUSED,
        TransactionStatus.OBSERVING,
        TransactionStatus.FAILED,
        TransactionStatus.UNKNOWN,
        TransactionStatus.CANCELLED,
        TransactionStatus.ROLLING_BACK,
    },
    TransactionStatus.PAUSED: {
        TransactionStatus.EXECUTING,
        TransactionStatus.CANCELLED,
    },
    TransactionStatus.OBSERVING: {
        TransactionStatus.VERIFYING,
        TransactionStatus.FAILED,
        TransactionStatus.UNKNOWN,
    },
    TransactionStatus.VERIFYING: {
        TransactionStatus.SUCCEEDED,
        TransactionStatus.FAILED,
        TransactionStatus.UNKNOWN,
        TransactionStatus.ROLLING_BACK,
    },
    TransactionStatus.FAILED: {
        TransactionStatus.ROLLING_BACK,
        TransactionStatus.RECOVERING,
    },
    TransactionStatus.UNKNOWN: {
        TransactionStatus.RECOVERING,
        TransactionStatus.SUCCEEDED,
        TransactionStatus.FAILED,
    },
    TransactionStatus.ROLLING_BACK: {
        TransactionStatus.ROLLED_BACK,
        TransactionStatus.FAILED,
        TransactionStatus.RECOVERING,
    },
    TransactionStatus.RECOVERING: {
        TransactionStatus.RECOVERED,
        TransactionStatus.FAILED,
    },
    TransactionStatus.SUCCEEDED: set(),
    TransactionStatus.ROLLED_BACK: set(),
    TransactionStatus.RECOVERED: set(),
    TransactionStatus.CANCELLED: set(),
    TransactionStatus.EXPIRED: set(),
    TransactionStatus.SUPERSEDED: set(),
}


class VerificationState(str, Enum):
    """Outcome verification state."""
    NOT_STARTED = "NOT_STARTED"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"
    INCONCLUSIVE = "INCONCLUSIVE"


class OutcomeType(str, Enum):
    """Auditable final classification of the transaction outcome."""
    FULL_SUCCESS = "FULL_SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class TargetType(str, Enum):
    """Explicit category of the bound target entity."""
    FILE = "FILE"
    SERVICE = "SERVICE"
    DATABASE = "DATABASE"
    CONTAINER = "CONTAINER"
    ENDPOINT = "ENDPOINT"
    WORKFLOW = "WORKFLOW"
    DEVICE = "DEVICE"
    HOST = "HOST"
    MEMORY = "MEMORY"
    RESOURCE = "RESOURCE"
    MACHINE = "MACHINE"


class TargetBinding(BaseModel):
    """Explicitly bound target entity preventing ambiguous execution (Phase 10)."""
    model_config = ConfigDict(extra="ignore")

    target_type: TargetType = TargetType.SERVICE
    target_id: str
    target_uri: str = ""
    environment: str = "development"
    metadata: dict[str, Any] = Field(default_factory=dict)


class PreflightCheckResult(BaseModel):
    """Individual gate check result within the 18-point pre-flight matrix (Phase 3)."""
    model_config = ConfigDict(extra="ignore")

    gate_name: str
    passed: bool
    reason: str = ""
    is_blocking: bool = True
    latency_ms: float = 0.0
    checked_at: datetime = Field(default_factory=_now_utc)


class ActionObservation(BaseModel):
    """Empirical telemetry captured during/after execution (Phase 15)."""
    model_config = ConfigDict(extra="ignore")

    observation_id: str = Field(default_factory=lambda: _uuid_hex("obs"))
    source: str = "ToolExecutor"  # ToolExecutor, RustRuntime, SystemState, Telemetry
    timestamp: datetime = Field(default_factory=_now_utc)
    exit_code: int | None = 0
    raw_snippet: str = ""
    telemetry_metrics: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)


class PostCondition(BaseModel):
    """Structured post-condition requirement for verification (Phase 16)."""
    model_config = ConfigDict(extra="ignore")

    condition_id: str = Field(default_factory=lambda: _uuid_hex("cnd"))
    description: str
    target_path: str = ""
    expected_state: Any = None
    actual_state: Any = None
    is_satisfied: bool = False
    verification_method: str = "probe"  # probe, telemetry, api_check, file_hash


class SagaStep(BaseModel):
    """Step in a multi-action transaction saga (Phase 21)."""
    model_config = ConfigDict(extra="ignore")

    step_index: int
    name: str
    action_reference: str
    target: TargetBinding
    parameters: dict[str, Any] = Field(default_factory=dict)
    compensation_action: str | None = None
    status: TransactionStatus = TransactionStatus.CREATED
    observation: ActionObservation | None = None
    is_completed: bool = False


class ActionTransaction(BaseModel):
    """Authoritative transaction record governing action execution (Phase 1)."""
    model_config = ConfigDict(extra="ignore")

    transaction_id: str = Field(default_factory=lambda: _uuid_hex("txn"))
    decision_id: str
    task_id: str | None = None
    workflow_id: str | None = None
    capability_id: str
    capability_version: str = "1.0.0"
    action_reference: str  # e.g., "tool:kubernetes_scale", "tool:file_writer"

    status: TransactionStatus = TransactionStatus.CREATED
    status_reason: str = ""
    idempotency_key: str
    is_idempotent: bool = True

    target: TargetBinding
    parameters: dict[str, Any] = Field(default_factory=dict)  # Scrubbed of raw secrets

    # Deadlines & Timeouts (Phase 12)
    created_at: datetime = Field(default_factory=_now_utc)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime = Field(default_factory=_now_utc)
    timeout_seconds: float = 30.0
    start_deadline: datetime | None = None
    transaction_deadline: datetime | None = None

    # Authority References (Phases 4 - 7)
    authorization_reference: str | None = None
    approval_reference: str | None = None
    governance_reference: str | None = None
    resource_reference: str | None = None

    # Execution & Verification Artifacts
    preflight_checks: list[PreflightCheckResult] = Field(default_factory=list)
    observations: list[ActionObservation] = Field(default_factory=list)
    postconditions: list[PostCondition] = Field(default_factory=list)
    verification_state: VerificationState = VerificationState.NOT_STARTED
    stability_window_seconds: float = 0.0

    # Outcome & Compensation (Phases 19 - 21)
    outcome_type: OutcomeType | None = None
    outcome_summary: dict[str, Any] = Field(default_factory=dict)
    deviation_score: float = 0.0
    regret_score: float = 0.0
    compensation_action: str | None = None
    rollback_reference: str | None = None
    saga_steps: list[SagaStep] = Field(default_factory=list)

    # Correlation & Audit
    correlation_id: str | None = None
    trace_id: str | None = None
    user_id: str = "default_user"
    provenance: dict[str, Any] = Field(default_factory=dict)

    def can_transition_to(self, target_state: TransactionStatus) -> bool:
        """Verify if the requested state transition is legal."""
        allowed = ALLOWED_TRANSACTION_TRANSITIONS.get(self.status, set())
        return target_state in allowed

    def transition_to(self, target_state: TransactionStatus, reason: str | None = None) -> None:
        """Enforce strict lifecycle transition rule."""
        if not self.can_transition_to(target_state):
            raise ValueError(f"Illegal transaction transition from '{self.status}' to '{target_state}'.")
        self.status = target_state
        if reason is not None:
            self.status_reason = reason
        self.updated_at = _now_utc()
        if target_state == TransactionStatus.EXECUTING and not self.started_at:
            self.started_at = self.updated_at
        elif target_state in (
            TransactionStatus.SUCCEEDED,
            TransactionStatus.FAILED,
            TransactionStatus.ROLLED_BACK,
            TransactionStatus.RECOVERED,
            TransactionStatus.CANCELLED,
            TransactionStatus.EXPIRED,
            TransactionStatus.SUPERSEDED,
        ) and not self.completed_at:
            self.completed_at = self.updated_at

    @property
    def is_expired(self) -> bool:
        """Check whether transaction or execution deadline has elapsed."""
        now = _now_utc()
        if self.transaction_deadline and now > self.transaction_deadline:
            return True
        if self.status == TransactionStatus.READY and self.start_deadline and now > self.start_deadline:
            return True
        return False
