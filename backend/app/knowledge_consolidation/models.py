"""Domain models and typed taxonomy for KAIRO Autonomous Knowledge Consolidation (Task 92).

Enforces non-negotiable cognitive invariants:
- MEMORY != TRUTH
- VECTOR SIMILARITY != TRUTH
- MODEL OUTPUT != FACT
- RECENCY != TRUTH
- CONFIDENCE != CERTAINTY
- INFERENCE != OBSERVATION
- HYPOTHESIS != BELIEF
- BELIEF != VERIFIED FACT
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(UTC)


def generate_id(prefix: str = "mem") -> str:
    """Generate prefixed identifier."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ==============================================================================
# Phase 1 — Memory Taxonomy Enums
# ==============================================================================


class MemoryType(str, Enum):
    """Categorical taxonomy for durable and transient knowledge."""

    EPISODIC = "EPISODIC"
    SEMANTIC = "SEMANTIC"
    PROCEDURAL = "PROCEDURAL"
    CONTEXTUAL = "CONTEXTUAL"
    PREFERENCE = "PREFERENCE"
    HYPOTHESIS = "HYPOTHESIS"
    BELIEF = "BELIEF"
    DERIVED = "DERIVED"
    OBSERVATION = "OBSERVATION"
    TASK_OUTCOME = "TASK_OUTCOME"
    SYSTEM_STATE = "SYSTEM_STATE"
    EXTERNAL_FACT = "EXTERNAL_FACT"


# ==============================================================================
# Phase 2 — Memory Status & Lifecycle
# ==============================================================================


class MemoryStatus(str, Enum):
    """Explicit lifecycle status values."""

    CANDIDATE = "CANDIDATE"
    ACTIVE = "ACTIVE"
    UNCERTAIN = "UNCERTAIN"
    CONFLICTED = "CONFLICTED"
    STALE = "STALE"
    INVALIDATED = "INVALIDATED"
    SUPERSEDED = "SUPERSEDED"
    ARCHIVED = "ARCHIVED"
    FORGOTTEN = "FORGOTTEN"
    BLOCKED = "BLOCKED"


# ==============================================================================
# Phase 3 — Provenance & Source Classifications
# ==============================================================================


class ProvenanceSourceType(str, Enum):
    """Origin classification distinguishing grounded reality from model inference."""

    OBSERVED = "OBSERVED"
    INFERRED = "INFERRED"
    DERIVED = "DERIVED"
    MODEL_GENERATED = "MODEL_GENERATED"
    EXTERNALLY_SOURCED = "EXTERNALLY_SOURCED"
    USER_ASSERTED = "USER_ASSERTED"
    SYSTEM_VERIFIED = "SYSTEM_VERIFIED"


# ==============================================================================
# Phase 4 — Evidence Relation Types
# ==============================================================================


class EvidenceRelationType(str, Enum):
    """Relationship between an evidence record and a target memory."""

    SUPPORT = "SUPPORT"
    CONTRADICT = "CONTRADICT"
    QUALIFY = "QUALIFY"
    EXPIRE = "EXPIRE"
    REVALIDATE = "REVALIDATE"


# ==============================================================================
# Phase 5 — Certainty States
# ==============================================================================


class CertaintyState(str, Enum):
    """Calibrated certainty levels separated strictly from numerical confidence."""

    KNOWN = "KNOWN"
    LIKELY = "LIKELY"
    POSSIBLE = "POSSIBLE"
    UNCERTAIN = "UNCERTAIN"
    CONTRADICTED = "CONTRADICTED"
    UNKNOWN = "UNKNOWN"


# ==============================================================================
# Phase 8 — Conflict Types
# ==============================================================================


class ConflictType(str, Enum):
    """Classification of contradictory claims between memory entities."""

    FACTUAL = "FACTUAL"
    TEMPORAL = "TEMPORAL"
    NUMERIC = "NUMERIC"
    IDENTITY = "IDENTITY"
    STATE = "STATE"
    PREFERENCE = "PREFERENCE"
    PROCEDURAL = "PROCEDURAL"
    DEPENDENCY = "DEPENDENCY"


# ==============================================================================
# Phase 11 — Volatility Classes
# ==============================================================================


class VolatilityClass(str, Enum):
    """Temporal decay volatility rating."""

    HIGH = "HIGH"  # Minutes to hours (e.g. system state, active task)
    MEDIUM = "MEDIUM"  # Days to weeks (e.g. active project context, sprint constraints)
    LOW = "LOW"  # Months to permanent (e.g. foundational facts, stable preferences)


# ==============================================================================
# Phase 12 — Retention Actions
# ==============================================================================


