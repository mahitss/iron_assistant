"""Pydantic v2 schemas and enums for Kairo Self-Modeling & Metacognition Engine."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CapabilityState(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    DEGRADED = "DEGRADED"
    RESTRICTED = "RESTRICTED"
    REQUIRES_AUTHORIZATION = "REQUIRES_AUTHORIZATION"
    REQUIRES_APPROVAL = "REQUIRES_APPROVAL"
    TEMPORARILY_DISABLED = "TEMPORARILY_DISABLED"
    UNKNOWN = "UNKNOWN"


class LimitationCategory(str, Enum):
    KNOWLEDGE = "KNOWLEDGE"
    CAPABILITY = "CAPABILITY"
    PERMISSION = "PERMISSION"
    AUTHORIZATION = "AUTHORIZATION"
    RESOURCE = "RESOURCE"
    NETWORK = "NETWORK"
    TOOL = "TOOL"
    POLICY = "POLICY"
    CONTEXT = "CONTEXT"
    TIME = "TIME"
    DATA = "DATA"
    VERIFICATION = "VERIFICATION"


class LimitationSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    BLOCKING = "BLOCKING"


class LimitationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    RESOLVED = "RESOLVED"
    MITIGATED = "MITIGATED"
    ACCEPTED = "ACCEPTED"


class KnowledgeCategory(str, Enum):
    KNOWN = "KNOWN"
    SUPPORTED = "SUPPORTED"
    UNCERTAIN = "UNCERTAIN"
    UNKNOWN = "UNKNOWN"
    CONTRADICTED = "CONTRADICTED"
    STALE = "STALE"


class UncertaintyType(str, Enum):
    MISSING_DATA = "MISSING_DATA"
    CONFLICTING_DATA = "CONFLICTING_DATA"
    STALE_DATA = "STALE_DATA"
    AMBIGUITY = "AMBIGUITY"
    MODEL_UNCERTAINTY = "MODEL_UNCERTAINTY"
    PREDICTION_UNCERTAINTY = "PREDICTION_UNCERTAINTY"
    TOOL_UNCERTAINTY = "TOOL_UNCERTAINTY"
    ENVIRONMENT_UNCERTAINTY = "ENVIRONMENT_UNCERTAINTY"


class AssumptionImpact(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ExecutionReadiness(str, Enum):
    READY = "READY"
    BLOCKED = "BLOCKED"
    WAITING = "WAITING"
    NEEDS_APPROVAL = "NEEDS_APPROVAL"
    NEEDS_AUTHORIZATION = "NEEDS_AUTHORIZATION"
    NEEDS_INFORMATION = "NEEDS_INFORMATION"
    NEEDS_VERIFICATION = "NEEDS_VERIFICATION"


class TaskState(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"


class ActionAuthority(str, Enum):
    UNAUTHORIZED = "UNAUTHORIZED"
    AUTHORIZED = "AUTHORIZED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    APPROVED = "APPROVED"
    BLOCKED = "BLOCKED"


class FailureType(str, Enum):
    TOOL_FAILURE = "TOOL_FAILURE"
    NETWORK_FAILURE = "NETWORK_FAILURE"
    AUTH_FAILURE = "AUTH_FAILURE"
    POLICY_BLOCK = "POLICY_BLOCK"
    INVALID_INPUT = "INVALID_INPUT"
    TIMEOUT = "TIMEOUT"
    RESOURCE_LIMIT = "RESOURCE_LIMIT"
    VERIFICATION_FAILURE = "VERIFICATION_FAILURE"
    UNKNOWN_FAILURE = "UNKNOWN_FAILURE"


class FailureCertainty(str, Enum):
    KNOWN = "KNOWN"
    SUSPECTED = "SUSPECTED"
    UNKNOWN = "UNKNOWN"


class TaskOrigin(str, Enum):
    USER = "USER"
    POLICY = "POLICY"
    AUTOMATION = "AUTOMATION"
    SYSTEM = "SYSTEM"
    RECOVERY = "RECOVERY"
    APPROVED_PROACTIVE_ACTION = "APPROVED_PROACTIVE_ACTION"


# =============================================================================
# DATA SCHEMAS
# =============================================================================

class CapabilitySchema(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    name: str
    category: str
    description: str
    state: CapabilityState = CapabilityState.AVAILABLE
    tools: List[str] = Field(default_factory=list)
    services: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    confidence: float = 1.0
    degradation_reason: Optional[str] = None
    alternatives: List[str] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SystemLimitationSchema(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    limitation_id: str
    category: LimitationCategory
    description: str
    scope: str = "GLOBAL"
    severity: LimitationSeverity = LimitationSeverity.MEDIUM
    source: str = "SYSTEM"
    status: LimitationStatus = LimitationStatus.ACTIVE
    mitigation_suggestion: Optional[str] = None
    detected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    resolved_at: Optional[datetime] = None


class KnowledgeStateSchema(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    subject: str
    category: KnowledgeCategory = KnowledgeCategory.KNOWN
    confidence: float = 1.0
    provenance: Dict[str, Any] = Field(default_factory=dict)
    is_verified: bool = False
    evidence_count: int = 1
    last_verified: Optional[datetime] = None
    freshness_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class UncertaintySchema(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    subject: str
    uncertainty_type: UncertaintyType
    confidence: float = 0.5
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    impact: str = "MEDIUM"
    resolution_status: str = "UNRESOLVED"
    identified_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AssumptionSchema(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    assumption_id: str
    statement: str
    originating_goal_id: Optional[str] = None
    impact: AssumptionImpact = AssumptionImpact.MEDIUM
    is_validated: bool = False
    validation_evidence: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ActionReadinessSchema(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    action_name: str
    readiness: ExecutionReadiness = ExecutionReadiness.READY
    required_capabilities: List[str] = Field(default_factory=list)
    missing_capabilities: List[str] = Field(default_factory=list)
    authority_state: ActionAuthority = ActionAuthority.AUTHORIZED
    policy_permitted: bool = True
    preconditions_met: bool = True
    blocking_reasons: List[str] = Field(default_factory=list)
    risk_level: str = "LOW"


class ExecutionFailureSchema(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    failure_id: str
    task_id: Optional[str] = None
    action: str
    failure_type: FailureType = FailureType.UNKNOWN_FAILURE
    certainty: FailureCertainty = FailureCertainty.KNOWN
    cause: str
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    recoverability: str = "RECOVERABLE"  # RECOVERABLE, NON_RECOVERABLE, UNKNOWN
    retry_count: int = 0
    max_retries: int = 3
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ReflectionRecordSchema(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    reflection_id: str
    goal: str
    attempted: str
    worked: List[str] = Field(default_factory=list)
    failed: List[str] = Field(default_factory=list)
    verified: List[str] = Field(default_factory=list)
    remaining_uncertainties: List[str] = Field(default_factory=list)
    lessons: List[str] = Field(default_factory=list)
    corrections_applied: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ResourceStateSchema(BaseModel):
    compute_pressure: str = "NORMAL"  # LOW, NORMAL, HIGH, EXHAUSTED
    memory_pressure: str = "NORMAL"
    latency_ms: float = 45.0
    api_budget_remaining_percent: float = 100.0
    rate_limited_tools: List[str] = Field(default_factory=list)
    active_tokens: int = 0
    cost_usd: float = 0.0


class SelfModelSchema(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    model_id: str
    version: str = "1.0.0"
    capabilities: Dict[str, CapabilitySchema] = Field(default_factory=dict)
    limitations: List[SystemLimitationSchema] = Field(default_factory=list)
    active_goals: List[Dict[str, Any]] = Field(default_factory=list)
    active_tasks: List[Dict[str, Any]] = Field(default_factory=list)
    current_state: str = "IDLE"  # IDLE, PLANNING, EXECUTING, WAITING, REFLECTING, ERROR
    knowledge_summary: Dict[str, int] = Field(default_factory=dict)
    uncertainty_count: int = 0
    resource_state: ResourceStateSchema = Field(default_factory=ResourceStateSchema)
    policy_state: Dict[str, Any] = Field(default_factory=dict)
    authorization_state: Dict[str, Any] = Field(default_factory=dict)
    is_operational_metadata_only: bool = True  # Invariant 3: NEVER consciousness
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MetacognitiveMetricsSchema(BaseModel):
    knowledge_accuracy: float = 1.0
    confidence_calibration: float = 1.0
    capability_accuracy: float = 1.0
    tool_reliability: float = 1.0
    goal_completion_rate: float = 1.0
    verification_rate: float = 1.0
    error_recovery_rate: float = 1.0
    overconfidence_count: int = 0
    underconfidence_count: int = 0
    false_capability_claims: int = 0
    false_completion_claims: int = 0
    false_verification_claims: int = 0


class IntrospectionResponseSchema(BaseModel):
    question_type: str  # WHAT_CAN_YOU_DO, WHY_CANT_YOU, HOW_SURE, DID_YOU_DO_IT, WHAT_WENT_WRONG
    grounded_answer: str
    verifiable_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float = 1.0
    limitations_referenced: List[str] = Field(default_factory=list)
