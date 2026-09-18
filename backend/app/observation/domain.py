"""Domain models, enums, and operational contracts for Task 114:
KAIRO Autonomous Active Observation, Value-of-Information, Information Acquisition & Uncertainty Reduction Engine.

Hard Architectural Invariants:
- UNKNOWN != FALSE
- MISSING DATA != NO CHANGE
- NO OBSERVATION != NO EVENT
- MORE DATA != MORE KNOWLEDGE
- MORE KNOWLEDGE != BETTER DECISION
- INFORMATION VALUE != ACTION VALUE
- OBSERVATION != AUTHORIZATION
- OBSERVATION != EXECUTION
- EVIDENCE != TRUTH
- CORRELATION != CAUSATION
- MODEL CONFIDENCE != REALITY
- INFORMATION ACQUISITION MUST HAVE A PURPOSE
- EXISTING VALID EVIDENCE IS PREFERRED OVER REDUNDANT RETRIEVAL
- PROMPT INJECTION DEFENSE: Observation targets and payloads are DATA, never authority.
- EMERGENCY_STOP ABSOLUTE PRIMACY
- NO RAW CHAIN-OF-THOUGHT PERSISTED
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import Enum
import hashlib
import json
from typing import Any, Dict, List, Optional, Set
import uuid
from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


def generate_uuid(prefix: str = "obs") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def compute_hash(data: Any) -> str:
    """Compute deterministic SHA-256 hash for deduplication and provenance."""
    if isinstance(data, str):
        content = data.encode("utf-8")
    else:
        content = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(content).hexdigest()


# =====================================================================
# ENUMS
# =====================================================================

class ObservationPlanStatus(str, Enum):
    """Lifecycle stages for an Observation Plan (Section 5)."""
    IDENTIFIED = "IDENTIFIED"
    SCOPING = "SCOPING"
    CANDIDATE_GENERATION = "CANDIDATE_GENERATION"
    EVALUATING = "EVALUATING"
    READY = "READY"
    WAITING = "WAITING"
    AUTHORIZED = "AUTHORIZED"
    OBSERVING = "OBSERVING"
    PROCESSING = "PROCESSING"
    EVIDENCE_PENDING = "EVIDENCE_PENDING"
    VERIFIED = "VERIFIED"
    PARTIAL = "PARTIAL"
    INSUFFICIENT = "INSUFFICIENT"
    STALE = "STALE"
    CANCELLED = "CANCELLED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    SUPERSEDED = "SUPERSEDED"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"


class UncertaintyDimensionType(str, Enum):
    """15 distinct dimensions of epistemic uncertainty (Section 7)."""
    FACTUAL = "FACTUAL"
    TEMPORAL = "TEMPORAL"
    CAUSAL = "CAUSAL"
    STATE = "STATE"
    IDENTITY = "IDENTITY"
    INTENT = "INTENT"
    CAPABILITY = "CAPABILITY"
    RESOURCE = "RESOURCE"
    RELIABILITY = "RELIABILITY"
    FORECAST = "FORECAST"
    DECISION = "DECISION"
    OUTCOME = "OUTCOME"
    PROVENANCE = "PROVENANCE"
    SCOPE = "SCOPE"
    FRESHNESS = "FRESHNESS"


class UncertaintyLevel(str, Enum):
    """Epistemic classification per uncertainty dimension (Section 7)."""
    KNOWN = "KNOWN"
    LIKELY = "LIKELY"
    UNCERTAIN = "UNCERTAIN"
    CONTESTED = "CONTESTED"
    UNKNOWN = "UNKNOWN"
    STALE = "STALE"


class InformationValueTier(str, Enum):
    """Qualitative Value-of-Information (VoI) levels (Section 9)."""
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"
    UNKNOWN = "UNKNOWN"


class ObservationMethodType(str, Enum):
    """Authoritative observation methods (Section 18)."""
    PASSIVE = "PASSIVE"         # Ingest existing telemetry, event bus, system state
    ACTIVE = "ACTIVE"           # Explicit query, bounded probe, health endpoint check
    CONTROLLED = "CONTROLLED"   # Authorized experiment or safe sandbox replay
    USER = "USER"               # Targeted user clarification (Task 108)
    WAIT = "WAIT"               # Await imminent natural transition or telemetry arrival


class ObservationScope(str, Enum):
    """Boundary enforcement for information acquisition (Section 10)."""
    LOCAL = "LOCAL"
    ENTITY = "ENTITY"
    SERVICE = "SERVICE"
    WORKFLOW = "WORKFLOW"
    MISSION = "MISSION"
    SYSTEM = "SYSTEM"
    ENVIRONMENT = "ENVIRONMENT"
    SIMULATION_ONLY = "SIMULATION_ONLY"


class StopConditionReason(str, Enum):
    """Stopping intelligence classifications (Section 16, 63, 64)."""
    SUFFICIENT_INFORMATION = "SUFFICIENT_INFORMATION"
    DECISION_INSENSITIVE = "DECISION_INSENSITIVE"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    DEADLINE_REACHED = "DEADLINE_REACHED"
    RISK_TOO_HIGH = "RISK_TOO_HIGH"
    NO_USEFUL_SOURCE = "NO_USEFUL_SOURCE"
    USER_REQUIRED = "USER_REQUIRED"
    NO_OBSERVATION_NEEDED = "NO_OBSERVATION_NEEDED"
    UNKNOWN = "UNKNOWN"


class VerificationStatus(str, Enum):
    """Integrity and provenance verification state of acquired evidence (Section 39)."""
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    CONTRADICTED = "CONTRADICTED"
    UNRESOLVED = "UNRESOLVED"
    FAILED = "FAILED"


class ConflictResolutionStrategy(str, Enum):
    """Strategy for evaluating conflicting multi-source observations (Section 40)."""
    RECENCY = "RECENCY"
    PROVENANCE_WEIGHT = "PROVENANCE_WEIGHT"
    INDEPENDENT_CONFIRMATION = "INDEPENDENT_CONFIRMATION"
    UNRESOLVED = "UNRESOLVED"


# =====================================================================
# DOMAIN MODELS
# =====================================================================

class UncertaintyDimension(BaseModel):
    """Specific dimension of uncertainty with assessment and basis (Section 7)."""
    model_config = ConfigDict(extra="ignore")

    dimension: UncertaintyDimensionType
    level: UncertaintyLevel = UncertaintyLevel.UNKNOWN
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    description: str = ""
    evidence_count: int = 0
    staleness_seconds: float = 0.0
    is_critical: bool = False


class UncertaintyState(BaseModel):
    """Comprehensive multi-dimensional uncertainty state for an entity or decision context."""
    model_config = ConfigDict(extra="ignore")

    state_id: str = Field(default_factory=lambda: generate_uuid("unc"))
    target_entity: str
    overall_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    dimensions: Dict[str, UncertaintyDimension] = Field(default_factory=dict)
    assumptions_count: int = 0
    stale_signals_count: int = 0
    missing_data_count: int = 0
    assessed_at: datetime = Field(default_factory=utc_now)


class InformationGap(BaseModel):
    """First-class representation of an unknown that may matter (Section 6)."""
    model_config = ConfigDict(extra="ignore")

    gap_id: str = Field(default_factory=lambda: generate_uuid("gap"))
    question: str
    missing_information: str
    affected_entity: str
    affected_state: str = ""
    source_candidates: List[str] = Field(default_factory=list)
    why_it_matters: str = ""
    dependent_decision_id: Optional[str] = None
    dependent_mission_id: Optional[str] = None
    dependent_situation_id: Optional[str] = None
    uncertainty_dimensions: List[UncertaintyDimensionType] = Field(default_factory=list)
    severity: str = "MEDIUM"  # LOW, MEDIUM, HIGH, CRITICAL
    freshness_requirement_seconds: float = 60.0
    temporal_scope: str = "CURRENT"  # HISTORICAL, CURRENT, TRANSITIONAL, FORECAST
    cost_estimate: float = 0.0
    latency_requirement_seconds: float = 5.0
    safety_constraints: List[str] = Field(default_factory=list)
    is_resolved_by_existing_data: bool = False
    existing_evidence_id: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)


class DecisionSensitivity(BaseModel):
    """Evaluation of whether resolving an uncertainty could change downstream action (Section 8, 46)."""
    model_config = ConfigDict(extra="ignore")

    sensitivity_id: str = Field(default_factory=lambda: generate_uuid("sens"))
    gap_id: str
    decisions_affected: List[str] = Field(default_factory=list)
    actions_affected: List[str] = Field(default_factory=list)
    milestones_affected: List[str] = Field(default_factory=list)
    is_decision_sensitive: bool = True
    sensitivity_score: float = Field(default=0.5, ge=0.0, le=1.0)  # 0.0 = completely insensitive, 1.0 = branch-changing
    possible_branch_changes: List[str] = Field(default_factory=list)
    rationale: str = ""


class ObservationCost(BaseModel):
    """Multidimensional cost model for an observation (Section 37)."""
    model_config = ConfigDict(extra="ignore")

    compute_units: float = 0.05
    token_cost: int = 0
    network_latency_ms: float = 50.0
    storage_bytes: int = 256
    interruption_penalty: float = 0.0  # > 0 for user clarification
    privacy_impact: str = "PUBLIC"     # PUBLIC, INTERNAL, SENSITIVE, RESTRICTED
    operational_overhead: float = 0.0


class ObservationRisk(BaseModel):
    """Risk and safety boundaries of an observation (Section 38)."""
    model_config = ConfigDict(extra="ignore")

    security_risk_level: str = "LOW"   # LOW, MEDIUM, HIGH, CRITICAL
    privacy_risk_level: str = "LOW"
    state_mutation_risk: bool = False  # Hard invariant: Observation must not mutate production state
    reversibility: str = "REVERSIBLE"
    blast_radius: str = "LOCAL"
    requires_approval: bool = False
    governance_approved: bool = True
    emergency_stop_triggered: bool = False


class ObservationConstraint(BaseModel):
    """Governance, budget, or scope constraint governing observation."""
    model_config = ConfigDict(extra="ignore")

    constraint_id: str = Field(default_factory=lambda: generate_uuid("cst"))
    rule: str
    is_hard_barrier: bool = True
    enforced_by: str = "Governance"


class InformationValueEstimate(BaseModel):
    """Structured Value-of-Information (VoI) estimate (Section 9, 64)."""
    model_config = ConfigDict(extra="ignore")

    estimate_id: str = Field(default_factory=lambda: generate_uuid("voi"))
    candidate_id: str
    tier: InformationValueTier = InformationValueTier.MODERATE
    expected_decision_improvement: float = Field(default=0.5, ge=0.0, le=1.0)
    expected_uncertainty_reduction: float = Field(default=0.5, ge=0.0, le=1.0)
    net_value_score: float = Field(default=0.5, ge=-1.0, le=1.0)  # value - (cost + risk)
    marginal_value: float = Field(default=0.5, ge=0.0, le=1.0)
    is_redundant: bool = False
    justification: str = ""


class ObservationCandidate(BaseModel):
    """A concrete observation option to acquire required evidence (Section 11, 12)."""
    model_config = ConfigDict(extra="ignore")

    candidate_id: str = Field(default_factory=lambda: generate_uuid("cand"))
    gap_id: str
    name: str
    target_source: str
    method: ObservationMethodType = ObservationMethodType.PASSIVE
    scope: ObservationScope = ObservationScope.ENTITY
    query_payload: Dict[str, Any] = Field(default_factory=dict)
    cost: ObservationCost = Field(default_factory=ObservationCost)
    risk: ObservationRisk = Field(default_factory=ObservationRisk)
    value_estimate: Optional[InformationValueEstimate] = None
    expected_latency_seconds: float = 1.0
    deadline_seconds: Optional[float] = None
    is_selected: bool = False
    is_blocked: bool = False
    block_reason: str = ""
    prompt_injection_sanitized: bool = True


class ObservationOutcome(BaseModel):
    """Empirical evidence acquired from an executed observation (Section 32, 40)."""
    model_config = ConfigDict(extra="ignore")

    outcome_id: str = Field(default_factory=lambda: generate_uuid("out"))
    candidate_id: str
    plan_id: str
    source: str
    method: ObservationMethodType
    observed_at: datetime = Field(default_factory=utc_now)
    freshness_seconds: float = 0.0
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    provenance_hash: str = ""
    data_payload: Dict[str, Any] = Field(default_factory=dict)
    summary: str = ""
    conflicts_with_existing: bool = False
    conflict_details: str = ""
    is_hypothetical: bool = False
    environment_label: str = "OBSERVED"


class ObservationVerification(BaseModel):
    """Integrity and provenance audit of acquired observation (Section 39)."""
    model_config = ConfigDict(extra="ignore")

    verification_id: str = Field(default_factory=lambda: generate_uuid("veri"))
    outcome_id: str
    status: VerificationStatus = VerificationStatus.PENDING
    source_authenticated: bool = True
    schema_valid: bool = True
    freshness_valid: bool = True
    tamper_free: bool = True
    verified_at: datetime = Field(default_factory=utc_now)
    auditor: str = "VerificationEngine"
    verification_notes: str = ""


class ObservationBudget(BaseModel):
    """Resource economy allocation for information acquisition (Section 33, 42)."""
    model_config = ConfigDict(extra="ignore")

    allocated_units: float = 10.0
    spent_units: float = 0.0
    remaining_units: float = 10.0
    max_active_queries: int = 5
    max_latency_seconds: float = 30.0
    is_exhausted: bool = False


class ObservationPlan(BaseModel):
    """Authoritative, bounded plan for acquiring information (Section 14)."""
    model_config = ConfigDict(extra="ignore")

    plan_id: str = Field(default_factory=lambda: generate_uuid("plan"))
    version: int = 1
    objective: str
    target_entity: str
    status: ObservationPlanStatus = ObservationPlanStatus.IDENTIFIED
    gaps: List[InformationGap] = Field(default_factory=list)
    sensitivities: Dict[str, DecisionSensitivity] = Field(default_factory=dict)
    candidates: List[ObservationCandidate] = Field(default_factory=list)
    outcomes: List[ObservationOutcome] = Field(default_factory=list)
    verifications: Dict[str, ObservationVerification] = Field(default_factory=dict)
    budget: ObservationBudget = Field(default_factory=ObservationBudget)
    uncertainty_before: Optional[UncertaintyState] = None
    uncertainty_after: Optional[UncertaintyState] = None
    stop_reason: Optional[StopConditionReason] = None
    recommended_stance: str = "OBSERVE"  # ACT NOW, WAIT, OBSERVE, ASK USER, NO FURTHER INFORMATION NEEDED
    is_stale: bool = False
    stale_reason: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ObservationRequest(BaseModel):
    """User or system request to resolve unknowns and plan observations (Section 6)."""
    model_config = ConfigDict(extra="ignore")

    target_entity: str
    question: str = "What don't I know and what observation is needed?"
    dependent_decision_id: Optional[str] = None
    dependent_mission_id: Optional[str] = None
    dependent_situation_id: Optional[str] = None
    uncertainty_dimensions: List[UncertaintyDimensionType] = Field(default_factory=list)
    budget_units: float = 10.0
    deadline_seconds: float = 30.0
    scope: ObservationScope = ObservationScope.ENTITY


class ObservationSnapshot(BaseModel):
    """Immutable point-in-time snapshot for reproducible audit (Section 41)."""
    model_config = ConfigDict(extra="ignore")

    snapshot_id: str = Field(default_factory=lambda: generate_uuid("snap"))
    plan_id: str
    plan_version: int
    target_entity: str
    status: ObservationPlanStatus
    uncertainty_summary: Dict[str, Any] = Field(default_factory=dict)
    selected_candidates: List[Dict[str, Any]] = Field(default_factory=list)
    outcomes_summary: List[Dict[str, Any]] = Field(default_factory=list)
    stop_reason: Optional[str] = None
    timestamp: datetime = Field(default_factory=utc_now)
    snapshot_hash: str = ""


class ObservationEvent(BaseModel):
    """Standardized event emitted on observation lifecycle transitions (Section 50)."""
    model_config = ConfigDict(extra="ignore")

    event_id: str = Field(default_factory=lambda: generate_uuid("evt"))
    event_type: str
    plan_id: str
    target_entity: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utc_now)