class RetentionAction(str, Enum):
    """Actionable outcomes from the memory retention engine."""

    RETAIN = "RETAIN"
    UPDATE = "UPDATE"
    MERGE = "MERGE"
    SUPERSEDE = "SUPERSEDE"
    ARCHIVE = "ARCHIVE"
    FORGET = "FORGET"
    REVALIDATE = "REVALIDATE"
    ESCALATE = "ESCALATE"


# ==============================================================================
# Phase 16 — Hypothesis Status
# ==============================================================================


class HypothesisStatus(str, Enum):
    """Operational status for claims under empirical validation."""

    PROPOSED = "PROPOSED"
    SUPPORTED = "SUPPORTED"
    WEAKENED = "WEAKENED"
    CONTRADICTED = "CONTRADICTED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


# ==============================================================================
# Phase 26 — Privacy & Sensitivity Classifications
# ==============================================================================


class SensitivityClassification(str, Enum):
    """Data sensitivity and access boundary."""

    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    PRIVATE = "PRIVATE"
    SENSITIVE = "SENSITIVE"
    RESTRICTED = "RESTRICTED"


# ==============================================================================
# Typed Domain Models
# ==============================================================================


class MemoryProvenance(BaseModel):
    """Auditable provenance record tracking extraction and lineage."""

    model_config = ConfigDict(extra="ignore")

    provenance_id: str = Field(default_factory=lambda: generate_id("prv"))
    memory_id: str
    source_type: ProvenanceSourceType = ProvenanceSourceType.OBSERVED
    source_identifier: str | None = None
    conversation_id: str | None = None
    message_id: str | None = None
    task_id: str | None = None
    run_id: str | None = None
    event_id: str | None = None
    document_ref: str | None = None
    external_source_ref: str | None = None
    extraction_method: str = "direct"
    extracted_at: datetime = Field(default_factory=utc_now)
    validation_status: str = "UNVERIFIED"
    transformation_history: list[dict[str, Any]] = Field(default_factory=list)
    actor: str = "kairo_system"


class MemoryEvidence(BaseModel):
    """Grounding evidence record linked to a memory."""

    model_config = ConfigDict(extra="ignore")

    evidence_id: str = Field(default_factory=lambda: generate_id("evi"))
    memory_id: str
    relation_type: EvidenceRelationType = EvidenceRelationType.SUPPORT
    source: str
    source_type: ProvenanceSourceType = ProvenanceSourceType.OBSERVED
    content: str
    reliability: float = Field(default=0.8, ge=0.0, le=1.0)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    freshness: str = "FRESH"
    provenance_id: str | None = None
    verification_status: str = "VERIFIED"
    created_at: datetime = Field(default_factory=utc_now)


class MemoryConflict(BaseModel):
    """Explicit contradiction tracking between competing memories."""

    model_config = ConfigDict(extra="ignore")

    conflict_id: str = Field(default_factory=lambda: generate_id("cnf"))
    conflict_type: ConflictType = ConflictType.FACTUAL
    memory_a_id: str
    memory_b_id: str
    explanation: str
    competing_values: dict[str, Any] = Field(default_factory=dict)
    evidence_ids: list[str] = Field(default_factory=list)
    detected_at: datetime = Field(default_factory=utc_now)
    status: str = "CONFLICTED"
    resolution_strategy: str | None = None
    resolution_winner_id: str | None = None
    resolved_by: str | None = None
    resolved_at: datetime | None = None


class ProceduralMemory(BaseModel):
    """Structured recipe or workflow representation."""

    model_config = ConfigDict(extra="ignore")

    procedure_id: str = Field(default_factory=lambda: generate_id("prc"))
    memory_id: str
    name: str
    description: str
    prerequisites: list[str] = Field(default_factory=list)
    steps: list[dict[str, Any]] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    failure_conditions: list[str] = Field(default_factory=list)
    validation_history: list[dict[str, Any]] = Field(default_factory=list)
    version: int = 1
    last_successful_execution_at: datetime | None = None
    capability_ref: str | None = None


class HypothesisModel(BaseModel):
    """Tentative empirical model requiring verification; NEVER stored as factual."""

    model_config = ConfigDict(extra="ignore")

    hypothesis_id: str = Field(default_factory=lambda: generate_id("hyp"))
    memory_id: str
    claim: str
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    validation_plan: str
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    contradicting_evidence_ids: list[str] = Field(default_factory=list)
    verified_at: datetime | None = None
    rejected_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)


class DerivedKnowledgeModel(BaseModel):
    """Lineage link for deduced facts that invalidate when parents change."""

    model_config = ConfigDict(extra="ignore")

    derived_memory_id: str
    parent_memory_ids: list[str] = Field(default_factory=list)
    derivation_method: str = "deductive_inference"
    assumptions: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    invalidation_dependencies: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class ConsolidationRecord(BaseModel):
    """Reversible record clustering episodic memories into semantic knowledge."""

    model_config = ConfigDict(extra="ignore")

    consolidation_id: str = Field(default_factory=lambda: generate_id("cns"))
    source_episode_ids: list[str] = Field(default_factory=list)
    consolidated_semantic_id: str
    abstraction_level: str = "SEMANTIC"
    summary: str
    common_entities: list[str] = Field(default_factory=list)
    confidence: float = 0.8
    created_at: datetime = Field(default_factory=utc_now)


