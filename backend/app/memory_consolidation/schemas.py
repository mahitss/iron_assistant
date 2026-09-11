"""Pydantic v2 schemas and cognitive enums for Task 68: Kairo Autonomous Knowledge & Memory Consolidation Engine.

Enforces critical invariants:
- memory != truth
- memory != evidence
- summary != source
- repetition != independent evidence
- retrieval != verification
- prediction != event
- simulation != experience
- agent output != fact
- historical memory != current state
- user preference != authorization
- private memory != public knowledge
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _now_utc() -> datetime:
    return datetime.now(UTC)


class CognitiveClassification(StrEnum):
    """Fundamental cognitive distinctions (Spec 2). Never collapse these."""

    OBSERVATION = "OBSERVATION"
    EVENT = "EVENT"
    EXPERIENCE = "EXPERIENCE"
    MEMORY = "MEMORY"
    CLAIM = "CLAIM"
    EVIDENCE = "EVIDENCE"
    VERIFIED_FACT = "VERIFIED_FACT"
    PREDICTION = "PREDICTION"
    SIMULATION = "SIMULATION"
    DECISION = "DECISION"
    OUTCOME = "OUTCOME"
    SUMMARY = "SUMMARY"
    DERIVED_KNOWLEDGE = "DERIVED_KNOWLEDGE"


class MemoryType(StrEnum):
    """Supported memory types (Spec 3)."""

    WORKING_MEMORY = "WORKING_MEMORY"
    EPISODIC_MEMORY = "EPISODIC_MEMORY"
    SEMANTIC_MEMORY = "SEMANTIC_MEMORY"
    PROCEDURAL_MEMORY = "PROCEDURAL_MEMORY"
    EXECUTIVE_MEMORY = "EXECUTIVE_MEMORY"
    PROSPECTIVE_MEMORY = "PROSPECTIVE_MEMORY"
    QUARANTINED_MEMORY = "QUARANTINED_MEMORY"


class MemoryLifecycleState(StrEnum):
    """Deterministic memory lifecycle states (Spec 5)."""

    CAPTURED = "CAPTURED"
    CLASSIFIED = "CLASSIFIED"
    VALIDATING = "VALIDATING"
    ACTIVE = "ACTIVE"
    CONSOLIDATING = "CONSOLIDATING"
    CONSOLIDATED = "CONSOLIDATED"
    PROMOTED = "PROMOTED"
    CONFLICTED = "CONFLICTED"
    QUARANTINED = "QUARANTINED"
    STALE = "STALE"
    SUPERSEDED = "SUPERSEDED"
    EXPIRED = "EXPIRED"
    FORGOTTEN = "FORGOTTEN"
    DELETED = "DELETED"


class TrustLevel(StrEnum):
    """Memory poisoning defense trust classifications (Spec 17)."""

    TRUSTED = "TRUSTED"
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    EXTERNAL = "EXTERNAL"
    SUSPICIOUS = "SUSPICIOUS"
    QUARANTINED = "QUARANTINED"


class FreshnessState(StrEnum):
    """Temporal freshness assessment (Spec 14)."""

    FRESH = "FRESH"
    AGING = "AGING"
    STALE = "STALE"
    EXPIRED = "EXPIRED"
    SUPERSEDED = "SUPERSEDED"


class AbstractionLevel(StrEnum):
    """Hierarchical abstraction tiers (Spec 10)."""

    RAW_OBSERVATION = "RAW_OBSERVATION"
    EPISODE = "EPISODE"
    PATTERN = "PATTERN"
    GENERALIZED_KNOWLEDGE = "GENERALIZED_KNOWLEDGE"
    EXECUTIVE_INSIGHT = "EXECUTIVE_INSIGHT"


class ContradictionStatus(StrEnum):
    """Contradiction assessment status (Spec 12)."""

    NONE = "NONE"
    CONFLICTED = "CONFLICTED"
    SUPERSEDED = "SUPERSEDED"
    CONTEXTUALIZED = "CONTEXTUALIZED"
    RESOLVED = "RESOLVED"


class ConflictResolutionType(StrEnum):
    """Mechanism of conflict resolution (Spec 12)."""

    TIME_BASED = "TIME_BASED"
    ENVIRONMENT_BASED = "ENVIRONMENT_BASED"
    VERSION_BASED = "VERSION_BASED"
    EVIDENCE_OVERRIDE = "EVIDENCE_OVERRIDE"
    MANUAL = "MANUAL"


class MemoryAuditEventType(StrEnum):
    """Auditable lifecycle transitions (Spec 33)."""

    MEMORY_CAPTURED = "MEMORY_CAPTURED"
    MEMORY_CLASSIFIED = "MEMORY_CLASSIFIED"
    MEMORY_VALIDATED = "MEMORY_VALIDATED"
    MEMORY_QUARANTINED = "MEMORY_QUARANTINED"
    MEMORY_DEDUPLICATED = "MEMORY_DEDUPLICATED"
    MEMORY_CONSOLIDATED = "MEMORY_CONSOLIDATED"
    MEMORY_PROMOTED = "MEMORY_PROMOTED"
    MEMORY_CONFLICT_DETECTED = "MEMORY_CONFLICT_DETECTED"
    MEMORY_SUPERSEDED = "MEMORY_SUPERSEDED"
    MEMORY_EXPIRED = "MEMORY_EXPIRED"
    MEMORY_FORGOTTEN = "MEMORY_FORGOTTEN"
    MEMORY_DELETED = "MEMORY_DELETED"
    MEMORY_RESTORED = "MEMORY_RESTORED"
    MEMORY_RETRIEVED = "MEMORY_RETRIEVED"
    MEMORY_USED_IN_DECISION = "MEMORY_USED_IN_DECISION"


# ==============================================================================
# Domain Models & Payloads
# ==============================================================================


class MemoryProvenance(BaseModel):
    """Detailed memory lineage and self-reinforcement defense metadata (Spec 7, 19)."""

    model_config = ConfigDict(extra="ignore")

    provenance_id: str = Field(default_factory=lambda: f"prv_{uuid.uuid4().hex[:10]}")
    source_type: str = "direct_observation"
    source_id: str | None = None
    source_refs: list[str] = Field(default_factory=list)
    event_refs: list[str] = Field(default_factory=list)
    parent_memory_ids: list[str] = Field(default_factory=list)
    derived_from_ids: list[str] = Field(default_factory=list)
    related_memory_ids: list[str] = Field(default_factory=list)
    decision_refs: list[str] = Field(default_factory=list)
    goal_refs: list[str] = Field(default_factory=list)
    plan_refs: list[str] = Field(default_factory=list)
    incident_refs: list[str] = Field(default_factory=list)
    prediction_refs: list[str] = Field(default_factory=list)
    outcome_refs: list[str] = Field(default_factory=list)
    verification_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    generation_lineage: list[str] = Field(
        default_factory=list,
        description="Tracks generative iterations to prevent circular confirmation (Spec 19).",
    )
    is_independent_source: bool = True
    actor: str = "kairo_system"


class DurableMemory(BaseModel):
    """Full persistent memory entity adhering to cognitive invariants (Spec 4)."""

    model_config = ConfigDict(extra="ignore")

    memory_id: str = Field(default_factory=lambda: f"mem_{uuid.uuid4().hex[:12]}")
    id: str | None = None
    tenant_id: str = "default"
    user_id: str = "default_user"
    project_id: str | None = None

    def model_post_init(self, __context: Any) -> None:
        if not self.id:
            self.id = self.memory_id

    cognitive_type: CognitiveClassification = CognitiveClassification.MEMORY
    memory_type: MemoryType = MemoryType.EPISODIC_MEMORY
    abstraction_level: AbstractionLevel = AbstractionLevel.RAW_OBSERVATION

    content: str
    structured_payload: dict[str, Any] = Field(default_factory=dict)

    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    relevance: float = Field(default=1.0, ge=0.0, le=1.0)
    freshness: FreshnessState = FreshnessState.FRESH
    sensitivity: str = "STANDARD"  # PUBLIC, STANDARD, CONFIDENTIAL, RESTRICTED
    trust_level: TrustLevel = TrustLevel.UNVERIFIED

    created_at: datetime = Field(default_factory=_now_utc)
    observed_at: datetime = Field(default_factory=_now_utc)
    valid_from: datetime = Field(default_factory=_now_utc)
    valid_until: datetime | None = None
    expires_at: datetime | None = None
    last_accessed_at: datetime = Field(default_factory=_now_utc)
    last_validated_at: datetime | None = None
    last_consolidated_at: datetime | None = None

    status: MemoryLifecycleState = MemoryLifecycleState.ACTIVE
    version: int = 1
    superseded_by: str | None = None
    supersedes: str | None = None

    provenance: MemoryProvenance = Field(default_factory=MemoryProvenance)

    retention_policy: str = "DEFAULT"
    access_policy: str = "PROJECT_SCOPED"

    created_by: str = "kairo_ingestion"
    updated_by: str = "kairo_ingestion"


class MemoryCaptureRequest(BaseModel):
    """Payload to ingest a new observation, event, claim, or experience."""

    model_config = ConfigDict(extra="ignore")

    content: str
    cognitive_type: CognitiveClassification = CognitiveClassification.OBSERVATION
    memory_type: MemoryType = MemoryType.EPISODIC_MEMORY
    structured_payload: dict[str, Any] = Field(default_factory=dict)

    source_type: str = "user_interaction"
    source_id: str | None = None
    source_refs: list[str] = Field(default_factory=list)

    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    sensitivity: str = "STANDARD"
    trust_level: TrustLevel = TrustLevel.UNVERIFIED

    valid_from: datetime | None = None
    valid_until: datetime | None = None
    expires_at: datetime | None = None

    parent_memory_ids: list[str] = Field(default_factory=list)
    goal_refs: list[str] = Field(default_factory=list)
    decision_refs: list[str] = Field(default_factory=list)
    plan_refs: list[str] = Field(default_factory=list)

    tenant_id: str = "default"
    user_id: str = "default_user"
    project_id: str | None = None


class MemorySearchRequest(BaseModel):
    """Multi-factor search parameters with explainable ranking (Spec 20, 21)."""

    query: str
    top_k: int = Field(default=10, ge=1, le=100)
    memory_type: MemoryType | None = None
    cognitive_type: CognitiveClassification | None = None
    trust_level: TrustLevel | None = None
    min_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    min_importance: float = Field(default=0.0, ge=0.0, le=1.0)
    include_stale: bool = False
    time_range_start: datetime | None = None
    time_range_end: datetime | None = None
    goal_id: str | None = None
    project_id: str | None = None
    tenant_id: str = "default"


class MemorySearchResult(BaseModel):
    """Search result with explainable scoring breakdown (Spec 21)."""

    memory: DurableMemory
    retrieval_reason: str
    relevance_score: float
    freshness_score: float
    composite_score: float
    confidence: float
    verification_state: str
    provenance_summary: str


class ContextAssemblyRequest(BaseModel):
    """Payload to build task-specific context window respecting token limits (Spec 22)."""

    task_intent: str
    max_tokens: int = Field(default=2000, ge=100, le=32000)
    tenant_id: str = "default"
    user_id: str = "default_user"
    project_id: str | None = None
    goal_id: str | None = None
    include_predictions: bool = False
    include_simulations: bool = False


class ContextAssemblyResult(BaseModel):
    """Structured context partitioned into strict cognitive categories (Spec 22)."""

    context_string: str
    facts: list[str] = Field(default_factory=list)
    claims: list[str] = Field(default_factory=list)
    memories: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    predictions: list[str] = Field(default_factory=list)
    simulations: list[str] = Field(default_factory=list)
    token_estimate: int = 0
    excluded_count: int = 0


class ConsolidationCandidate(BaseModel):
    """Cluster of related episodic memories identified for higher-level abstraction (Spec 9)."""

    candidate_id: str = Field(default_factory=lambda: f"cnd_{uuid.uuid4().hex[:10]}")
    source_memory_ids: list[str]
    abstraction_level: AbstractionLevel
    suggested_summary: str
    common_entities: list[str] = Field(default_factory=list)
    confidence: float = 0.7
    status: str = "PENDING"  # PENDING, VALIDATING, CONSOLIDATED, REJECTED
    tenant_id: str = "default"
    created_at: datetime = Field(default_factory=_now_utc)


class ContradictionReport(BaseModel):
    """Recorded conflict between two incompatible memory records (Spec 12)."""

    conflict_id: str = Field(default_factory=lambda: f"cnf_{uuid.uuid4().hex[:10]}")
    memory_a_id: str
    memory_b_id: str
    status: ContradictionStatus = ContradictionStatus.CONFLICTED
    explanation: str
    temporal_context: dict[str, Any] = Field(default_factory=dict)
    environment_context: dict[str, Any] = Field(default_factory=dict)
    resolution_type: ConflictResolutionType | None = None
    resolved_by: str | None = None
    resolved_at: datetime | None = None
    tenant_id: str = "default"
    detected_at: datetime = Field(default_factory=_now_utc)


class MemoryHealthMetrics(BaseModel):
    """Memory health metrics and operational telemetry (Spec 27)."""

    total_memories: int = 0
    memories_by_type: dict[str, int] = Field(default_factory=dict)
    active_count: int = 0
    quarantined_count: int = 0
    conflicted_count: int = 0
    stale_count: int = 0
    expired_count: int = 0
    promotion_rate: float = 0.0
    consolidation_rate: float = 0.0
    deduplication_rate: float = 0.0
    retrieval_hit_rate: float = 0.0
    average_age_hours: float = 0.0
    poisoning_detections_count: int = 0
    tenant_id: str = "default"
    calculated_at: datetime = Field(default_factory=_now_utc)
