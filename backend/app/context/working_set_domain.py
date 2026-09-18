"""Domain models, enums, and data structures for Task 110:
Kairo Autonomous Cognitive Working Set, Context Assembly, Relevance Packing & Context-Lifecycle Engine.

Strict Core Invariants:
1. CONTEXT != MEMORY (Context is an ephemeral, bounded working set, not permanent storage).
2. CONTEXT != TRUTH (Inclusion in context does not validate factual correctness).
3. CONTEXT != ATTENTION (Attention decides focus; context packs the required information within budget).
4. CONTEXT != DECISION (The context engine does not make decisions).
5. CONTEXT != AUTHORIZATION (Inclusion in context never grants permission or authorization).
6. CONTEXT != POLICY (Context engine does not define or alter security policies).
7. CONTEXT != GOAL (Missions and goals are defined upstream).
8. CONTEXT != WORLD STATE (Distinguishes observed reality from predicted or historical state).
9. CONTEXT != USER CONSENT (Cannot infer consent from context inclusion).
10. CONTEXT != EXECUTION (Zero execution primitives inside the context engine).
11. CONTEXT != COMPLETE REALITY (Absence from context does not equal absence from reality).
12. HIGH RELEVANCE != HIGH TRUTH (High relevance to a query does not make an item true).
13. RECENCY != CORRECTNESS (Freshness is tracked explicitly; recency does not imply accuracy).
14. MEMORY RETRIEVAL != CURRENT STATE (Stored memories cannot silently masquerade as live state).
15. BELIEF != FACT (Epistemic certainty is preserved and labeled).
16. SUMMARY != SOURCE (Lossy summarization retains source pointers; never claims equivalence).
17. COMPRESSION != LOSSLESS REPRESENTATION (Information loss is explicitly tracked).
18. TOKEN SAVINGS != COGNITIVE QUALITY (Compression must balance semantic fidelity).
19. UNTRUSTED CONTENT NEVER GAINS AUTHORITY (Web, DOM, Git, and agent text remain untrusted data).
20. EMERGENCY STOP ALWAYS OVERRIDES (Immediately invalidates execution-related working sets fail-closed).
"""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field


def utc_now() -> datetime:
    """Return timezone-aware current UTC timestamp."""
    return datetime.now(UTC)


