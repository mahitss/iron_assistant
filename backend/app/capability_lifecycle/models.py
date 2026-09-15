"""Strongly-typed domain models, enums, and schemas for the Kairo Capability Lifecycle Engine (Task 91)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, ConfigDict, Field


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def generate_cl_id(prefix: str = "cap") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ==============================================================================
# 1. ENUMS & TAXONOMIES
# ==============================================================================

class LifecycleState(str, Enum):
    """12 canonical lifecycle progression states."""

    DISCOVERED = "DISCOVERED"
    VALIDATING = "VALIDATING"
    VALIDATED = "VALIDATED"
    SIMULATING = "SIMULATING"
    CANARY = "CANARY"
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    BLOCKED = "BLOCKED"
    DEPRECATED = "DEPRECATED"
    RETIRING = "RETIRING"
    RETIRED = "RETIRED"
    FAILED = "FAILED"


class CapabilityType(str, Enum):
    """Categorization of application-level capabilities."""

    TOOL = "TOOL"
    NATIVE_RUNTIME = "NATIVE_RUNTIME"
    MODEL_PROVIDER = "MODEL_PROVIDER"
    WORKFLOW = "WORKFLOW"
    INTEGRATION = "INTEGRATION"
    COMPOSITE = "COMPOSITE"


class SecurityClassification(str, Enum):
    """Classification of data handling and privilege requirements."""

    INTERNAL = "INTERNAL"
    RESTRICTED = "RESTRICTED"
    CONFIDENTIAL = "CONFIDENTIAL"
    CRITICAL_INFRASTRUCTURE = "CRITICAL_INFRASTRUCTURE"


class CompatibilityClassification(str, Enum):
    """Classification of cross-version or consumer compatibility."""

    FULLY_COMPATIBLE = "FULLY_COMPATIBLE"
    BACKWARD_COMPATIBLE = "BACKWARD_COMPATIBLE"
    FORWARD_COMPATIBLE = "FORWARD_COMPATIBLE"
    PARTIALLY_COMPATIBLE = "PARTIALLY_COMPATIBLE"
    INCOMPATIBLE = "INCOMPATIBLE"
    UNKNOWN = "UNKNOWN"


class SimulationStatus(str, Enum):
    """Verification state evaluated against Task 89 digital twin simulation."""

    SIMULATION_NOT_REQUIRED = "SIMULATION_NOT_REQUIRED"
    SIMULATION_REQUIRED = "SIMULATION_REQUIRED"
    SIMULATION_PASSED = "SIMULATION_PASSED"
    SIMULATION_FAILED = "SIMULATION_FAILED"
    SIMULATION_STALE = "SIMULATION_STALE"


class HealthStatus(str, Enum):
    """Empirical operational health synthesized via Task 90 reliability signals."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNSTABLE = "UNSTABLE"
    UNSAFE = "UNSAFE"
    UNKNOWN = "UNKNOWN"


class DependencyType(str, Enum):
    """Types of dependencies a capability can declare."""

    CAPABILITY = "CAPABILITY"
    TOOL = "TOOL"
    NATIVE_CAPABILITY = "NATIVE_CAPABILITY"
    MODEL_PROVIDER = "MODEL_PROVIDER"
    RUNTIME_FEATURE = "RUNTIME_FEATURE"
    EXTERNAL_SERVICE = "EXTERNAL_SERVICE"


class RolloutState(str, Enum):
    """Progressive deployment states for canary rollouts."""

    INACTIVE = "INACTIVE"
    CANARY_RUNNING = "CANARY_RUNNING"
    PROMOTED = "PROMOTED"
    ROLLED_BACK = "ROLLED_BACK"
    ABORTED = "ABORTED"


# ==============================================================================
# 2. SUPPORTING SUB-MODELS
# ==============================================================================

class CapabilityDependency(BaseModel):
    """Explicit dependency requirement with version constraint."""

    model_config = ConfigDict(extra="ignore")

    dependency_id: str = Field(default_factory=lambda: generate_cl_id("dep"))
    dependency_type: DependencyType = DependencyType.CAPABILITY
    target_id: str
    version_constraint: str = ">=1.0.0"
    is_optional: bool = False
    health_status: HealthStatus = HealthStatus.HEALTHY
    description: str = ""


