"""Pydantic v2 schemas and enumerations for Kairo Autonomous Resilience,
Recovery, Containment, Adaptive Defense, and Post-Incident Learning (Task 76).

Explicitly separates:
RISK != VULNERABILITY != FAILURE != INCIDENT != CONTAINMENT != MITIGATION != RECOVERY != VERIFICATION != RESIDUAL RISK
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
import uuid

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


def generate_defense_id(prefix: str = "res") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ============================================================================
# 1. ENUMERATIONS & LIFECYCLE STATES
# ============================================================================

class ResilienceState(str, Enum):
    """Lifecycle states for a Resilience Assessment."""
    ASSESSED = "ASSESSED"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    VULNERABLE = "VULNERABLE"
    CRITICAL = "CRITICAL"
    RECOVERING = "RECOVERING"
    VERIFIED = "VERIFIED"
    STALE = "STALE"
    INVALIDATED = "INVALIDATED"


# Valid resilience assessment state transitions
VALID_RESILIENCE_TRANSITIONS: dict[ResilienceState, set[ResilienceState]] = {
    ResilienceState.ASSESSED: {
        ResilienceState.HEALTHY,
        ResilienceState.DEGRADED,
        ResilienceState.VULNERABLE,
        ResilienceState.CRITICAL,
        ResilienceState.STALE,
        ResilienceState.INVALIDATED,
    },
    ResilienceState.HEALTHY: {
        ResilienceState.DEGRADED,
        ResilienceState.VULNERABLE,
        ResilienceState.CRITICAL,
        ResilienceState.STALE,
        ResilienceState.INVALIDATED,
    },
    ResilienceState.DEGRADED: {
        ResilienceState.HEALTHY,
        ResilienceState.CRITICAL,
        ResilienceState.RECOVERING,
        ResilienceState.STALE,
        ResilienceState.INVALIDATED,
    },
    ResilienceState.VULNERABLE: {
        ResilienceState.HEALTHY,
        ResilienceState.DEGRADED,
        ResilienceState.CRITICAL,
        ResilienceState.RECOVERING,
        ResilienceState.STALE,
        ResilienceState.INVALIDATED,
    },
    ResilienceState.CRITICAL: {
        ResilienceState.RECOVERING,
        ResilienceState.DEGRADED,
        ResilienceState.STALE,
        ResilienceState.INVALIDATED,
    },
    ResilienceState.RECOVERING: {
        ResilienceState.VERIFIED,
        ResilienceState.DEGRADED,
        ResilienceState.CRITICAL,
        ResilienceState.INVALIDATED,
    },
    ResilienceState.VERIFIED: {
        ResilienceState.HEALTHY,
        ResilienceState.DEGRADED,
        ResilienceState.STALE,
        ResilienceState.INVALIDATED,
    },
    ResilienceState.STALE: {
        ResilienceState.ASSESSED,
        ResilienceState.INVALIDATED,
    },
    ResilienceState.INVALIDATED: {
        ResilienceState.ASSESSED,
    },
}


class RecoveryLifecycleState(str, Enum):
    """Explicit 17-state lifecycle for recovery operations."""
    DETECTED = "DETECTED"
    ASSESSED = "ASSESSED"
    CONTAINMENT_PLANNED = "CONTAINMENT_PLANNED"
    CONTAINMENT_PENDING_APPROVAL = "CONTAINMENT_PENDING_APPROVAL"
    CONTAINMENT_EXECUTING = "CONTAINMENT_EXECUTING"
    CONTAINED = "CONTAINED"
    RECOVERY_PLANNED = "RECOVERY_PLANNED"
    RECOVERY_PENDING_APPROVAL = "RECOVERY_PENDING_APPROVAL"
    RECOVERY_EXECUTING = "RECOVERY_EXECUTING"
    RECOVERY_VERIFICATION = "RECOVERY_VERIFICATION"
    RECOVERY_MONITORING = "RECOVERY_MONITORING"
    RECOVERED = "RECOVERED"
    PARTIALLY_RECOVERED = "PARTIALLY_RECOVERED"
    RECOVERY_FAILED = "RECOVERY_FAILED"
    ROLLED_BACK = "ROLLED_BACK"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"
    ABORTED = "ABORTED"


# Valid recovery lifecycle state transitions
VALID_RECOVERY_TRANSITIONS: dict[RecoveryLifecycleState, set[RecoveryLifecycleState]] = {
    RecoveryLifecycleState.DETECTED: {
        RecoveryLifecycleState.ASSESSED,
        RecoveryLifecycleState.ABORTED,
        RecoveryLifecycleState.HUMAN_REQUIRED,
    },
    RecoveryLifecycleState.ASSESSED: {
        RecoveryLifecycleState.CONTAINMENT_PLANNED,
        RecoveryLifecycleState.RECOVERY_PLANNED,
        RecoveryLifecycleState.HUMAN_REQUIRED,
        RecoveryLifecycleState.ABORTED,
    },
    RecoveryLifecycleState.CONTAINMENT_PLANNED: {
        RecoveryLifecycleState.CONTAINMENT_PENDING_APPROVAL,
        RecoveryLifecycleState.CONTAINMENT_EXECUTING,
        RecoveryLifecycleState.HUMAN_REQUIRED,
        RecoveryLifecycleState.ABORTED,
    },
    RecoveryLifecycleState.CONTAINMENT_PENDING_APPROVAL: {
        RecoveryLifecycleState.CONTAINMENT_EXECUTING,
        RecoveryLifecycleState.HUMAN_REQUIRED,
        RecoveryLifecycleState.ABORTED,
    },
    RecoveryLifecycleState.CONTAINMENT_EXECUTING: {
        RecoveryLifecycleState.CONTAINED,
        RecoveryLifecycleState.RECOVERY_FAILED,
        RecoveryLifecycleState.HUMAN_REQUIRED,
        RecoveryLifecycleState.ABORTED,
    },
    RecoveryLifecycleState.CONTAINED: {
        RecoveryLifecycleState.RECOVERY_PLANNED,
        RecoveryLifecycleState.RECOVERY_PENDING_APPROVAL,
        RecoveryLifecycleState.RECOVERY_EXECUTING,
        RecoveryLifecycleState.HUMAN_REQUIRED,
        RecoveryLifecycleState.ABORTED,
    },
    RecoveryLifecycleState.RECOVERY_PLANNED: {
        RecoveryLifecycleState.RECOVERY_PENDING_APPROVAL,
        RecoveryLifecycleState.RECOVERY_EXECUTING,
        RecoveryLifecycleState.HUMAN_REQUIRED,
        RecoveryLifecycleState.ABORTED,
    },
    RecoveryLifecycleState.RECOVERY_PENDING_APPROVAL: {
        RecoveryLifecycleState.RECOVERY_EXECUTING,
        RecoveryLifecycleState.HUMAN_REQUIRED,
        RecoveryLifecycleState.ABORTED,
    },
    RecoveryLifecycleState.RECOVERY_EXECUTING: {
        RecoveryLifecycleState.RECOVERY_VERIFICATION,
        RecoveryLifecycleState.RECOVERY_FAILED,
        RecoveryLifecycleState.ROLLED_BACK,
        RecoveryLifecycleState.HUMAN_REQUIRED,
        RecoveryLifecycleState.ABORTED,
    },
    RecoveryLifecycleState.RECOVERY_VERIFICATION: {
        RecoveryLifecycleState.RECOVERY_MONITORING,
        RecoveryLifecycleState.RECOVERED,
        RecoveryLifecycleState.PARTIALLY_RECOVERED,
        RecoveryLifecycleState.RECOVERY_FAILED,
        RecoveryLifecycleState.ROLLED_BACK,
        RecoveryLifecycleState.HUMAN_REQUIRED,
    },
    RecoveryLifecycleState.RECOVERY_MONITORING: {
        RecoveryLifecycleState.RECOVERED,
        RecoveryLifecycleState.PARTIALLY_RECOVERED,
        RecoveryLifecycleState.RECOVERY_FAILED,
        RecoveryLifecycleState.HUMAN_REQUIRED,
    },
    RecoveryLifecycleState.RECOVERED: set(),
    RecoveryLifecycleState.PARTIALLY_RECOVERED: {
        RecoveryLifecycleState.RECOVERY_PLANNED,
        RecoveryLifecycleState.HUMAN_REQUIRED,
    },
    RecoveryLifecycleState.RECOVERY_FAILED: {
        RecoveryLifecycleState.ROLLED_BACK,
        RecoveryLifecycleState.HUMAN_REQUIRED,
        RecoveryLifecycleState.RECOVERY_PLANNED,
    },
    RecoveryLifecycleState.ROLLED_BACK: {
        RecoveryLifecycleState.HUMAN_REQUIRED,
        RecoveryLifecycleState.RECOVERY_PLANNED,
        RecoveryLifecycleState.ABORTED,
    },
    RecoveryLifecycleState.HUMAN_REQUIRED: {
        RecoveryLifecycleState.RECOVERY_PLANNED,
        RecoveryLifecycleState.RECOVERY_EXECUTING,
        RecoveryLifecycleState.ABORTED,
    },
    RecoveryLifecycleState.ABORTED: set(),
}


class ResilienceDimensionType(str, Enum):
    """The 12 distinct dimensions of resilience."""
    REDUNDANCY = "redundancy"
    ISOLATION = "isolation"
    RECOVERABILITY = "recoverability"
    ADAPTABILITY = "adaptability"
    OBSERVABILITY = "observability"
    FAULT_TOLERANCE = "fault_tolerance"
    RESOURCE_SLACK = "resource_slack"
    DEPENDENCY_DIVERSITY = "dependency_diversity"
    RECOVERY_SPEED = "recovery_speed"
    ROLLBACK_CAPABILITY = "rollback_capability"
    HUMAN_FALLBACK = "human_fallback"
    CONTAINMENT_STRENGTH = "containment_strength"


class ResilienceGapType(str, Enum):
    """The 12 formal resilience gaps."""
    NO_REDUNDANCY = "no_redundancy"
    SINGLE_POINT_OF_FAILURE = "single_point_of_failure"
    WEAK_CONTAINMENT = "weak_containment"
    SLOW_RECOVERY = "slow_recovery"
    MISSING_ROLLBACK = "missing_rollback"
    INSUFFICIENT_OBSERVABILITY = "insufficient_observability"
    UNKNOWN_DEPENDENCY = "unknown_dependency"
    EXCESSIVE_COUPLING = "excessive_coupling"
    SCARCE_RESOURCE = "scarce_resource"
    UNTESTED_RECOVERY_PATH = "untested_recovery_path"
    UNVERIFIED_FALLBACK = "unverified_fallback"
    STALE_RECOVERY_PROCEDURE = "stale_recovery_procedure"


class RedundancyType(str, Enum):
    """Redundancy knowledge status."""
    KNOWN_REDUNDANCY = "KNOWN_REDUNDANCY"
    REDUNDANCY_UNKNOWN = "REDUNDANCY_UNKNOWN"
    NO_REDUNDANCY = "NO_REDUNDANCY"


class RedundancyBackupMode(str, Enum):
    """Backup mechanisms available for a component."""
    ACTIVE_BACKUP = "active_backup"
    PASSIVE_BACKUP = "passive_backup"
    ALTERNATIVE_SERVICE = "alternative_service"
    ALTERNATIVE_WORKFLOW = "alternative_workflow"
    MANUAL_FALLBACK = "manual_fallback"
    SUBSTITUTE_RESOURCE = "substitute_resource"


class RecoveryStrategyType(str, Enum):
    """The 12 supported recovery strategies."""
    ROLLBACK = "ROLLBACK"
    FAILOVER = "FAILOVER"
    ISOLATION = "ISOLATION"
    RESTART = "RESTART"
    RESOURCE_REALLOCATION = "RESOURCE_REALLOCATION"
    DEGRADED_MODE = "DEGRADED_MODE"
    FALLBACK_WORKFLOW = "FALLBACK_WORKFLOW"
    REDUNDANCY_ACTIVATION = "REDUNDANCY_ACTIVATION"
    RATE_LIMITING = "RATE_LIMITING"
    LOAD_SHEDDING = "LOAD_SHEDDING"
    MANUAL_HANDOFF = "MANUAL_HANDOFF"
    SAFE_STOP = "SAFE_STOP"


class KnowledgeLifecycleState(str, Enum):
    """Epistemic lifecycle for learned recovery patterns and dependency insights."""
    OBSERVED = "OBSERVED"
    HYPOTHESIZED = "HYPOTHESIZED"
    VALIDATED = "VALIDATED"
    TRUSTED = "TRUSTED"


# ============================================================================
# 2. CORE ASSESSMENT & GAP SCHEMAS
# ============================================================================

class ResilienceDimensionScore(BaseModel):
    """Structured score for a single resilience dimension with explicit evidence."""
    dimension: ResilienceDimensionType
    score: float = Field(ge=0.0, le=1.0, description="Normalized resilience score from 0.0 (fragile) to 1.0 (resilient)")
    evidence: list[str] = Field(default_factory=list, description="Concrete observations and metric findings")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class ResilienceScorecard(BaseModel):
    """Interpretable multi-dimensional resilience evaluation."""
    dimensions: dict[str, ResilienceDimensionScore] = Field(
        default_factory=dict,
        description="Dictionary mapping dimension name to ResilienceDimensionScore"
    )
    overall_resilience_index: float = Field(ge=0.0, le=1.0, description="Weighted composite resilience index")
    rationale: str = Field(description="Human-readable synthesis explaining the score")
    bottleneck_dimensions: list[ResilienceDimensionType] = Field(
        default_factory=list,
        description="Dimensions dragging down resilience below threshold"
    )


class ResilienceGap(BaseModel):
    """An identified weakness or resilience deficiency in the system."""
    gap_id: str = Field(default_factory=lambda: generate_defense_id("gap"))
    gap_type: ResilienceGapType
    affected_scope: str
    target_entity: str
    severity: str = Field(default="MEDIUM", description="LOW | MEDIUM | HIGH | CRITICAL")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    remediation_candidate: str
    provenance: dict[str, Any] = Field(default_factory=dict)
    detected_at: datetime = Field(default_factory=utc_now)


# ============================================================================
# 3. CONTAINMENT & RECOVERY PATH SCHEMAS
# ============================================================================

class ContainmentPoint(BaseModel):
    """Evaluated containment barrier along a risk cascade path."""
    point_id: str = Field(default_factory=lambda: generate_defense_id("cpt"))
    entity_id: str
    sequence_idx: int
    affected_scope: str
    expected_containment_strength: float = Field(ge=0.0, le=1.0)
    reversibility: bool = True
    collateral_impact: str = Field(default="LOW", description="NONE | LOW | MEDIUM | HIGH")
    required_permissions: list[str] = Field(default_factory=list)
    resource_requirements: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    recommendation_rank: int = 1
    isolation_method: str = Field(default="CIRCUIT_BREAKER", description="CIRCUIT_BREAKER | TRAFFIC_SHED | RATE_LIMIT | PROCESS_ISOLATION")


class RecoveryAction(BaseModel):
    """Specific step within a recovery path."""
    action_id: str = Field(default_factory=lambda: generate_defense_id("act"))
    sequence_order: int
    action_type: str = Field(description="E.g., FAILOVER_SWITCH, CONTAINER_RESTART, CACHE_WARM, ROUTE_DRAIN")
    target_entity: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    required_permission: str = Field(default="EXECUTE")
    rollback_action: str | None = None
    rollback_parameters: dict[str, Any] = Field(default_factory=dict)
    is_idempotent: bool = True
    expected_duration_seconds: float = 30.0


class RecoveryPath(BaseModel):
    """Actionable candidate recovery strategy."""
    recovery_path_id: str = Field(default_factory=lambda: generate_defense_id("path"))
    strategy_type: RecoveryStrategyType
    trigger: str
    target: str
    prerequisite_state: dict[str, Any] = Field(default_factory=dict)
    actions: list[RecoveryAction] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list, description="Entities that must be healthy before execution")
    expected_duration_seconds: float = 60.0
    min_plausible_duration_seconds: float = 30.0
    max_plausible_duration_seconds: float = 180.0
    expected_impact: str = Field(default="LOW", description="LOW | MEDIUM | HIGH")
    rollback_possibility: bool = True
    required_permissions: list[str] = Field(default_factory=lambda: ["EXECUTE"])
    required_resources: dict[str, Any] = Field(default_factory=dict)
    verification_method: str = Field(default="HEALTH_CHECK_AND_SYNTHETIC_PROBE")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    provenance: dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# 4. VERIFICATION, RESIDUAL RISK & HANDOFF SCHEMAS
# ============================================================================

class DeterministicVerificationCheck(BaseModel):
    """Rigorous non-LLM health check for recovery validation."""
    check_id: str = Field(default_factory=lambda: generate_defense_id("chk"))
    check_type: str = Field(description="HEALTH_PROBE | CONTRACT_TEST | METRIC_THRESHOLD | DEPENDENCY_STATUS")
    target_entity: str
    metric_name: str
    expected_value: Any
    actual_value: Any = None
    passed: bool = False
    deterministic: bool = True
    message: str = ""
    checked_at: datetime = Field(default_factory=utc_now)


class ResidualRiskReport(BaseModel):
    """Account of remaining risk post-containment or post-recovery."""
    assessment_id: str
    remaining_vulnerabilities: list[str] = Field(default_factory=list)
    remaining_dependency_risk: list[str] = Field(default_factory=list)
    unresolved_gaps: list[str] = Field(default_factory=list)
    reduced_capacity: float = Field(default=0.0, ge=0.0, le=1.0, description="Fraction of capacity currently impaired")
    degraded_functionality: list[str] = Field(default_factory=list)
    uncertainty: float = Field(default=0.2, ge=0.0, le=1.0)
    summary: str = Field(description="Summary message indicating what risk remains")
    reported_at: datetime = Field(default_factory=utc_now)


class HumanHandoffPacket(BaseModel):
    """Structured handoff dossier when autonomous safe recovery cannot proceed."""
    incident_id: str
    what_happened: str
    what_is_affected: list[str]
    what_has_been_contained: list[str]
    what_is_unknown: list[str]
    options: list[str]
    recommended_next_step: str
    approval_needed: str
    priority: str = Field(default="HIGH", description="MEDIUM | HIGH | CRITICAL")
    created_at: datetime = Field(default_factory=utc_now)


# ============================================================================
# 5. RECOVERY PLAN & EXECUTION SCHEMAS
# ============================================================================

class RecoveryExecutionStep(BaseModel):
    """Execution log for an individual recovery step."""
    step_id: str = Field(default_factory=lambda: generate_defense_id("step"))
    plan_id: str
    phase: str = Field(description="CONTAINMENT | RECOVERY | VERIFICATION | ROLLBACK")
    action_id: str
    state: str = Field(default="PENDING", description="PENDING | RUNNING | COMPLETED | FAILED | SKIPPED | ROLLED_BACK")
    started_at: datetime | None = None
    completed_at: datetime | None = None
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    rollback_performed: bool = False


class RecoveryPlan(BaseModel):
    """Full structured recovery blueprint ready for decisioning & execution."""
    plan_id: str = Field(default_factory=lambda: generate_defense_id("plan"))
    assessment_id: str
    incident_id: str | None = None
    cascade_id: str | None = None
    state: RecoveryLifecycleState = RecoveryLifecycleState.DETECTED
    selected_strategy: RecoveryStrategyType
    containment_points: list[ContainmentPoint] = Field(default_factory=list)
    recovery_paths: list[RecoveryPath] = Field(default_factory=list)
    execution_order: list[str] = Field(default_factory=list, description="Ordered entity IDs respecting recovery dependencies")
    preconditions: list[str] = Field(default_factory=list)
    verification_criteria: list[DeterministicVerificationCheck] = Field(default_factory=list)
    residual_risk: ResidualRiskReport | None = None
    return_to_normal_plan: str = "Transition out of degraded mode once monitoring passes"
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    approval_id: str | None = None
    approved_by: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


# ============================================================================
# 6. MASTER RESILIENCE ASSESSMENT SCHEMA
# ============================================================================

class ResilienceAssessment(BaseModel):
    """Top-level assessment of system resilience, weak points, and containment paths."""
    resilience_assessment_id: str = Field(default_factory=lambda: generate_defense_id("ass"))
    scope: str = "SYSTEM"
    target: str = "CORE"
    state: ResilienceState = ResilienceState.ASSESSED
    assessment_time: datetime = Field(default_factory=utc_now)
    graph_snapshot_ref: str | None = None
    world_state_ref: str | None = None
    dependency_ref: str | None = None
    scorecard: ResilienceScorecard
    identified_weaknesses: list[str] = Field(default_factory=list)
    gaps: list[ResilienceGap] = Field(default_factory=list)
    recovery_paths: list[RecoveryPath] = Field(default_factory=list)
    containment_controls: list[ContainmentPoint] = Field(default_factory=list)
    residual_risk: ResidualRiskReport | None = None
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    assumptions: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


# ============================================================================
# 7. ADAPTIVE DEFENSE & POST-INCIDENT LEARNING SCHEMAS
# ============================================================================

class PostIncidentLesson(BaseModel):
    """Structured knowledge distilled from incident containment and recovery outcomes."""
    lesson_id: str = Field(default_factory=lambda: generate_defense_id("les"))
    incident_id: str
    recovery_plan_id: str | None = None
    what_was_expected: str
    what_happened: str
    why_it_mattered: str
    what_should_change: str
    status: KnowledgeLifecycleState = KnowledgeLifecycleState.OBSERVED
    learned_at: datetime = Field(default_factory=utc_now)


class AdaptiveDefenseRecommendation(BaseModel):
    """Bounded, safe recommendation to improve structural resilience."""
    recommendation_id: str = Field(default_factory=lambda: generate_defense_id("rec"))
    recommendation_type: str = Field(description="ADD_REDUNDANCY | TIGHTEN_CIRCUIT_BREAKER | INCREASE_MONITORING | REDUCE_COUPLING")
    target_entity: str
    justification: str
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    cost: str = Field(default="LOW", description="LOW | MEDIUM | HIGH")
    reversibility: bool = True
    risk_reduction: float = Field(ge=0.0, le=1.0)
    requires_approval: bool = True
    status: str = "PENDING"
    created_at: datetime = Field(default_factory=utc_now)


class ResilienceTrendMetrics(BaseModel):
    """Historical resilience timing and operational metrics."""
    mttd_seconds: float | None = None  # Mean Time To Detect
    mttc_seconds: float | None = None  # Mean Time To Contain
    mttr_seconds: float | None = None  # Mean Time To Recover
    sample_size: int = 0
    trend_direction: str = "STABLE"  # IMPROVING | DEGRADING | STABLE | INSUFFICIENT_DATA
    recurring_weaknesses: list[str] = Field(default_factory=list)
