"""Domain entities, enums, and data transfer objects for Kairo Autonomous Attention,
Cognitive Resource Allocation, Focus Management & Interruption Governance Engine (Task 109).

Non-Negotiable Invariants:
1. ATTENTION != DECISION (Task 94 Decision Intelligence decides).
2. ATTENTION != PRIORITY AUTHORITY (Attention salience is contextual, not absolute priority).
3. ATTENTION != GOAL (Task 100 Mission Control & Goal Management manages goals).
4. ATTENTION != ACTION (Zero action execution primitives).
5. ATTENTION != AUTHORIZATION (SecurityCenter and ApprovalRegistry authorize).
6. ATTENTION != RESOURCE ALLOCATION AUTHORITY (Task 77 Resource Economy allocates).
7. EMERGENCY_STOP ABSOLUTE PRIMACY (Immediately surfaced, fail-closed, cannot be suppressed).
8. EXTERNAL CONTENT != PRIORITY AUTHORITY (Untrusted claims of 'CRITICAL' treated as unverified data).
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


def gen_attn_id(prefix: str = "att") -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


# ============================================================================
# Enums
# ============================================================================

class AttentionCandidateType(StrEnum):
    """Supported candidate sources and categories (Spec 3)."""
    USER_REQUEST = "USER_REQUEST"
    DEADLINE = "DEADLINE"
    MISSION_BLOCKER = "MISSION_BLOCKER"
    MISSION_PROGRESS = "MISSION_PROGRESS"
    SECURITY = "SECURITY"
    SAFETY = "SAFETY"
    FAILURE = "FAILURE"
    RECOVERY = "RECOVERY"
    WORLD_STATE_CHANGE = "WORLD_STATE_CHANGE"
    BELIEF_CHANGE = "BELIEF_CHANGE"
    SITUATION = "SITUATION"
    DECISION = "DECISION"
    ACTION = "ACTION"
    VERIFICATION = "VERIFICATION"
    CAPABILITY = "CAPABILITY"
    RELIABILITY = "RELIABILITY"
    FORECAST = "FORECAST"
    EVALUATION = "EVALUATION"
    EXPERIMENT = "EXPERIMENT"
    MEMORY = "MEMORY"
    LEARNING = "LEARNING"
    MAINTENANCE = "MAINTENANCE"
    BACKGROUND = "BACKGROUND"
    OPPORTUNITY = "OPPORTUNITY"


class AttentionLifecycleState(StrEnum):
    """Explicit 17-state attention lifecycle (Spec 4)."""
    CREATED = "CREATED"
    QUEUED = "QUEUED"
    CONSIDERING = "CONSIDERING"
    FOCUSED = "FOCUSED"
    BACKGROUND = "BACKGROUND"
    DEFERRED = "DEFERRED"
    SUPPRESSED = "SUPPRESSED"
    WATCHING = "WATCHING"
    INTERRUPT_REQUESTED = "INTERRUPT_REQUESTED"
    INTERRUPTED = "INTERRUPTED"
    RESUMABLE = "RESUMABLE"
    RESOLVED = "RESOLVED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    MERGED = "MERGED"
    SPLIT = "SPLIT"
    UNKNOWN = "UNKNOWN"


class InterruptionClassification(StrEnum):
    """6-tier interruption governance classification (Spec 10)."""
    NO_INTERRUPT = "NO_INTERRUPT"
    BACKGROUND = "BACKGROUND"
    DEFER = "DEFER"
    WATCH = "WATCH"
    INTERRUPT = "INTERRUPT"
    IMMEDIATE_INTERRUPT = "IMMEDIATE_INTERRUPT"


class FocusSwitchReason(StrEnum):
    """Recognized reasons for focus transitions (Spec 9)."""
    USER_REQUEST = "USER_REQUEST"
    SECURITY = "SECURITY"
    SAFETY = "SAFETY"
    MISSION_BLOCK = "MISSION_BLOCK"
    DEADLINE = "DEADLINE"
    HIGH_RISK = "HIGH_RISK"
    FAILURE = "FAILURE"
    RECOVERY = "RECOVERY"
    EXTERNAL_EVENT = "EXTERNAL_EVENT"
    FOCUS_COMPLETED = "FOCUS_COMPLETED"
    FOCUS_STALE = "FOCUS_STALE"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class WaitingConditionType(StrEnum):
    """Waiting states consuming minimal cognitive resources (Spec 36)."""
    WAITING_FOR_EVIDENCE = "WAITING_FOR_EVIDENCE"
    WAITING_FOR_USER = "WAITING_FOR_USER"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    WAITING_FOR_RESOURCE = "WAITING_FOR_RESOURCE"
    WAITING_FOR_DEPENDENCY = "WAITING_FOR_DEPENDENCY"
    WAITING_FOR_TIME = "WAITING_FOR_TIME"
    WAITING_FOR_EXTERNAL_EVENT = "WAITING_FOR_EXTERNAL_EVENT"


class CognitiveHealthStatus(StrEnum):
    """Cognitive load and stability indicator (Spec 44, 45)."""
    HEALTHY = "HEALTHY"
    MODERATE_LOAD = "MODERATE_LOAD"
    COGNITIVE_FRAGMENTATION = "COGNITIVE_FRAGMENTATION"
    ATTENTION_STORM = "ATTENTION_STORM"
    STARVATION_DETECTED = "STARVATION_DETECTED"
    EMERGENCY_HALTED = "EMERGENCY_HALTED"


# ============================================================================
# Salience & Scoring (Spec 5)
# ============================================================================

class AttentionScore(BaseModel):
    """Structured 15-dimensional salience representation.
    Does NOT reduce dimensions into one lossy opaque number (Spec 5).
    """
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    urgency: float = Field(default=0.5, ge=0.0, le=1.0)
    risk: float = Field(default=0.3, ge=0.0, le=1.0)
    deadline_pressure: float = Field(default=0.0, ge=0.0, le=1.0)
    user_relevance: float = Field(default=0.5, ge=0.0, le=1.0)
    mission_relevance: float = Field(default=0.5, ge=0.0, le=1.0)
    novelty: float = Field(default=0.0, ge=0.0, le=1.0)
    change_magnitude: float = Field(default=0.0, ge=0.0, le=1.0)
    dependency_impact: float = Field(default=0.0, ge=0.0, le=1.0)
    uncertainty: float = Field(default=0.2, ge=0.0, le=1.0)
    irreversibility: float = Field(default=0.0, ge=0.0, le=1.0)
    external_impact: float = Field(default=0.0, ge=0.0, le=1.0)
    resource_cost: float = Field(default=0.2, ge=0.0, le=1.0)
    interruption_cost: float = Field(default=0.2, ge=0.0, le=1.0)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)

    # Composite routing score for priority queue ordering (explainable weighted view)
    composite_salience: float = Field(default=0.5, ge=0.0, le=1.0)
    contributing_factors: List[str] = Field(default_factory=list)
    explanation: str = Field(default="")


class AttentionEvidence(BaseModel):
    """Auditable evidence backing an attention candidate (Spec 1, 2)."""
    evidence_id: str = Field(default_factory=lambda: gen_attn_id("aev"))
    candidate_id: str
    source_uri: str
    source_type: str = "INTERNAL_SIGNAL"  # USER, MISSION, SITUATION, BELIEF, TOOL, EXTERNAL
    is_trusted: bool = True
    credibility: float = Field(default=0.8, ge=0.0, le=1.0)
    observed_at: datetime = Field(default_factory=utc_now)
    claim: str = ""
    raw_payload: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# Attention Candidate (Spec 2)
# ============================================================================

class AttentionCandidate(BaseModel):
    """First-class Attention Candidate representing a cognitive stimulus."""
    candidate_id: str = Field(default_factory=lambda: gen_attn_id("acand"))
    source: str = "internal"
    type: AttentionCandidateType = AttentionCandidateType.BACKGROUND
    target: str = "unspecified"
    scope: str = "SYSTEM"
    timestamp: datetime = Field(default_factory=utc_now)
    freshness: float = Field(default=1.0, ge=0.0, le=1.0)
    lifecycle: AttentionLifecycleState = AttentionLifecycleState.CREATED
    title: str
    description: str = ""

    # Cross-Subsystem References (Spec 2, 13-23)
    related_mission: Optional[str] = None
    related_situation: Optional[str] = None
    related_goal: Optional[str] = None
    related_decision: Optional[str] = None
    related_action: Optional[str] = None
    related_capability: Optional[str] = None
    related_user_intent: Optional[str] = None

    # Uncertainty & Scoring
    uncertainty: float = Field(default=0.2, ge=0.0, le=1.0)
    score: AttentionScore = Field(default_factory=AttentionScore)
    evidence_ids: List[str] = Field(default_factory=list)

    # Aging & Fairness (Spec 26, 27)
    age_seconds: float = 0.0
    deferral_count: int = 0
    aging_boost: float = 0.0
    is_adversarial_dampened: bool = False
    deadline: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# Focus Session & Stack (Spec 7, 8, 9, 46, 47)
# ============================================================================

class FocusTarget(BaseModel):
    """Target entity under focused reasoning (Spec 1, 7)."""
    target_id: str
    target_type: str = "MISSION"  # MISSION, INTENT, TASK, INCIDENT, DEBUGGING, VERIFICATION
    name: str = ""
    scope: str = "DEFAULT"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ResumptionContext(BaseModel):
    """Compact context engineering bundle for restoring interrupted work (Spec 47)."""
    objective: str = ""
    progress_summary: str = ""
    blockers: List[str] = Field(default_factory=list)
    last_state: Dict[str, Any] = Field(default_factory=dict)
    relevant_evidence: List[str] = Field(default_factory=list)
    pending_actions: List[str] = Field(default_factory=list)
    unresolved_questions: List[str] = Field(default_factory=list)
    saved_at: datetime = Field(default_factory=utc_now)


class FocusSession(BaseModel):
    """Active or paused bounded focus session in the nested focus stack (Spec 7, 8)."""
    session_id: str = Field(default_factory=lambda: gen_attn_id("fsess"))
    parent_session_id: Optional[str] = None
    depth: int = Field(default=0, ge=0, le=5)  # Max depth bound = 5 (Spec 8)
    primary_target: FocusTarget
    candidate_id: str
    reason: FocusSwitchReason = FocusSwitchReason.USER_REQUEST
    start_time: datetime = Field(default_factory=utc_now)
    expected_duration_sec: int = Field(default=300, ge=1)
    resource_budget: Dict[str, Any] = Field(default_factory=dict)
    interruption_policy: str = "NORMAL"  # SHIELDED, NORMAL, STRICT
    dependencies: List[str] = Field(default_factory=list)
    success_condition: str = "Objective accomplished"
    exit_conditions: List[str] = Field(default_factory=list)
    is_active: bool = True
    end_time: Optional[datetime] = None
    resumption_context: Optional[ResumptionContext] = None


class FocusTransition(BaseModel):
    """Audit record of attention focus switching (Spec 9)."""
    transition_id: str = Field(default_factory=lambda: gen_attn_id("ftrn"))
    previous_target: Optional[str] = None
    new_target: str
    reason: FocusSwitchReason
    trigger_candidate_id: str
    switching_cost: float = Field(default=0.2, ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=utc_now)
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    details: str = ""


# ============================================================================
# Interruption Governance (Spec 10, 11, 12)
# ============================================================================

class InterruptionRequest(BaseModel):
    """Inbound request to interrupt current active focus (Spec 10)."""
    request_id: str = Field(default_factory=lambda: gen_attn_id("ireq"))
    incoming_candidate_id: str
    current_session_id: Optional[str] = None
    urgency: float = Field(default=0.5, ge=0.0, le=1.0)
    risk: float = Field(default=0.3, ge=0.0, le=1.0)
    source_is_user: bool = False
    source_is_emergency_stop: bool = False
    requested_at: datetime = Field(default_factory=utc_now)


class InterruptionCostBreakdown(BaseModel):
    """Multi-dimensional switching cost calculation (Spec 11)."""
    lost_context_cost: float = Field(default=0.1, ge=0.0, le=1.0)
    lost_progress_cost: float = Field(default=0.1, ge=0.0, le=1.0)
    recomputation_cost: float = Field(default=0.1, ge=0.0, le=1.0)
    resource_cost: float = Field(default=0.1, ge=0.0, le=1.0)
    deadline_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    cognitive_fragmentation_risk: float = Field(default=0.1, ge=0.0, le=1.0)
    action_safety_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    total_interruption_cost: float = Field(default=0.2, ge=0.0, le=1.0)


class InterruptionDecision(BaseModel):
    """Governance decision on whether and how to interrupt (Spec 10, 11)."""
    decision_id: str = Field(default_factory=lambda: gen_attn_id("idec"))
    request_id: str
    incoming_candidate_id: str
    classification: InterruptionClassification
    should_interrupt: bool
    cost_breakdown: InterruptionCostBreakdown = Field(default_factory=InterruptionCostBreakdown)
    reason: str
    evaluated_at: datetime = Field(default_factory=utc_now)


# ============================================================================
# Cognitive Budget & Resource Economy (Spec 24, 25)
# ============================================================================

class AttentionBudget(BaseModel):
    """Cognitive budget breakdown for attention tracking (Spec 25)."""
    budget_id: str = Field(default_factory=lambda: gen_attn_id("abud"))
    active_reasoning_pct: float = Field(default=100.0, ge=0.0, le=100.0)
    background_pct: float = Field(default=30.0, ge=0.0, le=100.0)
    pending_queue_slots: int = Field(default=50, ge=1)
    reserved_emergency_pct: float = Field(default=20.0, ge=0.0, le=100.0)
    consumed_budget_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    deadline_budget_sec: float = Field(default=3600.0, ge=0.0)
    context_token_capacity: int = Field(default=128000, ge=1000)
    context_tokens_used: int = Field(default=0, ge=0)
    updated_at: datetime = Field(default_factory=utc_now)


class AttentionAllocation(BaseModel):
    """Formal demand request submitted to Task 77 Resource Economy (Spec 24)."""
    allocation_id: str = Field(default_factory=lambda: gen_attn_id("aalloc"))
    candidate_id: str
    estimated_reasoning_cost: float = Field(default=1.0, ge=0.1)
    expected_benefit: float = Field(default=0.7, ge=0.0, le=1.0)
    urgency: float = Field(default=0.5, ge=0.0, le=1.0)
    resource_class: str = "STANDARD_REASONING"  # LOW_LATENCY, DEEP_THINKING, PARALLEL_SEARCH
    deadline: Optional[datetime] = None
    economy_status: str = "REQUESTED"  # ALLOCATED, DEFERRED, DENIED, THROTTLED
    created_at: datetime = Field(default_factory=utc_now)


# ============================================================================
# Suppression, Watches, Reminders & Conflicts (Spec 32, 33, 36, 37)
# ============================================================================

class AttentionSuppression(BaseModel):
    """Record of duplicate, storm, or adversarial candidate dampening (Spec 32, 33, 50)."""
    suppression_id: str = Field(default_factory=lambda: gen_attn_id("asup"))
    candidate_id: str
    fingerprint: str
    reason: str  # DUPLICATE, STORM_LIMIT, ADVERSARIAL_INJECTION, COOLDOWN, QUIET_HOURS
    suppressed_at: datetime = Field(default_factory=utc_now)
    expires_at: Optional[datetime] = None


class AttentionWatch(BaseModel):
    """Bounded condition watch consuming minimal cognitive resources (Spec 37)."""
    watch_id: str = Field(default_factory=lambda: gen_attn_id("awtch"))
    candidate_id: str
    condition_type: WaitingConditionType
    condition_expr: str  # e.g. "deployment.status == 'SUCCESS'" or "user_response_received"
    reconsideration_trigger: str
    created_at: datetime = Field(default_factory=utc_now)
    is_active: bool = True


class AttentionReminder(BaseModel):
    """Time-based reminder for deferred candidates (Spec 1, 38)."""
    reminder_id: str = Field(default_factory=lambda: gen_attn_id("arem"))
    candidate_id: str
    trigger_at: datetime
    reason: str
    is_triggered: bool = False


class AttentionDependency(BaseModel):
    """Dependency link between attention candidates (Spec 1)."""
    dependency_id: str = Field(default_factory=lambda: gen_attn_id("adep"))
    parent_candidate_id: str
    child_candidate_id: str
    is_blocking: bool = True


class AttentionConflict(BaseModel):
    """Detected priority competition requiring decision-level arbitration (Spec 1)."""
    conflict_id: str = Field(default_factory=lambda: gen_attn_id("acnf"))
    candidate_ids: List[str]
    nature: str  # RESOURCE_COMPETITION, MUTUALLY_EXCLUSIVE_FOCUS, DEADLINE_COLLISION
    severity: str = "HIGH"
    surfaced_to_decision_engine: bool = False
    created_at: datetime = Field(default_factory=utc_now)


# ============================================================================
# Decision Snapshot & Audit Events (Spec 41, 42, 58)
# ============================================================================

class AttentionSnapshot(BaseModel):
    """Immutable point-in-time snapshot of the cognitive attention engine (Spec 41)."""
    snapshot_id: str = Field(default_factory=lambda: gen_attn_id("asnap"))
    created_at: datetime = Field(default_factory=utc_now)
    active_focus_session: Optional[FocusSession] = None
    nested_stack_sessions: List[FocusSession] = Field(default_factory=list)
    queue_summary: List[Dict[str, Any]] = Field(default_factory=list)
    budget: AttentionBudget = Field(default_factory=AttentionBudget)
    health_status: CognitiveHealthStatus = CognitiveHealthStatus.HEALTHY
    active_missions: List[str] = Field(default_factory=list)
    active_intents: List[str] = Field(default_factory=list)
    recent_transitions: List[FocusTransition] = Field(default_factory=list)


class AttentionFeedback(BaseModel):
    """Post-hoc evaluation telemetry on attention decisions (Spec 43, 64)."""
    feedback_id: str = Field(default_factory=lambda: gen_attn_id("afbk"))
    candidate_id: str
    decision_type: str  # INTERRUPT, DEFER, FOCUS, SUPPRESS
    was_appropriate: bool
    missed_critical: bool = False
    unnecessary_interrupt: bool = False
    starvation_occurred: bool = False
    notes: str = ""
    recorded_at: datetime = Field(default_factory=utc_now)


class AttentionEvent(BaseModel):
    """Structured telemetry event emitted across the lifecycle (Spec 58)."""
    event_id: str = Field(default_factory=lambda: gen_attn_id("aevt"))
    event_type: str  # attention.created, attention.focused, attention.interrupted, etc.
    candidate_id: Optional[str] = None
    session_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utc_now)


# Non-authoritative Decision Recommendation (Spec 1, 48)
class AttentionDecision(BaseModel):
    """Attention routing recommendation surfaced to Task 94 Decision Engine.
    NOTE: ATTENTION != DECISION (Spec 1, 48).
    """
    recommendation_id: str = Field(default_factory=lambda: gen_attn_id("arec"))
    candidate_id: str
    recommended_routing: InterruptionClassification
    suggested_focus_target: Optional[FocusTarget] = None
    salience: AttentionScore
    rationale: str
    created_at: datetime = Field(default_factory=utc_now)


# ============================================================================
# Compatibility Aliases
# ============================================================================
AttentionLifecycle = AttentionLifecycleState
FocusContext = ResumptionContext
InterruptionReason = FocusSwitchReason
AttentionHealthStatus = CognitiveHealthStatus
ConditionWatch = AttentionWatch
ResourceBudget = AttentionBudget
InterruptionEvaluation = InterruptionDecision
