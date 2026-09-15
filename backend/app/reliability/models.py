"""Domain models, lifecycle state machines, and contracts for Kairo Reliability (Task 88)."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import uuid
from pydantic import BaseModel, ConfigDict, Field

from app.reliability.taxonomy import FailureSeverity, FailureType


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def generate_id(prefix: str = "rel") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ==============================================================================
# 1. LIFECYCLE STATES & TRANSITION TABLES
# ==============================================================================

class FailureLifecycleState(str, Enum):
    """Explicit 13-state failure lifecycle from detection to resolution or terminal."""

    DETECTED = "DETECTED"
    CLASSIFIED = "CLASSIFIED"
    CORRELATED = "CORRELATED"
    ASSESSING = "ASSESSING"
    RECOVERY_SELECTED = "RECOVERY_SELECTED"
    AUTHORIZING = "AUTHORIZING"
    RECOVERING = "RECOVERING"
    VERIFYING = "VERIFYING"
    RECOVERED = "RECOVERED"

    # Terminal / Escalated States
    UNRECOVERABLE = "UNRECOVERABLE"
    ESCALATED = "ESCALATED"
    ABORTED = "ABORTED"
    EMERGENCY_STOPPED = "EMERGENCY_STOPPED"


VALID_FAILURE_TRANSITIONS: Dict[FailureLifecycleState, Set[FailureLifecycleState]] = {
    FailureLifecycleState.DETECTED: {
        FailureLifecycleState.CLASSIFIED,
        FailureLifecycleState.ABORTED,
        FailureLifecycleState.EMERGENCY_STOPPED,
    },
    FailureLifecycleState.CLASSIFIED: {
        FailureLifecycleState.CORRELATED,
        FailureLifecycleState.ASSESSING,
        FailureLifecycleState.UNRECOVERABLE,
        FailureLifecycleState.ESCALATED,
        FailureLifecycleState.ABORTED,
        FailureLifecycleState.EMERGENCY_STOPPED,
    },
    FailureLifecycleState.CORRELATED: {
        FailureLifecycleState.ASSESSING,
        FailureLifecycleState.RECOVERY_SELECTED,
        FailureLifecycleState.UNRECOVERABLE,
        FailureLifecycleState.ESCALATED,
        FailureLifecycleState.ABORTED,
        FailureLifecycleState.EMERGENCY_STOPPED,
    },
    FailureLifecycleState.ASSESSING: {
        FailureLifecycleState.RECOVERY_SELECTED,
        FailureLifecycleState.UNRECOVERABLE,
        FailureLifecycleState.ESCALATED,
        FailureLifecycleState.ABORTED,
        FailureLifecycleState.EMERGENCY_STOPPED,
    },
    FailureLifecycleState.RECOVERY_SELECTED: {
        FailureLifecycleState.AUTHORIZING,
        FailureLifecycleState.RECOVERING,
        FailureLifecycleState.UNRECOVERABLE,
        FailureLifecycleState.ESCALATED,
        FailureLifecycleState.ABORTED,
        FailureLifecycleState.EMERGENCY_STOPPED,
    },
    FailureLifecycleState.AUTHORIZING: {
        FailureLifecycleState.RECOVERING,
        FailureLifecycleState.ESCALATED,
        FailureLifecycleState.ABORTED,
        FailureLifecycleState.EMERGENCY_STOPPED,
    },
    FailureLifecycleState.RECOVERING: {
        FailureLifecycleState.VERIFYING,
        FailureLifecycleState.RECOVERED,
        FailureLifecycleState.ESCALATED,
        FailureLifecycleState.ABORTED,
        FailureLifecycleState.EMERGENCY_STOPPED,
    },
    FailureLifecycleState.VERIFYING: {
        FailureLifecycleState.RECOVERED,
        FailureLifecycleState.RECOVERING,  # Re-attempt alternative recovery
        FailureLifecycleState.UNRECOVERABLE,
        FailureLifecycleState.ESCALATED,
        FailureLifecycleState.ABORTED,
        FailureLifecycleState.EMERGENCY_STOPPED,
    },
    FailureLifecycleState.RECOVERED: set(),
    FailureLifecycleState.UNRECOVERABLE: set(),
    FailureLifecycleState.ESCALATED: {
        FailureLifecycleState.RECOVERING,  # Manual intervention can re-trigger recovery
        FailureLifecycleState.ABORTED,
    },
    FailureLifecycleState.ABORTED: set(),
    FailureLifecycleState.EMERGENCY_STOPPED: set(),
}


class IncidentLifecycleState(str, Enum):
    """Explicit 7-state lifecycle for grouped failure incidents."""

    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    RECOVERING = "RECOVERING"
    MONITORING = "MONITORING"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"


VALID_INCIDENT_TRANSITIONS: Dict[IncidentLifecycleState, Set[IncidentLifecycleState]] = {
    IncidentLifecycleState.OPEN: {
        IncidentLifecycleState.INVESTIGATING,
        IncidentLifecycleState.RECOVERING,
        IncidentLifecycleState.ESCALATED,
        IncidentLifecycleState.CLOSED,
    },
    IncidentLifecycleState.INVESTIGATING: {
        IncidentLifecycleState.RECOVERING,
        IncidentLifecycleState.ESCALATED,
        IncidentLifecycleState.CLOSED,
    },
    IncidentLifecycleState.RECOVERING: {
        IncidentLifecycleState.MONITORING,
        IncidentLifecycleState.RESOLVED,
        IncidentLifecycleState.ESCALATED,
        IncidentLifecycleState.CLOSED,
    },
    IncidentLifecycleState.MONITORING: {
        IncidentLifecycleState.RESOLVED,
        IncidentLifecycleState.RECOVERING,  # Failure recurred within stability window
        IncidentLifecycleState.ESCALATED,
    },
    IncidentLifecycleState.RESOLVED: {
        IncidentLifecycleState.CLOSED,
        IncidentLifecycleState.OPEN,  # Reopen if incident returns
    },
    IncidentLifecycleState.ESCALATED: {
        IncidentLifecycleState.RECOVERING,
        IncidentLifecycleState.CLOSED,
    },
    IncidentLifecycleState.CLOSED: set(),
}


# ==============================================================================
# 2. STRATEGY & SAFETY CLASSIFICATIONS
# ==============================================================================

class RecoveryStrategyType(str, Enum):
    """The 15 canonical recovery strategies for runtime self-healing."""

    RETRY = "RETRY"
    RECONNECT = "RECONNECT"
    RESTART_COMPONENT = "RESTART_COMPONENT"
    RESTART_PROCESS = "RESTART_PROCESS"
    RECREATE_SANDBOX = "RECREATE_SANDBOX"
    REBUILD_CONNECTION_POOL = "REBUILD_CONNECTION_POOL"
    RELEASE_LEAKED_RESOURCE = "RELEASE_LEAKED_RESOURCE"
    RECONCILE_RESOURCE = "RECONCILE_RESOURCE"
    PAUSE_WORKFLOW = "PAUSE_WORKFLOW"
    RESUME_WORKFLOW = "RESUME_WORKFLOW"
    FAILOVER = "FAILOVER"
    DEGRADE_CAPABILITY = "DEGRADE_CAPABILITY"
    DISABLE_CAPABILITY = "DISABLE_CAPABILITY"
    ROLLBACK_SAFE_STATE = "ROLLBACK_SAFE_STATE"
    ESCALATE = "ESCALATE"


class SafeRecoveryClass(str, Enum):
    """Risk tier of the recovery action determining required approval."""

    READ_ONLY_DIAGNOSTIC = "READ_ONLY_DIAGNOSTIC"
    LOW_RISK_RECOVERY = "LOW_RISK_RECOVERY"
    MODERATE_RECOVERY = "MODERATE_RECOVERY"
    HIGH_RISK_RECOVERY = "HIGH_RISK_RECOVERY"
    DESTRUCTIVE_RECOVERY = "DESTRUCTIVE_RECOVERY"


class VerificationState(str, Enum):
    """Deterministic post-recovery verification status."""

    VERIFIED_RECOVERED = "VERIFIED_RECOVERED"
    RECOVERED_UNVERIFIED = "RECOVERED_UNVERIFIED"
    RECOVERY_FAILED = "RECOVERY_FAILED"
    RECOVERY_UNKNOWN = "RECOVERY_UNKNOWN"


# ==============================================================================
# 3. CORE DOMAIN SCHEMAS
# ==============================================================================

class FailureRecord(BaseModel):
    """Immutable factual record of a detected failure."""

    model_config = ConfigDict(extra="ignore")

    failure_id: str = Field(default_factory=lambda: generate_id("fail"))
    failure_type: FailureType
    component: str
    operation: str = "unspecified"
    severity: FailureSeverity
    state: FailureLifecycleState = FailureLifecycleState.DETECTED
    timestamp: datetime = Field(default_factory=_now_utc)
    correlation_id: str = "unspecified"
    trace_id: Optional[str] = None
    causation_id: Optional[str] = None
    root_cause_candidate: str
    affected_resources: List[str] = Field(default_factory=list)
    affected_executions: List[str] = Field(default_factory=list)
    confidence: float = 0.8
    recoverability: bool = True
    retryability: bool = False
    message: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    fingerprint: str = ""

    def transition_to(self, new_state: FailureLifecycleState) -> None:
        """Validate and apply a lifecycle state transition."""
        valid_targets = VALID_FAILURE_TRANSITIONS.get(self.state, set())
        if new_state not in valid_targets:
            raise ValueError(
                f"Invalid failure transition from {self.state} to {new_state}. Allowed: {valid_targets}"
            )
        self.state = new_state


class RecoveryStrategy(BaseModel):
    """Declared recovery strategy template."""

    model_config = ConfigDict(extra="ignore")

    strategy_id: str = Field(default_factory=lambda: generate_id("strat"))
    strategy_type: RecoveryStrategyType
    risk: SafeRecoveryClass
    required_capability: Optional[str] = None
    resource_cost: Dict[str, float] = Field(default_factory=dict)  # cpu, memory_mb, slots
    authorization_class: str = "STANDARD"
    side_effect_class: str = "SAFE_READ"
    verification_strategy: str = "SYNTHETIC_PROBE"
    max_attempts: int = 3
    cooldown_seconds: float = 5.0
    description: str = ""


class RecoveryExecutionRecord(BaseModel):
    """Log of a concrete recovery execution attempt."""

    model_config = ConfigDict(extra="ignore")

    recovery_id: str = Field(default_factory=lambda: generate_id("rec"))
    failure_id: str
    incident_id: Optional[str] = None
    component: str
    strategy: RecoveryStrategyType
    risk_class: SafeRecoveryClass
    state: FailureLifecycleState = FailureLifecycleState.RECOVERING
    attempt_number: int = 1
    started_at: datetime = Field(default_factory=_now_utc)
    completed_at: Optional[datetime] = None
    authorization_decision_id: Optional[str] = None
    approval_id: Optional[str] = None
    resource_reservation_id: Optional[str] = None
    allocated_resources: Dict[str, Any] = Field(default_factory=dict)
    action_details: Dict[str, Any] = Field(default_factory=dict)
    verification_state: VerificationState = VerificationState.RECOVERY_UNKNOWN
    verification_details: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    is_dry_run: bool = False


class RecoveryEvidenceRecord(BaseModel):
    """Structured forensic evidence bundle for auditability."""

    model_config = ConfigDict(extra="ignore")

    evidence_id: str = Field(default_factory=lambda: generate_id("evi"))
    failure_id: str
    recovery_id: str
    strategy: str
    before_state: Dict[str, Any]
    action_taken: Dict[str, Any]
    after_state: Dict[str, Any]
    verification: Dict[str, Any]
    resource_usage: Dict[str, Any]
    timestamps: Dict[str, str]
    result_status: str
    provenance: Dict[str, Any] = Field(default_factory=dict)


class IncidentRecord(BaseModel):
    """Aggregated incident grouping related failures across a failure window."""

    model_config = ConfigDict(extra="ignore")

    incident_id: str = Field(default_factory=lambda: generate_id("inc"))
    severity: FailureSeverity
    current_state: IncidentLifecycleState = IncidentLifecycleState.OPEN
    root_cause_candidate: str
    affected_components: List[str] = Field(default_factory=list)
    affected_executions: List[str] = Field(default_factory=list)
    affected_resources: List[str] = Field(default_factory=list)
    blast_radius_summary: Dict[str, Any] = Field(default_factory=dict)
    failures: List[str] = Field(default_factory=list)  # List of failure_ids
    recovery_attempts: List[str] = Field(default_factory=list)  # List of recovery_ids
    started_at: datetime = Field(default_factory=_now_utc)
    last_seen_at: datetime = Field(default_factory=_now_utc)
    monitoring_until: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolution_summary: Optional[str] = None
    verification_state: VerificationState = VerificationState.RECOVERY_UNKNOWN
    failure_fingerprint: str = ""

    def transition_to(self, new_state: IncidentLifecycleState) -> None:
        """Validate and apply an incident state transition."""
        valid_targets = VALID_INCIDENT_TRANSITIONS.get(self.current_state, set())
        if new_state not in valid_targets:
            raise ValueError(
                f"Invalid incident transition from {self.current_state} to {new_state}. Allowed: {valid_targets}"
            )
        self.current_state = new_state


class VerificationResult(BaseModel):
    """Structured result of non-LLM deterministic health verification."""

    model_config = ConfigDict(extra="ignore")

    check_id: str = Field(default_factory=lambda: generate_id("vchk"))
    component: str
    state: VerificationState
    probe_name: str
    passed: bool
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=_now_utc)


# ==============================================================================
# 4. FAULT INJECTION & SCENARIO SCHEMAS
# ==============================================================================

class FaultScenario(BaseModel):
    """Named deterministic fault scenario for testing and chaos drills."""

    model_config = ConfigDict(extra="ignore")

    scenario_name: str
    target_component: str
    failure_type: FailureType
    parameters: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = False
    max_invocations: int = 1
    current_invocations: int = 0
    created_at: datetime = Field(default_factory=_now_utc)


class FaultInjectionConfig(BaseModel):
    """Global fault injection configuration (disabled by default)."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = False
    allow_process_kills: bool = False
    allow_network_drops: bool = False
    allow_resource_exhaustion: bool = False
    active_scenarios: Dict[str, FaultScenario] = Field(default_factory=dict)
