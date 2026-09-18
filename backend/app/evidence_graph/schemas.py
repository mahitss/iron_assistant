"""Pydantic schemas for Task 117 Evidence Graph API."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.evidence_graph.domain import (
    EvidenceGraphEdgeType,
    EvidenceGraphNodeType,
    FreshnessState,
    ImpactSeverity,
    LifecycleStatus,
    ProvenanceStatus,
    RevalidationRecommendation,
)


class EvidenceGraphNodeCreate(BaseModel):
    node_id: str
    node_type: str = "EVIDENCE"
    source_system: str = "generic"
    version: int = 1
    temporal_scope: Dict[str, Any] = Field(default_factory=dict)
    lifecycle_status: str = "ACTIVE"
    provenance_status: str = "UNVERIFIED"
    freshness_state: str = "FRESH"
    payload: Dict[str, Any] = Field(default_factory=dict)


class EvidenceGraphNodeResponse(BaseModel):
    node_id: str
    node_type: str
    source_system: str
    version: int
    created_at: str
    updated_at: str
    temporal_scope: Dict[str, Any]
    lifecycle_status: str
    provenance_status: str
    freshness_state: str
    integrity_state: str
    payload: Dict[str, Any]
    content_hash: str


class EvidenceGraphEdgeCreate(BaseModel):
    edge_id: Optional[str] = None
    source_node_id: str
    target_node_id: str
    relationship_type: str = "DEPENDS_ON"
    confidence: float = 1.0
    provenance: Dict[str, Any] = Field(default_factory=dict)
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    source_system: str = "generic"
    actor_component: str = "system"


class EvidenceGraphEdgeResponse(BaseModel):
    edge_id: str
    source_node_id: str
    target_node_id: str
    relationship_type: str
    confidence: float
    provenance: Dict[str, Any]
    created_at: str
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    observed_at: Optional[str] = None
    discovered_at: Optional[str] = None
    source_system: str
    actor_component: str
    evidence_references: List[str] = Field(default_factory=list)
    derivation_method: str = "DIRECT"
    verification_status: str = "UNVERIFIED"


class TraversalResponse(BaseModel):
    start_node_id: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    depth_reached: int
    is_truncated: bool
    status: str
    cycles: List[List[str]] = Field(default_factory=list)


class MinimalChainResponse(BaseModel):
    target_node_id: str
    chain_type: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    depth: int
    root_sources: List[str]


class ImpactAssessmentResponse(BaseModel):
    target_node_id: str
    target_node_type: str
    root_cause_node_id: str
    cause_reason: str
    severity: str
    direct_impacts: List[Dict[str, Any]]
    indirect_impacts: List[Dict[str, Any]]
    impacted_claims: List[str]
    impacted_verifications: List[str]
    impacted_beliefs: List[str]
    impacted_decisions: List[str]
    impacted_missions: List[str]
    impacted_situations: List[str]
    impacted_hypotheses: List[str]
    impacted_memories: List[str]
    impacted_strategies: List[str]
    impacted_self_models: List[str]
    revalidation_candidates: List[Dict[str, Any]]
    timestamp: str


class RevalidationCandidateResponse(BaseModel):
    candidate_id: str
    affected_node_id: str
    affected_node_type: str
    reason: str
    upstream_cause_id: str
    severity: str
    freshness_state: str
    decision_impact: Optional[str] = None
    mission_impact: Optional[str] = None
    resource_estimate: float
    expected_information_value: float
    deadline: Optional[str] = None
    required_capability: str
    recommended_next_step: str
    status: str
    created_at: str


class SourceConcentrationResponse(BaseModel):
    target_node_id: str
    origin_count: int
    dependency_depth: int
    independent_source_estimate: int
    shared_origin_groups: Dict[str, List[str]]
    is_high_concentration: bool
    details: str


class EvidenceFragilityResponse(BaseModel):
    node_id: str
    source_concentration_score: float
    provenance_completeness_score: float
    freshness_score: float
    reproducibility_score: float
    dependency_depth: int
    contradiction_exposure_score: float
    single_source_dependence: bool
    transformation_count: int
    unresolved_gaps_count: int
    dimension_findings: Dict[str, Any]
    overall_fragility_label: str
    created_at: str


class ProvenanceGapResponse(BaseModel):
    gap_id: str
    affected_node_id: str
    missing_relationship: str
    expected_node_type: str
    reason: str
    severity: str
    recoverable: bool
    acquisition_method: Optional[str] = None
    confidence: float
    created_at: str


class SnapshotResponse(BaseModel):
    snapshot_id: str
    timestamp: str
    graph_version: int
    node_count: int
    edge_count: int
    query_scope: Dict[str, Any]
    filters: Dict[str, Any]
    checksum: str
    creation_reason: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]


class GraphDiffResponse(BaseModel):
    base_ref: str
    target_ref: str
    added_nodes: List[Dict[str, Any]]
    removed_nodes: List[Dict[str, Any]]
    changed_nodes: List[Dict[str, Any]]
    added_edges: List[Dict[str, Any]]
    removed_edges: List[Dict[str, Any]]
    changed_edges: List[Dict[str, Any]]
    invalidated_nodes: List[Dict[str, Any]]
    stale_nodes: List[Dict[str, Any]]
    superseded_nodes: List[Dict[str, Any]]
    timestamp: str


class GraphHealthResponse(BaseModel):
    provenance_completeness_rate: float
    orphan_rate: float
    duplicate_rate: float
    stale_edge_rate: float
    reconciliation_lag_seconds: float
    cycle_rate: float
    unresolved_gap_rate: float
    query_failure_rate: float
    snapshot_consistency_ok: bool
    sync_state: str
    component_health: Dict[str, Any]
    created_at: str


class LineageRecordIngest(BaseModel):
    producer: str
    object_type: str
    object_id: str
    object_version: int = 1
    input_references: List[str] = Field(default_factory=list)
    output_references: List[str] = Field(default_factory=list)
    operation: str = "PRODUCE"
    timestamp: Optional[str] = None
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    provenance: Dict[str, Any] = Field(default_factory=dict)
    scope: Dict[str, Any] = Field(default_factory=dict)
    deterministic_status: bool = True