def gen_ctx_id(prefix: str = "ws") -> str:
    """Generate cryptographically unique context domain identifier."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ============================================================================
# 1. Domain Enums
# ============================================================================

class WorkingSetLifecycle(str, enum.Enum):
    """Lifecycle state of an assembled Cognitive Working Set."""
    DRAFT = "DRAFT"
    ASSEMBLING = "ASSEMBLING"
    VALIDATING = "VALIDATING"
    READY = "READY"
    IN_USE = "IN_USE"
    REFRESHING = "REFRESHING"
    SUPERSEDED = "SUPERSEDED"
    EXPIRED = "EXPIRED"
    INVALIDATED = "INVALIDATED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class FreshnessClassification(str, enum.Enum):
    """Categorical freshness evaluation of context information."""
    FRESH = "FRESH"
    RECENT = "RECENT"
    AGING = "AGING"
    STALE = "STALE"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"


class CompressionLevel(str, enum.Enum):
    """Level of lossy or lossless compression applied to a context item."""
    NONE = "NONE"
    LIGHT = "LIGHT"
    MODERATE = "MODERATE"
    AGGRESSIVE = "AGGRESSIVE"
    REFERENCE_ONLY = "REFERENCE_ONLY"


class ItemInclusionSemantics(str, enum.Enum):
    """Semantic necessity of an item within a specific cognitive working set."""
    REQUIRED = "REQUIRED"
    IMPORTANT = "IMPORTANT"
    OPTIONAL = "OPTIONAL"
    REFERENCE_ONLY = "REFERENCE_ONLY"
    EXCLUDED = "EXCLUDED"


class DependencyType(str, enum.Enum):
    """Directional dependency relationship between context elements."""
    REQUIRES = "REQUIRES"
    SUPPORTS = "SUPPORTS"
    DERIVED_FROM = "DERIVED_FROM"
    EXPLAINS = "EXPLAINS"
    CONTRADICTS = "CONTRADICTS"
    SUPERSEDES = "SUPERSEDES"
    RELATED_TO = "RELATED_TO"


class LeaseState(str, enum.Enum):
    """Validity lease state for a working set."""
    VALID = "VALID"
    AGING = "AGING"
    INVALIDATED = "INVALIDATED"
    EXPIRED = "EXPIRED"


class FailureClass(str, enum.Enum):
    """Explicit failure taxonomy for context assembly and lifecycle operations."""
    RETRIEVAL_FAILURE = "RETRIEVAL_FAILURE"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    STALE_SOURCE = "STALE_SOURCE"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    DEPENDENCY_EXPANSION_LIMIT = "DEPENDENCY_EXPANSION_LIMIT"
    PROVENANCE_FAILURE = "PROVENANCE_FAILURE"
    SECURITY_FILTER_FAILURE = "SECURITY_FILTER_FAILURE"
    SCOPE_VIOLATION = "SCOPE_VIOLATION"
    CONFLICT_UNRESOLVED = "CONFLICT_UNRESOLVED"
    TRANSFORMATION_FAILURE = "TRANSFORMATION_FAILURE"
    COMPRESSION_FAILURE = "COMPRESSION_FAILURE"
    SERIALIZATION_FAILURE = "SERIALIZATION_FAILURE"
    SNAPSHOT_FAILURE = "SNAPSHOT_FAILURE"
    LEASE_EXPIRED = "LEASE_EXPIRED"
    CONTEXT_INVALIDATED = "CONTEXT_INVALIDATED"
    UNKNOWN = "UNKNOWN"


class TrustClassification(str, enum.Enum):
    """Epistemic trust class of content, preventing untrusted privilege escalation."""
    OBSERVED = "OBSERVED"
    USER_AUTHORED = "USER_AUTHORED"
    SYSTEM_DERIVED = "SYSTEM_DERIVED"
    MODEL_DERIVED = "MODEL_DERIVED"
    AGENT_DERIVED = "AGENT_DERIVED"
    EXTERNAL_UNTRUSTED = "EXTERNAL_UNTRUSTED"
    TOOL_UNTRUSTED = "TOOL_UNTRUSTED"
    WEB_UNTRUSTED = "WEB_UNTRUSTED"


class ContextSectionType(str, enum.Enum):
    """Canonical structural sections for cognitive working sets."""
    SYSTEM_STATE = "SYSTEM_STATE"
    CURRENT_USER_REQUEST = "CURRENT_USER_REQUEST"
    ACTIVE_INTENT = "ACTIVE_INTENT"
    CURRENT_MISSION = "CURRENT_MISSION"
    CURRENT_GOAL = "CURRENT_GOAL"
    CURRENT_SITUATION = "CURRENT_SITUATION"
    RELEVANT_WORLD_STATE = "RELEVANT_WORLD_STATE"
    RELEVANT_SELF_STATE = "RELEVANT_SELF_STATE"
    RELEVANT_BELIEFS = "RELEVANT_BELIEFS"
    RELEVANT_MEMORY = "RELEVANT_MEMORY"
    RELEVANT_STRATEGIES = "RELEVANT_STRATEGIES"
    RELEVANT_GRAPH_FACTS = "RELEVANT_GRAPH_FACTS"
    RELEVANT_DECISIONS = "RELEVANT_DECISIONS"
    RELEVANT_ACTION_STATE = "RELEVANT_ACTION_STATE"
    RELEVANT_CAPABILITIES = "RELEVANT_CAPABILITIES"
    RELEVANT_CONSTRAINTS = "RELEVANT_CONSTRAINTS"
    RELEVANT_RISKS = "RELEVANT_RISKS"
    RELEVANT_FORECASTS = "RELEVANT_FORECASTS"
    RELEVANT_RELIABILITY_SIGNALS = "RELEVANT_RELIABILITY_SIGNALS"
    RELEVANT_AGENT_RESULTS = "RELEVANT_AGENT_RESULTS"
    RECENT_EVENTS = "RECENT_EVENTS"
    CONFLICTS = "CONFLICTS"
    UNCERTAINTIES = "UNCERTAINTIES"
    MISSING_INFORMATION = "MISSING_INFORMATION"
    USER_PINNED_CONTEXT = "USER_PINNED_CONTEXT"


# ============================================================================
# 2. Context Provenance & Transformations
# ============================================================================

class ContextProvenance(BaseModel):
    """Complete provenance and lineage trace for a context item."""
    source_type: str
    source_id: str
    source_version: str = "1.0.0"
    originating_subsystem: str
    acquisition_timestamp: datetime = Field(default_factory=utc_now)
    observation_timestamp: datetime = Field(default_factory=utc_now)
    trust_label: TrustClassification = TrustClassification.SYSTEM_DERIVED
    user_originated: bool = False
    external_origin: bool = False
    agent_originated: bool = False
    generated_origin: bool = False
    lineage_path: List[str] = Field(default_factory=list)
    signature: Optional[str] = None


class ContextTransformation(BaseModel):
    """Record of an explicit transformation applied to an item."""
    transformation_id: str = Field(default_factory=lambda: gen_ctx_id("tr"))
    input_item_ids: List[str]
    output_item_id: str
    transformation_type: str  # NORMALIZED, SUMMARIZED, COMPRESSED, CLUSTERED, EXTRACTED
    algorithm: str = "standard_v1"
    timestamp: datetime = Field(default_factory=utc_now)
    information_loss: str = "NONE"  # NONE, MINOR, MODERATE, SEVERE
    is_reversible: bool = False
    original_size_bytes: int = 0
    transformed_size_bytes: int = 0
    source_reference: Optional[str] = None


# ============================================================================
# 3. Context Freshness & Dependencies
# ============================================================================

class ContextFreshness(BaseModel):
    """Freshness evaluation of a context element."""
    classification: FreshnessClassification = FreshnessClassification.FRESH
    source_timestamp: datetime
    effective_timestamp: datetime = Field(default_factory=utc_now)
    expiry_timestamp: Optional[datetime] = None
    last_validated_at: datetime = Field(default_factory=utc_now)
    age_seconds: float = 0.0
    domain_volatility_score: float = 0.5  # 0.0 = static (code file), 1.0 = highly volatile (market tick)
    staleness_score: float = 0.0  # 0.0 = perfectly fresh, 1.0 = completely stale


class ContextDependency(BaseModel):
    """Explicit dependency link between two context elements."""
    dependency_id: str = Field(default_factory=lambda: gen_ctx_id("cdep"))
    source_item_id: str
    target_item_id: str
    relationship: DependencyType
    is_blocking: bool = False
    explanation: str = ""


# ============================================================================
# 4. Context Budget & Allocations
# ============================================================================

class ContextBudget(BaseModel):
    """Budget constraints allocated for a working set assembly operation."""
    budget_id: str = Field(default_factory=lambda: gen_ctx_id("cbgt"))
    max_tokens: int = 8000
    max_bytes: int = 64000
    max_items: int = 60
    max_retrieval_calls: int = 20
    latency_budget_ms: float = 250.0
    allocated_tokens: int = 0
    allocated_bytes: int = 0
    allocated_items: int = 0
    used_tokens: int = 0
    used_bytes: int = 0
    used_items: int = 0
    retrieval_calls_made: int = 0
    actual_latency_ms: float = 0.0
    is_exhausted: bool = False
    exhaustion_reason: Optional[str] = None


class ContextAllocation(BaseModel):
    """Budget slice allocated to a specific section or subsystem."""
    section: ContextSectionType
    token_ceiling: int
    item_ceiling: int
    tokens_consumed: int = 0
    items_consumed: int = 0


# ============================================================================
# 5. Conflicts, Gaps & Exclusions
# ============================================================================

class ContextConflict(BaseModel):
    """Explicitly preserved conflict between context items, surfaced without false consensus."""
    conflict_id: str = Field(default_factory=lambda: gen_ctx_id("cconf"))
    competing_item_ids: List[str]
    conflict_dimension: str  # FACTUAL, TEMPORAL, NUMERIC, IDENTITY, STATE, PREFERENCE, PROCEDURAL
    summary: str
    severity: str = "MEDIUM"  # LOW, MEDIUM, HIGH, CRITICAL
    resolution_status: str = "UNRESOLVED"  # UNRESOLVED, ARBITRATED, PROVISIONAL
    arbitration_reference: Optional[str] = None  # Pointer to Task 107 Belief arbitration if present
    timestamp: datetime = Field(default_factory=utc_now)


class ContextGap(BaseModel):
    """Identified missing information required for high-confidence downstream reasoning."""
    gap_id: str = Field(default_factory=lambda: gen_ctx_id("cgap"))
    missing_information: str
    why_it_matters: str
    expected_source: str
    severity: str = "MEDIUM"  # LOW, MEDIUM, HIGH, BLOCKING
    is_blocking: bool = False
    confidence_impact: float = 0.2  # Penalty to overall confidence estimate
    suggested_retrieval: Optional[str] = None
    estimated_retrieval_cost: float = 1.0
    timestamp: datetime = Field(default_factory=utc_now)


class ContextExclusion(BaseModel):
    """Record of a candidate excluded from the final working set."""
    exclusion_id: str = Field(default_factory=lambda: gen_ctx_id("cexc"))
    candidate_id: str
    source_subsystem: str
    reason: str  # BUDGET_EXHAUSTED, RELEVANCE_BELOW_THRESHOLD, STALE, SECURITY_FILTERED, SCOPE_MISMATCH
    relevance_score: float = 0.0
    timestamp: datetime = Field(default_factory=utc_now)


class ContextPin(BaseModel):
    """Pin configuration ensuring a context item remains included across refreshes."""
    pin_id: str = Field(default_factory=lambda: gen_ctx_id("cpin"))
    item_id: str
    pinned_by: str = "user"  # user, system, developer
    reason: str = "User pinned requirement"
    created_at: datetime = Field(default_factory=utc_now)
    expires_at: Optional[datetime] = None


# ============================================================================
# 6. Context Items & Sections
# ============================================================================

class ContextItem(BaseModel):
    """A bounded atomic unit of information ready for cognitive presentation."""
    item_id: str = Field(default_factory=lambda: gen_ctx_id("citem"))
    version: int = 1
    section: ContextSectionType
    title: str
    content: str
    structured_payload: Dict[str, Any] = Field(default_factory=dict)
    inclusion: ItemInclusionSemantics = ItemInclusionSemantics.OPTIONAL
    relevance_score: float = 0.5
    relevance_components: Dict[str, float] = Field(default_factory=dict)
    confidence: float = 1.0
    freshness: ContextFreshness
    provenance: ContextProvenance
    compression: CompressionLevel = CompressionLevel.NONE
    token_estimate: int = 0
    character_count: int = 0
    is_pinned: bool = False
    is_untrusted: bool = False
    dependencies: List[str] = Field(default_factory=list)  # Target item IDs
    created_at: datetime = Field(default_factory=utc_now)


class ContextSection(BaseModel):
    """A structured logical grouping of context items."""
    section_type: ContextSectionType
    title: str
    items: List[ContextItem] = Field(default_factory=list)
    total_tokens: int = 0
    item_count: int = 0
    is_empty: bool = True


# ============================================================================
# 7. Context Candidate & Assembly Request
# ============================================================================

class ContextCandidate(BaseModel):
    """Raw candidate evidence gathered from a subsystem before filtering/packing."""
    candidate_id: str = Field(default_factory=lambda: gen_ctx_id("ccand"))
    source_subsystem: str
    source_id: str
    source_timestamp: datetime
    title: str
    raw_content: str
    structured_data: Dict[str, Any] = Field(default_factory=dict)
    trust_label: TrustClassification = TrustClassification.SYSTEM_DERIVED
    preliminary_relevance: float = 0.5
    domain_volatility: float = 0.5
    dependencies: List[str] = Field(default_factory=list)
    is_untrusted: bool = False


class ContextAssemblyRequest(BaseModel):
    """Typed demand specification for assembling a cognitive working set."""
    request_id: str = Field(default_factory=lambda: gen_ctx_id("creq"))
    tenant_id: str = "default"
    user_scope: str = "default_user"
    operation_type: str = "DELIBERATION"  # DELIBERATION, PLANNING, DECISION, ACTION_PREFLIGHT, MISSION_EVAL
    operation_id: Optional[str] = None
    session_id: Optional[str] = None
    conversation_id: Optional[str] = None
    objective: str = ""
    explicit_user_request: Optional[str] = None
    current_intent_id: Optional[str] = None
    active_mission_id: Optional[str] = None
    active_goal_id: Optional[str] = None
    active_situation_id: Optional[str] = None
    active_decision_id: Optional[str] = None
    active_action_transaction_id: Optional[str] = None
    agent_id: Optional[str] = None
    agent_role: Optional[str] = None
    token_budget: int = 8000
    latency_budget_ms: float = 250.0
    freshness_threshold_seconds: float = 3600.0
    compression_policy: str = "ADAPTIVE"  # NONE, LIGHT, ADAPTIVE, AGGRESSIVE
    required_sections: List[ContextSectionType] = Field(default_factory=list)
    pinned_item_ids: List[str] = Field(default_factory=list)
    forbidden_sources: List[str] = Field(default_factory=list)
    emergency_stop_checked: bool = True
    created_at: datetime = Field(default_factory=utc_now)


# ============================================================================
# 8. Working Set & Context Lease
# ============================================================================

class ContextLease(BaseModel):
    """Short-lived lease guaranteeing working set validity duration."""
    lease_id: str = Field(default_factory=lambda: gen_ctx_id("clease"))
    working_set_id: str
    working_set_version: int = 1
    state: LeaseState = LeaseState.VALID
    ttl_seconds: float = 60.0
    granted_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime = Field(default_factory=lambda: utc_now() + timedelta(seconds=60))
    invalidated_at: Optional[datetime] = None
    invalidation_reason: Optional[str] = None


class WorkingSet(BaseModel):
    """Authoritative cognitive working set bound to a specific operation."""
    working_set_id: str = Field(default_factory=lambda: gen_ctx_id("ws"))
    version: int = 1
    tenant_id: str = "default"
    user_scope: str = "default_user"
    operation_type: str
    operation_id: Optional[str] = None
    request_id: str
    session_id: Optional[str] = None
    conversation_id: Optional[str] = None
    objective: str
    mission_id: Optional[str] = None
    goal_id: Optional[str] = None
    situation_id: Optional[str] = None
    decision_id: Optional[str] = None
    action_transaction_id: Optional[str] = None
    agent_id: Optional[str] = None
    lifecycle: WorkingSetLifecycle = WorkingSetLifecycle.DRAFT
    sections: Dict[str, ContextSection] = Field(default_factory=dict)
    budget: ContextBudget
    lease: Optional[ContextLease] = None
    conflicts: List[ContextConflict] = Field(default_factory=list)
    gaps: List[ContextGap] = Field(default_factory=list)
    exclusions: List[ContextExclusion] = Field(default_factory=list)
    pinned_items: List[str] = Field(default_factory=list)
    quality_score: float = 1.0
    completeness_estimate: float = 1.0
    confidence_summary: float = 1.0
    item_count: int = 0
    total_tokens: int = 0
    compressed_item_count: int = 0
    has_untrusted_content: bool = False
    trace_id: str = Field(default_factory=lambda: gen_ctx_id("trace"))
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


# ============================================================================
# 9. Context Snapshot, Quality Assessment & Feedback
# ============================================================================

class ContextSnapshot(BaseModel):
    """Immutable audit record answering: 'What exact context did Kairo have when making this decision?'"""
    snapshot_id: str = Field(default_factory=lambda: gen_ctx_id("csnap"))
    working_set_id: str
    working_set_version: int
    operation_type: str
    operation_id: Optional[str] = None
    item_ids: List[str]
    source_versions: Dict[str, str] = Field(default_factory=dict)
    transformations_applied: List[str] = Field(default_factory=list)
    freshness_summary: Dict[str, int] = Field(default_factory=dict)
    conflict_count: int = 0
    gap_count: int = 0
    total_tokens: int = 0
    quality_score: float = 1.0
    has_untrusted_content: bool = False
    trace_id: str
    created_at: datetime = Field(default_factory=utc_now)
    snapshot_hash: str = ""  # Deterministic SHA-256 fingerprint


class ContextQualityAssessment(BaseModel):
    """Multi-dimensional evaluation of working set suitability."""
    assessment_id: str = Field(default_factory=lambda: gen_ctx_id("cqa"))
    working_set_id: str
    relevance_score: float = 1.0
    freshness_score: float = 1.0
    completeness_score: float = 1.0
    provenance_coverage_score: float = 1.0
    contradiction_visibility_score: float = 1.0
    redundancy_penalty: float = 0.0
    compression_quality_score: float = 1.0
    budget_efficiency_score: float = 1.0
    latency_score: float = 1.0
    source_diversity_score: float = 1.0
    task_alignment_score: float = 1.0
    safety_coverage_score: float = 1.0
    isolation_correctness_score: float = 1.0
    composite_quality: float = 1.0
    created_at: datetime = Field(default_factory=utc_now)


class ContextFeedback(BaseModel):
    """Post-deliberation feedback capturing how the working set was utilized."""
    feedback_id: str = Field(default_factory=lambda: gen_ctx_id("cfb"))
    working_set_id: str
    operation_id: Optional[str] = None
    items_used: List[str] = Field(default_factory=list)
    items_ignored: List[str] = Field(default_factory=list)
    items_misleading: List[str] = Field(default_factory=list)
    items_missing: List[str] = Field(default_factory=list)
    was_compression_harmful: bool = False
    was_freshness_sufficient: bool = True
    context_size_rating: str = "OPTIMAL"  # TOO_SMALL, OPTIMAL, TOO_LARGE
    downstream_outcome: str = "SUCCESS"  # SUCCESS, FAILURE, ABORTED
    comments: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