class ResourceProfile(BaseModel):
    """Bounded resource envelope declared by the capability."""

    model_config = ConfigDict(extra="ignore")

    cpu_cores: float = 0.5
    memory_mb: float = 128.0
    network_bandwidth_kbps: float = 1024.0
    max_concurrency: int = 5
    timeout_seconds: float = 30.0
    estimated_token_cost: Optional[float] = 0.0


class ReliabilityMetadata(BaseModel):
    """Empirical reliability counters maintained by Task 90 integration."""

    model_config = ConfigDict(extra="ignore")

    success_rate: float = 1.0
    total_invocations: int = 0
    total_successes: int = 0
    total_failures: int = 0
    mean_latency_ms: float = 0.0
    last_failure_reason: Optional[str] = None
    consecutive_failures: int = 0
    stability_window_passed: bool = True
    last_evaluated_at: Optional[datetime] = None


# ==============================================================================
# 3. CORE DOMAIN: CAPABILITY & IMMUTABLE VERSION
# ==============================================================================

class CapabilityVersionRecord(BaseModel):
    """Immutable record of an activated or evaluated capability version."""

    model_config = ConfigDict(extra="ignore")

    version_id: str = Field(default_factory=lambda: generate_cl_id("ver"))
    capability_id: str
    version_str: str  # SemVer e.g. "1.2.0"
    major: int = 1
    minor: int = 0
    patch: int = 0
    build_metadata: str = ""
    source_revision: str = "git_head"
    contract_fingerprint: str = ""
    implementation_fingerprint: str = ""
    dependency_fingerprint: str = ""
    supersedes: Optional[str] = None
    superseded_by: Optional[str] = None
    is_active: bool = False
    created_at: datetime = Field(default_factory=_now_utc)
    activated_at: Optional[datetime] = None


class CapabilityMetadata(BaseModel):
    """Authoritative capability entity managing state, versions, and evolution."""

    model_config = ConfigDict(extra="ignore")

    capability_id: str
    name: str
    description: str
    capability_type: CapabilityType = CapabilityType.TOOL
    owner_source: str = "core.kairo"
    version: str = "1.0.0"

    # Cryptographic Fingerprints
    contract_fingerprint: str = ""
    implementation_fingerprint: str = ""
    composite_fingerprint: str = ""

    # Contracts & Constraints
    parameters_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Optional[Dict[str, Any]] = None
    dependencies: List[CapabilityDependency] = Field(default_factory=list)
    required_permissions: List[str] = Field(default_factory=lambda: ["READ"])
    resource_profile: ResourceProfile = Field(default_factory=ResourceProfile)
    security_classification: SecurityClassification = SecurityClassification.INTERNAL

    # State & Health
    lifecycle_state: LifecycleState = LifecycleState.DISCOVERED
    health_state: HealthStatus = HealthStatus.UNKNOWN
    reliability: ReliabilityMetadata = Field(default_factory=ReliabilityMetadata)

    # Rollout & Deprecation
    active_version_id: Optional[str] = None
    canary_version_id: Optional[str] = None
    deprecation_reason: Optional[str] = None
    replacement_capability_id: Optional[str] = None
    sunset_deadline: Optional[datetime] = None
    retirement_reason: Optional[str] = None

    # Audit & Provenance
    created_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)
    last_validated_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None
    provenance: Dict[str, Any] = Field(default_factory=dict)


# ==============================================================================
# 4. LIFECYCLE EVENT & TRANSITION
# ==============================================================================

class LifecycleTransitionEvent(BaseModel):
    """Deterministic, immutable audit record of a lifecycle state transition."""

    model_config = ConfigDict(extra="ignore")

    event_id: str = Field(default_factory=lambda: generate_cl_id("ev"))
    capability_id: str
    version: str
    from_state: LifecycleState
    to_state: LifecycleState
    reason: str
    actor: str = "system"
    correlation_id: str = Field(default_factory=lambda: generate_cl_id("corr"))
    trace_id: Optional[str] = None
    safety_metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=_now_utc)


# ==============================================================================
# 5. COMPATIBILITY & CONFORMANCE
# ==============================================================================