class RetentionDecision(BaseModel):
    """Audit record for retention decisions."""

    model_config = ConfigDict(extra="ignore")

    decision_id: str = Field(default_factory=lambda: generate_id("ret"))
    memory_id: str
    action: RetentionAction
    reason: str
    importance_score: float = 0.5
    utility_score: float = 0.5
    storage_cost: float = 0.0
    evaluated_at: datetime = Field(default_factory=utc_now)


class MemoryEntity(BaseModel):
    """Complete strongly typed domain model for KAIRO knowledge entities (Task 92 Phase 1)."""

    model_config = ConfigDict(extra="ignore")

    memory_id: str = Field(default_factory=lambda: generate_id("mem"))
    tenant_id: str = "default"
    user_id: str = "default_user"
    project_id: str | None = None

    type: MemoryType = MemoryType.OBSERVATION
    content: str
    structured_representation: dict[str, Any] = Field(default_factory=dict)
    source: str = "direct_input"

    created_at: datetime = Field(default_factory=utc_now)
    observed_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    valid_from: datetime = Field(default_factory=utc_now)
    valid_until: datetime | None = None
    expires_at: datetime | None = None

    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    certainty: CertaintyState = CertaintyState.KNOWN
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    relevance: float = Field(default=1.0, ge=0.0, le=1.0)
    freshness: str = "FRESH"
    volatility: VolatilityClass = VolatilityClass.MEDIUM

    retention_policy: str = "DEFAULT"
    status: MemoryStatus = MemoryStatus.ACTIVE
    version: int = 1
    supersedes: str | None = None
    superseded_by: str | None = None

    contradiction_links: list[str] = Field(default_factory=list)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    contradicting_evidence_ids: list[str] = Field(default_factory=list)

    last_validated_at: datetime | None = None
    next_validation_at: datetime | None = None
    sensitivity: SensitivityClassification = SensitivityClassification.INTERNAL

    provenance: MemoryProvenance | None = None


# ==============================================================================
# API Schemas
# ==============================================================================


class MemoryIngestionRequest(BaseModel):
    """Payload for ingesting raw knowledge or interaction."""

    model_config = ConfigDict(extra="ignore")

    content: str
    type: MemoryType = MemoryType.OBSERVATION
    structured_payload: dict[str, Any] = Field(default_factory=dict)
    source: str = "user_input"
    source_type: ProvenanceSourceType = ProvenanceSourceType.OBSERVED
    source_identifier: str | None = None
    confidence: float = 0.8
    certainty: CertaintyState = CertaintyState.KNOWN
    importance: float = 0.5
    volatility: VolatilityClass = VolatilityClass.MEDIUM
    sensitivity: SensitivityClassification = SensitivityClassification.INTERNAL
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    tenant_id: str = "default"
    user_id: str = "default_user"
    project_id: str | None = None


class ConflictResolutionRequest(BaseModel):
    """Payload to resolve a detected contradiction."""

    model_config = ConfigDict(extra="ignore")

    resolution_strategy: str = Field(
        ...,
        description="Resolution strategy: stronger_evidence, newer_verified, authoritative_source, user_correction, system_verification",
    )
    winning_memory_id: str | None = None
    explanation: str = "Resolved via verified authoritative source"
    resolved_by: str = "user"


class MemoryReconstructionRequest(BaseModel):
    """Payload to reconstruct timeline and knowledge evolution for an entity/topic."""

    model_config = ConfigDict(extra="ignore")

    query: str
    entity: str | None = None
    tenant_id: str = "default"
    include_superseded: bool = True
    include_conflicts: bool = True
    max_events: int = 50


class TimelineEvent(BaseModel):
    """Individual chronological event in reconstruction."""

    timestamp: datetime
    memory_id: str
    type: MemoryType
    summary: str
    status: MemoryStatus
    confidence: float
    certainty: CertaintyState
    source_type: ProvenanceSourceType
    evidence_count: int = 0


class MemoryReconstructionResult(BaseModel):
    """Forensic memory reconstruction result."""

    query: str
    timeline: list[TimelineEvent] = Field(default_factory=list)
    current_state: str
    superseded_states: list[str] = Field(default_factory=list)
    unresolved_conflicts: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float = 0.8
    certainty: CertaintyState = CertaintyState.KNOWN
    evidence_references: list[str] = Field(default_factory=list)
    synthesized_narrative: str
