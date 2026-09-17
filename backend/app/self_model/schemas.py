"""Canonical schemas and domain models for Kairo Autonomous Self-Model (Task 101).

Implements strict distinctions:
- AVAILABLE != READY
- READY != AUTHORIZED
- AUTHORIZED != SAFE
- SAFE != RELIABLE
- RELIABLE != ALWAYS AVAILABLE
- CAPABLE != CURRENTLY CAPABLE
- INSTALLED != USABLE
- CONFIGURED != VERIFIED
- VERIFIED != PERMANENT
- PREDICTED != OBSERVED
- AGENT CLAIM != FACT
- TOOL SUCCESS != WORLD-STATE SUCCESS
- NO DATA != HEALTHY
- STALE DATA != CURRENT STATE
- UNKNOWN != FALSE
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


def _now_utc() -> str:
    return datetime.now(UTC).isoformat()


class CapabilityReadinessState(str, Enum):
    """Reflects grounded capability operational readiness."""
    UNKNOWN = "UNKNOWN"
    DISCOVERED = "DISCOVERED"
    INSTALLED = "INSTALLED"
    CONFIGURED = "CONFIGURED"
    AVAILABLE = "AVAILABLE"
    READY = "READY"
    DEGRADED = "DEGRADED"
    BLOCKED = "BLOCKED"
    UNAVAILABLE = "UNAVAILABLE"
    DEPRECATED = "DEPRECATED"
    QUARANTINED = "QUARANTINED"
    FAILED = "FAILED"


class FreshnessState(str, Enum):
    """Freshness verification of self-model components."""
    CURRENT = "CURRENT"
    RECENT = "RECENT"
    STALE = "STALE"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"


class AutonomyMode(str, Enum):
    """Derived autonomy mode reflecting aggregate safety and governance constraints."""
    NORMAL = "NORMAL"
    OBSERVATION_ONLY = "OBSERVATION_ONLY"
    ASSISTED = "ASSISTED"
    PROPOSAL_ONLY = "PROPOSAL_ONLY"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    BOUNDED_AUTONOMY = "BOUNDED_AUTONOMY"
    DEGRADED = "DEGRADED"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class FailureCategory(str, Enum):
    """Categorized capability and tool failure domains."""
    CONFIGURATION = "CONFIGURATION"
    DEPENDENCY = "DEPENDENCY"
    AUTHORIZATION = "AUTHORIZATION"
    POLICY = "POLICY"
    RESOURCE = "RESOURCE"
    TIMEOUT = "TIMEOUT"
    NETWORK = "NETWORK"
    PROTOCOL = "PROTOCOL"
    RUNTIME = "RUNTIME"
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    EXTERNAL = "EXTERNAL"
    UNKNOWN = "UNKNOWN"


class ChangeType(str, Enum):
    """Granular delta event types between self-model snapshots."""
    CAPABILITY_STATE_CHANGED = "CAPABILITY_STATE_CHANGED"
    RUNTIME_STATE_CHANGED = "RUNTIME_STATE_CHANGED"
    RESOURCE_STATE_CHANGED = "RESOURCE_STATE_CHANGED"
    ACCESS_STATE_CHANGED = "ACCESS_STATE_CHANGED"
    DEPENDENCY_STATE_CHANGED = "DEPENDENCY_STATE_CHANGED"
    POLICY_STATE_CHANGED = "POLICY_STATE_CHANGED"
    RELIABILITY_STATE_CHANGED = "RELIABILITY_STATE_CHANGED"
    AUTONOMY_STATE_CHANGED = "AUTONOMY_STATE_CHANGED"
    EMERGENCY_STOP_CHANGED = "EMERGENCY_STOP_CHANGED"
    LIMITATION_CHANGED = "LIMITATION_CHANGED"
    UNCERTAINTY_CHANGED = "UNCERTAINTY_CHANGED"


class ReadinessDimensionScore(BaseModel):
    dimension: str
    status: str  # READY, NOT_READY, DEGRADED, UNKNOWN
    evidence: str
    reason: str


class CapabilityAwarenessItem(BaseModel):
    capability_id: str
    name: str
    version: str
    lifecycle_state: str
    readiness_state: CapabilityReadinessState
    health_state: str
    reliability_score: float = Field(ge=0.0, le=1.0, default=1.0)
    consecutive_failures: int = 0
    dimensions: Dict[str, ReadinessDimensionScore] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)
    required_resources: List[str] = Field(default_factory=list)
    requires_approval: bool = False
    security_level: str = "SAFE"
    known_limitations: List[str] = Field(default_factory=list)
    last_verified_at: Optional[str] = None
    last_failure_at: Optional[str] = None
    last_failure_reason: Optional[str] = None
    failure_category: Optional[FailureCategory] = None
    freshness: FreshnessState = FreshnessState.UNKNOWN
    evidence: List[str] = Field(default_factory=list)


class ToolAwarenessItem(BaseModel):
    tool_name: str
    execution_class: str
    capability_id: Optional[str] = None
    requires_approval: bool = False
    risk_level: str = "LOW"
    invocations: int = 0
    success_rate: float = 1.0
    is_available: bool = True
    restrictions: List[str] = Field(default_factory=list)


class RuntimeAwarenessItem(BaseModel):
    runtime_version: str = "0.2.0"
    protocol_version: str = "1.0.0"
    process_health: str = "HEALTHY"
    worker_health: str = "HEALTHY"
    ipc_state: str = "CONNECTED"
    rust_heartbeat_fresh: bool = True
    emergency_stop_active: bool = False
    degraded_modes: List[str] = Field(default_factory=list)
    last_heartbeat_at: Optional[str] = None
    freshness: FreshnessState = FreshnessState.CURRENT


class ResourceAwareness(BaseModel):
    saturation_pct: float = 0.0
    saturation_state: str = "HEALTHY"
    degradation_tier: str = "FULL_FIDELITY"
    total_resources: int = 0
    resource_states: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    freshness: FreshnessState = FreshnessState.CURRENT


class SecurityGovernanceAwareness(BaseModel):
    emergency_stop_active: bool = False
    emergency_stop_reason: Optional[str] = None
    autonomy_mode: AutonomyMode = AutonomyMode.BOUNDED_AUTONOMY
    approval_required_actions: List[str] = Field(default_factory=list)
    pending_approvals_count: int = 0
    blocked_capabilities: List[str] = Field(default_factory=list)
    restricted_operations: List[str] = Field(default_factory=list)
    active_policies: List[str] = Field(default_factory=list)
    freshness: FreshnessState = FreshnessState.CURRENT


class DependencyAwarenessItem(BaseModel):
    dependency_name: str
    dependency_type: str
    status: str  # AVAILABLE, DEGRADED, UNAVAILABLE, UNKNOWN
    affected_capabilities: List[str] = Field(default_factory=list)
    last_verified_at: Optional[str] = None
    evidence: str = "Operational check"


class LimitationItem(BaseModel):
    limitation_id: str
    subject: str
    description: str
    reason: str
    evidence: str
    is_hard_limit: bool = True
    created_at: str = Field(default_factory=_now_utc)


class UncertaintyItem(BaseModel):
    uncertainty_id: str
    subject: str
    reason: str
    evidence: str
    affected_capabilities: List[str] = Field(default_factory=list)
    revalidation_policy: str = "PERIODIC_CHECK"
    created_at: str = Field(default_factory=_now_utc)


class SelfStateChange(BaseModel):
    change_id: str
    change_type: ChangeType
    target_id: str
    old_state: Any
    new_state: Any
    reason: str
    evidence: str
    timestamp: str = Field(default_factory=_now_utc)


class SelfModelAnswers(BaseModel):
    """Strict resolution of all 15 canonical operational questions."""
    q1_capabilities: List[str] = Field(default_factory=list, description="What capabilities do I have?")
    q2_versions: Dict[str, str] = Field(default_factory=dict, description="Which versions are available?")
    q3_ready_capabilities: List[str] = Field(default_factory=list, description="Which capabilities are actually ready?")
    q4_degraded_capabilities: List[str] = Field(default_factory=list, description="Which are degraded?")
    q5_temporarily_unavailable: List[str] = Field(default_factory=list, description="Which are temporarily unavailable?")
    q6_current_resources: ResourceAwareness = Field(default_factory=ResourceAwareness, description="What resources do I currently have?")
    q7_usable_tools: List[str] = Field(default_factory=list, description="What tools can I use?")
    q8_authorized_access: List[str] = Field(default_factory=list, description="What access is currently authorized?")
    q9_actions_requiring_approval: List[str] = Field(default_factory=list, description="Which actions require approval?")
    q10_failing_dependencies: List[str] = Field(default_factory=list, description="Which dependencies are failing?")
    q11_recently_failed_capabilities: List[str] = Field(default_factory=list, description="Which capabilities have recently failed?")
    q12_capability_reliability: Dict[str, float] = Field(default_factory=dict, description="How reliable is each capability?")
    q13_changes_since_last_check: List[SelfStateChange] = Field(default_factory=list, description="What has changed since the last check?")
    q14_limitations: List[LimitationItem] = Field(default_factory=list, description="What do I know about my own limitations?")
    q15_uncertainties: List[UncertaintyItem] = Field(default_factory=list, description="What am I uncertain about?")


class SelfModelSnapshot(BaseModel):
    """Immutable, versioned snapshot of Kairo's internal operational state."""
    snapshot_id: str
    created_at: str = Field(default_factory=_now_utc)
    model_version: str = "1.0.0"
    runtime_version: str = "0.2.0"
    protocol_version: str = "1.0.0"
    autonomy_mode: AutonomyMode = AutonomyMode.BOUNDED_AUTONOMY
    emergency_stop_state: bool = False
    capabilities: Dict[str, CapabilityAwarenessItem] = Field(default_factory=dict)
    tools: Dict[str, ToolAwarenessItem] = Field(default_factory=dict)
    runtime: RuntimeAwarenessItem = Field(default_factory=RuntimeAwarenessItem)
    resources: ResourceAwareness = Field(default_factory=ResourceAwareness)
    security_governance: SecurityGovernanceAwareness = Field(default_factory=SecurityGovernanceAwareness)
    dependencies: Dict[str, DependencyAwarenessItem] = Field(default_factory=dict)
    limitations: List[LimitationItem] = Field(default_factory=list)
    uncertainties: List[UncertaintyItem] = Field(default_factory=list)
    active_missions: List[str] = Field(default_factory=list)
    active_situations: List[str] = Field(default_factory=list)
    answers: SelfModelAnswers = Field(default_factory=SelfModelAnswers)
    confidence_score: float = 1.0
    evidence_references: List[str] = Field(default_factory=list)


class SelfModelDelta(BaseModel):
    """Structured diff between two self-state snapshots."""
    base_snapshot_id: str
    target_snapshot_id: str
    created_at: str = Field(default_factory=_now_utc)
    changes: List[SelfStateChange] = Field(default_factory=list)
    added_limitations: List[LimitationItem] = Field(default_factory=list)
    resolved_limitations: List[LimitationItem] = Field(default_factory=list)
    added_uncertainties: List[UncertaintyItem] = Field(default_factory=list)
    resolved_uncertainties: List[UncertaintyItem] = Field(default_factory=list)


class GroundingVerificationResult(BaseModel):
    """Evidence verification ensuring no fictional self-awareness claims."""
    is_grounded: bool
    total_claims: int
    verified_claims: int
    unverified_claims: List[str] = Field(default_factory=list)
    violations: List[str] = Field(default_factory=list)
    verdict: str
