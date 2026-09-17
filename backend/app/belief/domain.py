"""Domain models, enums, and operational contracts for Task 107:
KAIRO Autonomous Belief, Evidence Arbitration, Conflict Resolution & World-Model Revision Engine.

Strict Architectural Invariants:
- BELIEF != TRUTH
- BELIEF != AUTHORIZATION
- BELIEF != POLICY
- BELIEF != GOAL
- BELIEF != DECISION
- BELIEF != MEMORY
- BELIEF != GRAPH FACT
- FORECAST != OBSERVATION
- SIMULATION != REALITY
- AGENT REPORT != INDEPENDENT TRUTH
- DUPLICATE EVIDENCE != INDEPENDENT EVIDENCE
- UNKNOWN != FALSE
- STALE != CURRENT
- CONFLICT != RESOLUTION
- CORRELATION != CAUSATION
- HISTORICAL VALIDITY != CURRENT VALIDITY
- USER ASSERTION != AUTOMATICALLY VERIFIED FACT
- CONFIDENCE != CERTAINTY
- EMERGENCY_STOP ABSOLUTE PRIMACY
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


def generate_uuid(prefix: str = "blf") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def compute_content_hash(data: Any) -> str:
    """Compute deterministic SHA-256 hash for deduplication and integrity."""
    if isinstance(data, str):
        content = data.encode("utf-8")
    else:
        content = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(content).hexdigest()


# =====================================================================
# ENUMS
# =====================================================================

class BeliefStatus(str, Enum):
    """Lifecycle statuses for a Belief (Phase 2)."""
    CANDIDATE = "CANDIDATE"
    SUPPORTED = "SUPPORTED"
    PROVISIONAL = "PROVISIONAL"
    CONFIDENT = "CONFIDENT"
    CONTESTED = "CONTESTED"
    CONTRADICTED = "CONTRADICTED"
    STALE = "STALE"
    EXPIRED = "EXPIRED"
    REVALIDATION_REQUIRED = "REVALIDATION_REQUIRED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"
    UNKNOWN = "UNKNOWN"


class EvidenceClassification(str, Enum):
    """Rigorous classification of evidence items (Phase 5)."""
    DIRECT_OBSERVATION = "DIRECT_OBSERVATION"
    VERIFIED_OUTCOME = "VERIFIED_OUTCOME"
    INDEPENDENT_EVALUATION = "INDEPENDENT_EVALUATION"
    EXPERIMENTAL = "EXPERIMENTAL"
    TELEMETRY = "TELEMETRY"
    INFERRED = "INFERRED"
    MEMORY = "MEMORY"
    AGENT_REPORT = "AGENT_REPORT"
    SIMULATION = "SIMULATION"
    FORECAST = "FORECAST"
    USER_ASSERTION = "USER_ASSERTION"
    EXTERNAL_SOURCE = "EXTERNAL_SOURCE"


class ArbitrationOutcome(str, Enum):
    """Result of evaluating evidence against a claim (Phase 7)."""
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    NEUTRAL = "NEUTRAL"
    UNKNOWN = "UNKNOWN"


class ConflictType(str, Enum):
    """Typology of epistemic conflicts between claims (Phase 13)."""
    DIRECT = "DIRECT"
    TEMPORAL = "TEMPORAL"
    SCOPE = "SCOPE"
    VERSION = "VERSION"
    SOURCE = "SOURCE"
    DEPENDENCY = "DEPENDENCY"
    DERIVATION = "DERIVATION"


class ConflictResolution(str, Enum):
    """Outcome of conflict resolution deliberation (Phase 14)."""
    CLAIM_A_SUPPORTED = "CLAIM_A_SUPPORTED"
    CLAIM_B_SUPPORTED = "CLAIM_B_SUPPORTED"
    BOTH_CONTEXTUALLY_VALID = "BOTH_CONTEXTUALLY_VALID"
    CONTESTED = "CONTESTED"
    UNKNOWN = "UNKNOWN"


class RevisionReason(str, Enum):
    """Standardized reasons for revising a belief (Phase 17)."""
    NEW_EVIDENCE = "NEW_EVIDENCE"
    CONTRADICTING_EVIDENCE = "CONTRADICTING_EVIDENCE"
    STALE_EVIDENCE = "STALE_EVIDENCE"
    SOURCE_CORRECTION = "SOURCE_CORRECTION"
    WORLD_STATE_CHANGE = "WORLD_STATE_CHANGE"
    CAPABILITY_CHANGE = "CAPABILITY_CHANGE"
    ENVIRONMENT_CHANGE = "ENVIRONMENT_CHANGE"
    EVALUATION_RESULT = "EVALUATION_RESULT"
    EXPERIMENT_RESULT = "EXPERIMENT_RESULT"
    USER_CORRECTION = "USER_CORRECTION"
    MODEL_ERROR = "MODEL_ERROR"
    DATA_CORRECTION = "DATA_CORRECTION"
    SCOPE_CHANGE = "SCOPE_CHANGE"
    VERSION_CHANGE = "VERSION_CHANGE"


class UncertaintyType(str, Enum):
    """Explicit classifications of uncertainty (Phase 30)."""
    NONE = "NONE"
    UNKNOWN = "UNKNOWN"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONFLICTED = "CONFLICTED"
    STALE = "STALE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    UNVERIFIED = "UNVERIFIED"
    NON_REPRODUCIBLE = "NON_REPRODUCIBLE"


class BeliefScope(str, Enum):
    """Operational scopes for beliefs and claims."""
    SYSTEM = "SYSTEM"
    PROJECT = "PROJECT"
    WORKFLOW = "WORKFLOW"
    TASK = "TASK"
    SERVICE = "SERVICE"
    CAPABILITY = "CAPABILITY"
    RESOURCE = "RESOURCE"
    ENVIRONMENT = "ENVIRONMENT"
    USER_SESSION = "USER_SESSION"
    AGENT_SWARM = "AGENT_SWARM"
    INFRASTRUCTURE = "INFRASTRUCTURE"


# =====================================================================
# DOMAIN ENTITIES (17 Entities per Specification)
# =====================================================================

class EvidenceSource(BaseModel):
    """Entity 1: Metadata regarding an origin source of evidence."""
    model_config = ConfigDict(extra="ignore")
    source_id: str = Field(default_factory=lambda: generate_uuid("src"))
    source_type: EvidenceClassification = EvidenceClassification.DIRECT_OBSERVATION
    name: str = ""
    historical_reliability: float = Field(default=0.8, ge=0.0, le=1.0)
    provenance_domain: str = "system"
    is_verified_authority: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class EvidenceItem(BaseModel):
    """Entity 2: Immutable item of evidence backing or refuting claims."""
    model_config = ConfigDict(extra="ignore")
    evidence_id: str = Field(default_factory=lambda: generate_uuid("evi"))
    source_id: str = ""
    source_type: EvidenceClassification = EvidenceClassification.DIRECT_OBSERVATION
    timestamp: datetime = Field(default_factory=utc_now)
    scope: str = BeliefScope.SYSTEM.value
    content: Dict[str, Any] = Field(default_factory=dict)
    summary: str = ""
    content_hash: str = ""
    freshness_ttl_seconds: int = 300
    integrity_verified: bool = True
    derived_from_evidence_ids: List[str] = Field(default_factory=list)
    reliability_weight: float = Field(default=0.8, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=utc_now)

    def model_post_init(self, __context: Any) -> None:
        if not self.content_hash:
            self.content_hash = compute_content_hash({
                "source_id": self.source_id,
                "source_type": self.source_type.value,
                "scope": self.scope,
                "content": self.content,
                "derived": self.derived_from_evidence_ids,
            })


class EvidenceRelationship(BaseModel):
    """Entity 3: Relationship between evidence items (e.g. derived_from, corroborated_by)."""
    model_config = ConfigDict(extra="ignore")
    relationship_id: str = Field(default_factory=lambda: generate_uuid("evrel"))
    source_evidence_id: str = ""
    target_evidence_id: str = ""
    relationship_type: str = "DERIVED_FROM"  # DERIVED_FROM, CORROBORATES, REPLACES
    created_at: datetime = Field(default_factory=utc_now)


class EvidenceAssessment(BaseModel):
    """Entity 4: Formal arbitration assessment of an evidence item against a claim."""
    model_config = ConfigDict(extra="ignore")
    assessment_id: str = Field(default_factory=lambda: generate_uuid("evasm"))
    evidence_id: str = ""
    claim_id: str = ""
    outcome: ArbitrationOutcome = ArbitrationOutcome.NEUTRAL
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    explanation: str = ""
    assessed_at: datetime = Field(default_factory=utc_now)


class Claim(BaseModel):
    """Entity 5: A proposition about an entity, state, capability, or strategy."""
    model_config = ConfigDict(extra="ignore")
    claim_id: str = Field(default_factory=lambda: generate_uuid("clm"))
    subject: str = ""
    predicate: str = ""
    object_value: Any = None
    scope: str = BeliefScope.SYSTEM.value
    valid_from: datetime = Field(default_factory=utc_now)
    valid_until: Optional[datetime] = None
    version: int = 1
    uncertainty: float = Field(default=0.2, ge=0.0, le=1.0)
    uncertainty_type: UncertaintyType = UncertaintyType.NONE
    provenance: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ClaimVersion(BaseModel):
    """Entity 6: Immutable historical version of a claim proposition."""
    model_config = ConfigDict(extra="ignore")
    version_id: str = Field(default_factory=lambda: generate_uuid("clmv"))
    claim_id: str = ""
    version_number: int = 1
    subject: str = ""
    predicate: str = ""
    object_value: Any = None
    scope: str = BeliefScope.SYSTEM.value
    valid_from: datetime = Field(default_factory=utc_now)
    valid_until: Optional[datetime] = None
    uncertainty: float = 0.2
    uncertainty_type: UncertaintyType = UncertaintyType.NONE
    created_at: datetime = Field(default_factory=utc_now)


class Belief(BaseModel):
    """Entity 7: Persistent belief synthesizing claims, evidence, and uncertainty."""
    model_config = ConfigDict(extra="ignore")
    belief_id: str = Field(default_factory=lambda: generate_uuid("blf"))
    subject: str = ""
    predicate: str = ""
    claim_id: str = ""
    current_version: int = 1
    scope: str = BeliefScope.SYSTEM.value
    status: BeliefStatus = BeliefStatus.CANDIDATE
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    uncertainty: float = Field(default=0.5, ge=0.0, le=1.0)
    uncertainty_type: UncertaintyType = UncertaintyType.NONE
    valid_from: datetime = Field(default_factory=utc_now)
    valid_until: Optional[datetime] = None
    last_verified_at: Optional[datetime] = None
    last_evaluated_at: Optional[datetime] = None
    freshness_ttl_seconds: int = 3600
    is_stale: bool = False
    evidence_ids: List[str] = Field(default_factory=list)
    contradiction_evidence_ids: List[str] = Field(default_factory=list)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class BeliefVersion(BaseModel):
    """Entity 8: Immutable historical version snapshot of a belief."""
    model_config = ConfigDict(extra="ignore")
    version_id: str = Field(default_factory=lambda: generate_uuid("blfv"))
    belief_id: str = ""
    version_number: int = 1
    status: BeliefStatus = BeliefStatus.CANDIDATE
    confidence: float = 0.5
    uncertainty: float = 0.5
    uncertainty_type: UncertaintyType = UncertaintyType.NONE
    claim_id: str = ""
    evidence_ids: List[str] = Field(default_factory=list)
    contradiction_evidence_ids: List[str] = Field(default_factory=list)
    revision_reason: RevisionReason = RevisionReason.NEW_EVIDENCE
    revision_notes: str = ""
    version_hash: str = ""
    created_at: datetime = Field(default_factory=utc_now)

    def model_post_init(self, __context: Any) -> None:
        if not self.version_hash:
            self.version_hash = compute_content_hash({
                "belief_id": self.belief_id,
                "version_number": self.version_number,
                "status": self.status.value,
                "confidence": self.confidence,
                "claim_id": self.claim_id,
                "reason": self.revision_reason.value,
            })


class BeliefSupport(BaseModel):
    """Entity 9: Association link between supporting evidence and a belief."""
    model_config = ConfigDict(extra="ignore")
    support_id: str = Field(default_factory=lambda: generate_uuid("bsup"))
    belief_id: str = ""
    evidence_id: str = ""
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    directness: float = Field(default=1.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=utc_now)


class BeliefConflict(BaseModel):
    """Entity 10: Explicit conflict between two competing claims or beliefs."""
    model_config = ConfigDict(extra="ignore")
    conflict_id: str = Field(default_factory=lambda: generate_uuid("bcnf"))
    belief_id_a: str = ""
    belief_id_b: Optional[str] = None
    claim_id_a: str = ""
    claim_id_b: Optional[str] = None
    conflict_type: ConflictType = ConflictType.DIRECT
    resolution: ConflictResolution = ConflictResolution.CONTESTED
    competing_evidence_ids: List[str] = Field(default_factory=list)
    rationale: str = ""
    detected_at: datetime = Field(default_factory=utc_now)
    resolved_at: Optional[datetime] = None


class BeliefRevision(BaseModel):
    """Entity 11: Audit trail record of a non-destructive belief revision."""
    model_config = ConfigDict(extra="ignore")
    revision_id: str = Field(default_factory=lambda: generate_uuid("brev"))
    belief_id: str = ""
    prior_version_number: int = 1
    new_version_number: int = 2
    prior_status: BeliefStatus = BeliefStatus.CANDIDATE
    new_status: BeliefStatus = BeliefStatus.SUPPORTED
    prior_confidence: float = 0.5
    new_confidence: float = 0.6
    reason: RevisionReason = RevisionReason.NEW_EVIDENCE
    evidence_id_trigger: Optional[str] = None
    notes: str = ""
    timestamp: datetime = Field(default_factory=utc_now)


class BeliefDependency(BaseModel):
    """Entity 12: Epistemic dependency edge where child belief depends on parent belief."""
    model_config = ConfigDict(extra="ignore")
    dependency_id: str = Field(default_factory=lambda: generate_uuid("bdep"))
    parent_belief_id: str = ""
    child_belief_id: str = ""
    dependency_strength: float = Field(default=1.0, ge=0.0, le=1.0)
    is_hard_prerequisite: bool = True
    notes: str = ""
    created_at: datetime = Field(default_factory=utc_now)


class BeliefSnapshot(BaseModel):
    """Entity 13: Immutable point-in-time snapshot of the belief manifold for replay/auditing."""
    model_config = ConfigDict(extra="ignore")
    snapshot_id: str = Field(default_factory=lambda: generate_uuid("bsnap"))
    trigger_type: str = "MANUAL"  # DECISION_CONTEXT, EXPERIMENT_BASE, MISSION_CHECKPOINT, REPLAY
    reference_id: Optional[str] = None  # decision_id, run_id, mission_id
    scope: str = BeliefScope.SYSTEM.value
    beliefs_manifest: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_manifest: List[Dict[str, Any]] = Field(default_factory=list)
    integrity_hash: str = ""
    created_at: datetime = Field(default_factory=utc_now)

    def model_post_init(self, __context: Any) -> None:
        if not self.integrity_hash:
            self.integrity_hash = compute_content_hash({
                "snapshot_id": self.snapshot_id,
                "trigger_type": self.trigger_type,
                "reference_id": self.reference_id,
                "beliefs": self.beliefs_manifest,
            })


class BeliefValidation(BaseModel):
    """Entity 14: Formal verification record for a belief through independent testing/evaluation."""
    model_config = ConfigDict(extra="ignore")
    validation_id: str = Field(default_factory=lambda: generate_uuid("bval"))
    belief_id: str = ""
    validator_type: str = "INDEPENDENT_EVALUATION"  # TASK_104_EVAL, RUNTIME_VERIFICATION, EXPERIMENT
    validator_ref: str = ""
    passed: bool = True
    confidence_delta: float = 0.0
    evidence_produced_id: Optional[str] = None
    notes: str = ""
    validated_at: datetime = Field(default_factory=utc_now)


class BeliefCorrection(BaseModel):
    """Entity 15: Explicit user or system correction recorded against a belief."""
    model_config = ConfigDict(extra="ignore")
    correction_id: str = Field(default_factory=lambda: generate_uuid("bcor"))
    belief_id: str = ""
    source: str = "USER"  # USER, GOVERNANCE, AUTOMATED_AUDIT
    correction_statement: str = ""
    verified: bool = False
    evidence_id: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)


class BeliefExpiry(BaseModel):
    """Entity 16: Expiry and staleness tracking rule for a domain scope or predicate."""
    model_config = ConfigDict(extra="ignore")
    expiry_id: str = Field(default_factory=lambda: generate_uuid("bexp"))
    predicate_pattern: str = "*"
    scope: str = BeliefScope.SYSTEM.value
    ttl_seconds: int = 3600
    stale_action: str = "REVALIDATION_REQUIRED"  # STALE, REVALIDATION_REQUIRED, EXPIRED
    created_at: datetime = Field(default_factory=utc_now)


class BeliefEvent(BaseModel):
    """Entity 17: Domain audit event emitted onto the event bus."""
    model_config = ConfigDict(extra="ignore")
    event_id: str = Field(default_factory=lambda: generate_uuid("bev"))
    event_type: str = "belief.created"  # belief.created, belief.revised, evidence.ingested, etc.
    belief_id: Optional[str] = None
    evidence_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    emitted_at: datetime = Field(default_factory=utc_now)
