"""Pydantic schemas and DTO contracts for Task 107:
Autonomous Belief, Evidence Arbitration, Conflict Resolution & World-Model Revision Engine.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.belief.domain import (
    ArbitrationOutcome,
    BeliefScope,
    BeliefStatus,
    ConflictResolution,
    ConflictType,
    EvidenceClassification,
    RevisionReason,
    UncertaintyType,
)


class ClaimCreateRequest(BaseModel):
    subject: str = Field(..., description="Entity or topic of proposition")
    predicate: str = Field(..., description="Property or relation being claimed")
    object_value: Any = Field(..., description="Claimed state or value")
    scope: str = Field(default=BeliefScope.SYSTEM.value)
    uncertainty: float = Field(default=0.2, ge=0.0, le=1.0)
    uncertainty_type: UncertaintyType = Field(default=UncertaintyType.NONE)
    provenance: Dict[str, Any] = Field(default_factory=dict)


class ClaimResponse(BaseModel):
    claim_id: str
    subject: str
    predicate: str
    object_value: Any
    scope: str
    valid_from: datetime
    valid_until: Optional[datetime] = None
    version: int
    uncertainty: float
    uncertainty_type: UncertaintyType
    provenance: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class EvidenceIngestRequest(BaseModel):
    source_id: str
    source_type: EvidenceClassification = Field(default=EvidenceClassification.DIRECT_OBSERVATION)
    scope: str = Field(default=BeliefScope.SYSTEM.value)
    content: Dict[str, Any] = Field(default_factory=dict)
    summary: str = ""
    freshness_ttl_seconds: int = Field(default=300, ge=1)
    derived_from_evidence_ids: List[str] = Field(default_factory=list)
    reliability_weight: float = Field(default=0.8, ge=0.0, le=1.0)


class EvidenceItemResponse(BaseModel):
    evidence_id: str
    source_id: str
    source_type: EvidenceClassification
    timestamp: datetime
    scope: str
    content: Dict[str, Any]
    summary: str
    content_hash: str
    freshness_ttl_seconds: int
    integrity_verified: bool
    derived_from_evidence_ids: List[str]
    reliability_weight: float
    created_at: datetime


class BeliefCreateRequest(BaseModel):
    subject: str
    predicate: str
    object_value: Any
    scope: str = Field(default=BeliefScope.SYSTEM.value)
    initial_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence_ids: List[str] = Field(default_factory=list)
    freshness_ttl_seconds: int = Field(default=3600, ge=1)
    provenance: Dict[str, Any] = Field(default_factory=dict)


class BeliefResponse(BaseModel):
    belief_id: str
    subject: str
    predicate: str
    claim_id: str
    current_version: int
    scope: str
    status: BeliefStatus
    confidence: float
    uncertainty: float
    uncertainty_type: UncertaintyType
    valid_from: datetime
    valid_until: Optional[datetime] = None
    last_verified_at: Optional[datetime] = None
    last_evaluated_at: Optional[datetime] = None
    freshness_ttl_seconds: int
    is_stale: bool
    evidence_ids: List[str]
    contradiction_evidence_ids: List[str]
    provenance: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class BeliefVersionResponse(BaseModel):
    version_id: str
    belief_id: str
    version_number: int
    status: BeliefStatus
    confidence: float
    uncertainty: float
    uncertainty_type: UncertaintyType
    claim_id: str
    evidence_ids: List[str]
    contradiction_evidence_ids: List[str]
    revision_reason: RevisionReason
    revision_notes: str
    version_hash: str
    created_at: datetime


class BeliefRevisionRequest(BaseModel):
    new_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    new_status: Optional[BeliefStatus] = None
    reason: RevisionReason = Field(default=RevisionReason.NEW_EVIDENCE)
    evidence_id_trigger: Optional[str] = None
    notes: str = ""


class BeliefConflictResponse(BaseModel):
    conflict_id: str
    belief_id_a: str
    belief_id_b: Optional[str] = None
    claim_id_a: str
    claim_id_b: Optional[str] = None
    conflict_type: ConflictType
    resolution: ConflictResolution
    competing_evidence_ids: List[str]
    rationale: str
    detected_at: datetime
    resolved_at: Optional[datetime] = None


class BeliefDependencyCreateRequest(BaseModel):
    parent_belief_id: str
    child_belief_id: str
    dependency_strength: float = Field(default=1.0, ge=0.0, le=1.0)
    is_hard_prerequisite: bool = True
    notes: str = ""


class BeliefDependencyResponse(BaseModel):
    dependency_id: str
    parent_belief_id: str
    child_belief_id: str
    dependency_strength: float
    is_hard_prerequisite: bool
    notes: str
    created_at: datetime


class BeliefSnapshotCreateRequest(BaseModel):
    trigger_type: str = Field(default="MANUAL")  # DECISION_CONTEXT, EXPERIMENT_BASE, MISSION_CHECKPOINT
    reference_id: Optional[str] = None
    scope: str = Field(default=BeliefScope.SYSTEM.value)


class BeliefSnapshotResponse(BaseModel):
    snapshot_id: str
    trigger_type: str
    reference_id: Optional[str] = None
    scope: str
    beliefs_manifest: List[Dict[str, Any]]
    evidence_manifest: List[Dict[str, Any]]
    integrity_hash: str
    created_at: datetime


class BeliefEvidencePack(BaseModel):
    """Compact context pack formatted for Task 93 Context Assembler & Task 94 Decision Engine."""
    belief_id: str
    subject: str
    predicate: str
    status: BeliefStatus
    confidence: float
    uncertainty: float
    uncertainty_type: UncertaintyType
    is_stale: bool
    freshness_seconds: float
    supporting_evidence_count: int
    contradicting_evidence_count: int
    evidence_summaries: List[str]
    contradiction_summaries: List[str]
    limitations: List[str]
    epistemic_disclaimer: str = (
        "EPISTEMIC NOTICE: This belief represents empirical evidence and probabilistic confidence. "
        "It is NOT ground truth, NOT authorization, and NOT policy."
    )


class BeliefExplanationResponse(BaseModel):
    """Structured explanation answering WHAT, WHEN, WHY/EVIDENCE, WHEN NOT, CONFIDENCE, LIMITATIONS."""
    belief_id: str
    subject: str
    predicate: str
    status: BeliefStatus
    confidence: float
    uncertainty: float
    uncertainty_type: UncertaintyType
    what: str
    when: str
    why_evidence: List[str]
    when_not_contradictions: List[str]
    limitations: List[str]
    last_verified: Optional[str] = None
    revalidation_triggers: List[str] = Field(default_factory=list)


class BeliefDashboardMetrics(BaseModel):
    total_beliefs: int
    confident_beliefs: int
    contested_beliefs: int
    stale_beliefs: int
    unknown_beliefs: int
    total_evidence_items: int
    active_conflicts: int
    total_revisions: int
    total_snapshots: int
    epistemic_invariants_enforced: bool = True