class CompatibilityReport(BaseModel):
    """Comprehensive evaluation across contracts, dependencies, and resources."""

    model_config = ConfigDict(extra="ignore")

    report_id: str = Field(default_factory=lambda: generate_cl_id("comp"))
    capability_id: str
    source_version: str
    target_version: str
    classification: CompatibilityClassification = CompatibilityClassification.UNKNOWN
    contract_compatible: bool = True
    schema_compatible: bool = True
    dependency_compatible: bool = True
    resource_compatible: bool = True
    security_compatible: bool = True
    migration_requirements: List[str] = Field(default_factory=list)
    affected_consumers: List[str] = Field(default_factory=list)
    risk_level: str = "LOW"
    recommendation: str = "PROCEED"
    evaluated_at: datetime = Field(default_factory=_now_utc)


class ConformanceTestVector(BaseModel):
    """Deterministic input vector and expected output assertions."""

    vector_id: str = Field(default_factory=lambda: generate_cl_id("vec"))
    name: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    expected_output_subset: Optional[Dict[str, Any]] = None
    expected_error_class: Optional[str] = None
    timeout_seconds: float = 5.0
    idempotent_assert: bool = False


class ConformanceTestResult(BaseModel):
    """Persistent audit record of a capability conformance test execution."""

    model_config = ConfigDict(extra="ignore")

    run_id: str = Field(default_factory=lambda: generate_cl_id("run"))
    capability_id: str
    version: str
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    unsupported: int = 0
    duration_ms: float = 0.0
    resource_consumption: Dict[str, float] = Field(default_factory=dict)
    failure_details: List[str] = Field(default_factory=list)
    safety_invariants_verified: bool = True
    executed_at: datetime = Field(default_factory=_now_utc)


# ==============================================================================
# 6. CANARY, PROMOTION & ROLLBACK
# ==============================================================================

class CanaryRolloutConfig(BaseModel):
    """Configuration governing progressive traffic shifting."""

    canary_percent: float = Field(default=5.0, ge=1.0, le=50.0)
    canary_duration_seconds: float = Field(default=60.0, ge=10.0)
    max_workloads: int = 100
    error_rate_threshold: float = Field(default=0.05, ge=0.01, le=0.50)
    latency_threshold_ms: float = 500.0
    rollback_threshold: int = 2  # Rollback on 2 consecutive violations


class CanaryRolloutState(BaseModel):
    """Active execution state of a canary rollout."""

    model_config = ConfigDict(extra="ignore")

    rollout_id: str = Field(default_factory=lambda: generate_cl_id("roll"))
    capability_id: str
    target_version: str
    config: CanaryRolloutConfig = Field(default_factory=CanaryRolloutConfig)
    current_percent: float = 0.0
    workloads_routed: int = 0
    errors_encountered: int = 0
    error_rate: float = 0.0
    state: RolloutState = RolloutState.INACTIVE
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    abort_reason: Optional[str] = None


class PromotionGateEvaluation(BaseModel):
    """Structured scorecard evaluating all 11 mandatory promotion gates."""

    model_config = ConfigDict(extra="ignore")

    capability_id: str
    version: str
    gates: Dict[str, bool] = Field(
        default_factory=lambda: {
            "validation_passed": False,
            "conformance_passed": False,
            "dependency_compatibility_passed": False,
            "security_policy_passed": False,
            "governance_policy_passed": False,
            "resource_allocation_available": False,
            "simulation_passed": False,
            "reliability_threshold_passed": False,
            "canary_passed": False,
            "approval_obtained": False,
            "emergency_stop_inactive": False,
        }
    )
    all_passed: bool = False
    blockers: List[str] = Field(default_factory=list)
    evaluated_at: datetime = Field(default_factory=_now_utc)


class RollbackRecord(BaseModel):
    """Audit record capturing safe rollback to a stable target version."""

    model_config = ConfigDict(extra="ignore")

    rollback_id: str = Field(default_factory=lambda: generate_cl_id("rb"))
    capability_id: str
    from_version: str
    to_version: str
    reason: str
    initiated_by: str = "autonomous_safeguard"
    verification_passed: bool = True
    stability_monitored: bool = True
    rolled_back_at: datetime = Field(default_factory=_now_utc)


class DeprecationPlan(BaseModel):
    """Authoritative schedule and migration path for an aging capability."""

    model_config = ConfigDict(extra="ignore")

    plan_id: str = Field(default_factory=lambda: generate_cl_id("depr"))
    capability_id: str
    version: str
    deprecation_reason: str
    replacement_capability_id: Optional[str] = None
    migration_guidance: str = ""
    affected_workflows: List[str] = Field(default_factory=list)
    sunset_deadline: datetime
    is_retired: bool = False
    created_at: datetime = Field(default_factory=_now_utc)
