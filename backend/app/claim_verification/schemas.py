"""Pydantic API request and response schemas for Task 116 Claim Verification Engine."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CreateVerificationRequest(BaseModel):
    """Payload to initiate an autonomous verification case."""
    claim_text: str = Field(..., description="The claim or assertion to verify")
    title: Optional[str] = Field(None, description="Human-readable title of verification case")
    scope: Dict[str, Any] = Field(default_factory=dict, description="Scope constraints (temporal, entity, spatial)")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="Initial source descriptors")
    evidence: List[Dict[str, Any]] = Field(default_factory=list, description="Initial evidence artifact descriptors")
    idempotency_key: Optional[str] = Field(None, description="Unique key to prevent duplicate verification runs")
    correlation_id: Optional[str] = Field(None, description="Trace or correlation identifier")


class VerificationCaseResponse(BaseModel):
    """Authoritative representation of a verification case."""
    case_id: str
    version: int = 1
    title: str
    claim_id: str
    status: str
    scope: Dict[str, Any] = Field(default_factory=dict)
    resolution_summary: str = ""
    idempotency_key: Optional[str] = None
    correlation_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class VerificationResultResponse(BaseModel):
    """Detailed outcome of a completed verification execution."""
    result_id: str
    case_id: str
    claim_id: str
    status: str
    scope: Dict[str, Any] = Field(default_factory=dict)
    justification: str
    evidence_ids: List[str] = Field(default_factory=list)
    contradiction_ids: List[str] = Field(default_factory=list)
    method_types: List[str] = Field(default_factory=list)
    uncertainty_profile: Dict[str, Any] = Field(default_factory=dict)
    gaps: List[str] = Field(default_factory=list)
    reproducibility_status: str
    validity_window_start: Optional[datetime] = None
    validity_window_end: Optional[datetime] = None
    verified_at: datetime
    expires_at: Optional[datetime] = None


class ClaimResponse(BaseModel):
    """Decomposed claim and fragment details."""
    claim_id: str
    canonical_text: str
    normalized_text: str
    claim_type: str
    subject: str
    predicate: str
    object_val: str
    temporal_scope: Dict[str, Any] = Field(default_factory=dict)
    entity_scope: List[str] = Field(default_factory=list)
    fragments: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float
    uncertainty: float
    created_at: datetime


class SourceResponse(BaseModel):
    """Identified information source with trust profile."""
    source_id: str
    uri: str
    category: str
    publisher: str
    owner: str
    auth_state: str
    trust_profile: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool
    created_at: datetime


class EvidenceArtifactResponse(BaseModel):
    """Extracted evidence artifact with quality dimensions."""
    evidence_id: str
    source_id: str
    snapshot_id: Optional[str] = None
    location: str = ""
    content_hash: str
    content_text: str
    quality_profile: Dict[str, Any] = Field(default_factory=dict)
    direct_status: bool = True
    is_synthetic: bool = False
    is_simulated: bool = False
    created_at: datetime


class ProvenanceGraphResponse(BaseModel):
    """Nodes and edges representing lineage DAG."""
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]


class ContradictionResponse(BaseModel):
    """Detailed conflict or discrepancy."""
    contradiction_id: str
    case_id: str
    contradiction_type: str
    claim_a_id: str
    claim_b_id: Optional[str] = None
    evidence_a_id: str
    evidence_b_id: str
    description: str
    severity: float
    status: str
    created_at: datetime


class VerificationGapResponse(BaseModel):
    """Unresolved information gap."""
    gap_id: str
    case_id: str
    missing_evidence_desc: str
    impact_reason: str
    affected_claim_id: str
    possible_methods: List[str] = Field(default_factory=list)
    expected_info_gain: float
    cost: float
    risk: float
    urgency: float
    created_at: datetime


class VerificationExplanationResponse(BaseModel):
    """Explanation tree explaining why a claim has its verification status."""
    case_id: str
    status: str
    justification: str
    claim: Dict[str, Any]
    supporting_evidence: List[Dict[str, Any]]
    contradictions: List[Dict[str, Any]]
    corroboration: Dict[str, Any]
    independence: Dict[str, Any]
    reproducibility: Dict[str, Any]
    unresolved_gaps: List[Dict[str, Any]]
    belief_proposal: Optional[Dict[str, Any]] = None
    integrity_checks: List[Dict[str, Any]] = Field(default_factory=list)
