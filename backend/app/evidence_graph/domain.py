"""Domain models, enums, and data structures for Task 117:
Kairo Autonomous Evidence Graph, Provenance Intelligence & Verification Dependency Engine.

Architectural Invariant:
SOURCE -> EVIDENCE -> TRANSFORMATION -> CLAIM -> VERIFICATION -> DOWNSTREAM DEPENDENCY

Existing systems remain authoritative for their own domains:
- Knowledge Graph (Task 97) owns semantic entity-relation truth.
- Belief Engine (Task 107) owns belief arbitration and lifecycle.
- Decision Intelligence (Task 94) owns decision selection and policy.
- Mission Control (Task 100) owns mission milestones and state.
- SecurityCenter & EmergencyStop own authorization and fail-closed bounds.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any, Dict, List, Optional, Set, Union
import uuid


class EvidenceGraphNodeType(str, Enum):
    SOURCE = "SOURCE"
    SOURCE_SNAPSHOT = "SOURCE_SNAPSHOT"
    DOCUMENT = "DOCUMENT"
    ARTIFACT = "ARTIFACT"
    EVIDENCE = "EVIDENCE"
    CLAIM = "CLAIM"
    CLAIM_FRAGMENT = "CLAIM_FRAGMENT"
    VERIFICATION_CASE = "VERIFICATION_CASE"
    VERIFICATION_RESULT = "VERIFICATION_RESULT"
    OBSERVATION = "OBSERVATION"
    HYPOTHESIS = "HYPOTHESIS"
    BELIEF = "BELIEF"
    WORLD_STATE_ASSERTION = "WORLD_STATE_ASSERTION"
    MEMORY = "MEMORY"
    KNOWLEDGE_NODE = "KNOWLEDGE_NODE"
    KNOWLEDGE_EDGE = "KNOWLEDGE_EDGE"
    DECISION = "DECISION"
    ACTION = "ACTION"
    MISSION = "MISSION"
    SITUATION = "SITUATION"
    AGENT_RESULT = "AGENT_RESULT"
    EXPERIMENT = "EXPERIMENT"
    SIMULATION = "SIMULATION"
    STRATEGY = "STRATEGY"
    EVALUATION_RESULT = "EVALUATION_RESULT"
    SELF_MODEL_ASSERTION = "SELF_MODEL_ASSERTION"


class EvidenceGraphEdgeType(str, Enum):
    DERIVED_FROM = "DERIVED_FROM"
    EXTRACTED_FROM = "EXTRACTED_FROM"
    TRANSFORMED_FROM = "TRANSFORMED_FROM"
    SUMMARIZED_FROM = "SUMMARIZED_FROM"
    GENERATED_FROM = "GENERATED_FROM"
    OBSERVED_FROM = "OBSERVED_FROM"
    SUPPORTED_BY = "SUPPORTED_BY"
    CONTRADICTED_BY = "CONTRADICTED_BY"
    VERIFIED_BY = "VERIFIED_BY"
    CORROBORATED_BY = "CORROBORATED_BY"
    DEPENDS_ON = "DEPENDS_ON"
    REQUIRES = "REQUIRES"
    SUPERSEDES = "SUPERSEDES"
    SUPERSEDED_BY = "SUPERSEDED_BY"
    INVALIDATED_BY = "INVALIDATED_BY"
    REVALIDATED_BY = "REVALIDATED_BY"
    CONFIRMED_BY = "CONFIRMED_BY"
    REFUTED_BY = "REFUTED_BY"
    SCOPED_BY = "SCOPED_BY"
    CONSTRAINED_BY = "CONSTRAINED_BY"
    PRODUCED_BY = "PRODUCED_BY"
    REPORTED_BY = "REPORTED_BY"
    MEASURED_BY = "MEASURED_BY"
    REPRODUCED_BY = "REPRODUCED_BY"
    SIMULATED_BY = "SIMULATED_BY"
    EVALUATED_BY = "EVALUATED_BY"
    USED_BY = "USED_BY"


class ImpactSeverity(str, Enum):
    DIRECT = "DIRECT"
    INDIRECT = "INDIRECT"
    POSSIBLE = "POSSIBLE"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    UNKNOWN = "UNKNOWN"


class FreshnessState(str, Enum):
    FRESH = "FRESH"
    STALE = "STALE"
    EXPIRED = "EXPIRED"
    SUPERSEDED = "SUPERSEDED"
    INVALID = "INVALID"
    UNKNOWN = "UNKNOWN"


class LifecycleStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"
    ORPHANED_REFERENCE = "ORPHANED_REFERENCE"
    SUPERSEDED = "SUPERSEDED"
    INVALIDATED = "INVALIDATED"


class ProvenanceStatus(str, Enum):
    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    CONTRADICTED = "CONTRADICTED"
    UNCERTAIN = "UNCERTAIN"
    GAP_DETECTED = "GAP_DETECTED"


class IntegrityState(str, Enum):
    INTACT = "INTACT"
    HASH_MISMATCH = "HASH_MISMATCH"
    MUTATED = "MUTATED"
    CORRUPTED = "CORRUPTED"
    UNVERIFIED = "UNVERIFIED"


class RevalidationRecommendation(str, Enum):
    REVALIDATE_NOW = "REVALIDATE_NOW"
    REVALIDATE_LATER = "REVALIDATE_LATER"
    OBSERVE = "OBSERVE"
    WAIT = "WAIT"
    ESCALATE = "ESCALATE"
    IGNORE = "IGNORE"
    UNKNOWN = "UNKNOWN"


class ProvenanceCompleteness(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    INCOMPLETE = "INCOMPLETE"
    UNKNOWN = "UNKNOWN"


class IndependenceStatus(str, Enum):
    INDEPENDENT = "INDEPENDENT"
    LIKELY_INDEPENDENT = "LIKELY_INDEPENDENT"
    POSSIBLY_DEPENDENT = "POSSIBLY_DEPENDENT"
    DEPENDENT = "DEPENDENT"
    DIRECT_COPY = "DIRECT_COPY"
    COMMON_ORIGIN = "COMMON_ORIGIN"
    UNKNOWN = "UNKNOWN"


class DuplicateEvidenceType(str, Enum):
    EXACT_DUPLICATE = "EXACT_DUPLICATE"
    LIKELY_DUPLICATE = "LIKELY_DUPLICATE"
    POSSIBLE_DUPLICATE = "POSSIBLE_DUPLICATE"
    SEMANTICALLY_SIMILAR = "SEMANTICALLY_SIMILAR"
    DISTINCT = "DISTINCT"
    UNKNOWN = "UNKNOWN"


class GraphSyncState(str, Enum):
    GRAPH_CURRENT = "GRAPH_CURRENT"
    GRAPH_LAGGING = "GRAPH_LAGGING"
    GRAPH_RECONCILING = "GRAPH_RECONCILING"
    GRAPH_INCOMPLETE = "GRAPH_INCOMPLETE"


class DiffChangeType(str, Enum):
    ADDED_NODE = "ADDED_NODE"
    REMOVED_NODE = "REMOVED_NODE"
    CHANGED_NODE = "CHANGED_NODE"
    ADDED_EDGE = "ADDED_EDGE"
    REMOVED_EDGE = "REMOVED_EDGE"
    CHANGED_EDGE = "CHANGED_EDGE"
    INVALIDATED_NODE = "INVALIDATED_NODE"
    STALE_NODE = "STALE_NODE"
    SUPERSEDED_NODE = "SUPERSEDED_NODE"


class ProvenanceMinimalityType(str, Enum):
    MINIMAL_KNOWN_CHAIN = "MINIMAL_KNOWN_CHAIN"
    BOUNDED_MINIMAL_CHAIN = "BOUNDED_MINIMAL_CHAIN"
    COMPLETE_CHAIN = "COMPLETE_CHAIN"
    PARTIAL_CHAIN = "PARTIAL_CHAIN"


@dataclass
class LineageRecord:
    """Canonical cross-system lineage contract matching Section 52."""
    producer: str
    object_type: str
    object_id: str
    object_version: int = 1
    input_references: List[str] = field(default_factory=list)
    output_references: List[str] = field(default_factory=list)
    operation: str = "PRODUCE"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    causation_id: Optional[str] = None
    provenance: Dict[str, Any] = field(default_factory=dict)
    scope: Dict[str, Any] = field(default_factory=dict)
    deterministic_status: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "producer": self.producer,
            "object_type": self.object_type,
            "object_id": self.object_id,
            "object_version": self.object_version,
            "input_references": list(self.input_references),
            "output_references": list(self.output_references),
            "operation": self.operation,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "provenance": dict(self.provenance),
            "scope": dict(self.scope),
            "deterministic_status": self.deterministic_status,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LineageRecord:
        return cls(
            producer=data.get("producer", "unknown"),
            object_type=data.get("object_type", "UNKNOWN"),
            object_id=data.get("object_id", ""),
            object_version=int(data.get("object_version", 1)),
            input_references=list(data.get("input_references") or []),
            output_references=list(data.get("output_references") or []),
            operation=data.get("operation", "PRODUCE"),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            correlation_id=data.get("correlation_id", str(uuid.uuid4())),
            causation_id=data.get("causation_id"),
            provenance=dict(data.get("provenance") or {}),
            scope=dict(data.get("scope") or {}),
            deterministic_status=bool(data.get("deterministic_status", True)),
        )


@dataclass
class EvidenceGraphNode:
    """Stable node in the directed evidence provenance & dependency graph."""
    node_id: str
    node_type: EvidenceGraphNodeType
    source_system: str
    version: int = 1
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    temporal_scope: Dict[str, Any] = field(default_factory=lambda: {
        "event_time": None,
        "observed_time": None,
        "ingested_time": None,
        "processed_time": None,
        "effective_time": None,
        "valid_from": None,
        "valid_until": None,
    })
    lifecycle_status: LifecycleStatus = LifecycleStatus.ACTIVE
    provenance_status: ProvenanceStatus = ProvenanceStatus.UNVERIFIED
    freshness_state: FreshnessState = FreshnessState.FRESH
    integrity_state: IntegrityState = IntegrityState.INTACT
    payload: Dict[str, Any] = field(default_factory=dict)
    content_hash: str = ""

    def __post_init__(self):
        if not self.content_hash and self.payload:
            payload_str = json.dumps(self.payload, sort_keys=True)
            self.content_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value if hasattr(self.node_type, "value") else str(self.node_type),
            "source_system": self.source_system,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "temporal_scope": dict(self.temporal_scope),
            "lifecycle_status": self.lifecycle_status.value if hasattr(self.lifecycle_status, "value") else str(self.lifecycle_status),
            "provenance_status": self.provenance_status.value if hasattr(self.provenance_status, "value") else str(self.provenance_status),
            "freshness_state": self.freshness_state.value if hasattr(self.freshness_state, "value") else str(self.freshness_state),
            "integrity_state": self.integrity_state.value if hasattr(self.integrity_state, "value") else str(self.integrity_state),
            "payload": dict(self.payload),
            "content_hash": self.content_hash,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EvidenceGraphNode:
        return cls(
            node_id=data["node_id"],
            node_type=EvidenceGraphNodeType(data.get("node_type", "EVIDENCE")),
            source_system=data.get("source_system", "generic"),
            version=int(data.get("version", 1)),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
            temporal_scope=dict(data.get("temporal_scope") or {}),
            lifecycle_status=LifecycleStatus(data.get("lifecycle_status", "ACTIVE")),
            provenance_status=ProvenanceStatus(data.get("provenance_status", "UNVERIFIED")),
            freshness_state=FreshnessState(data.get("freshness_state", "FRESH")),
            integrity_state=IntegrityState(data.get("integrity_state", "INTACT")),
            payload=dict(data.get("payload") or {}),
            content_hash=data.get("content_hash", ""),
        )


@dataclass
class EvidenceGraphEdge:
    """Explicitly typed directed relationship with comprehensive provenance metadata."""
    edge_id: str
    source_node_id: str
    target_node_id: str
    relationship_type: EvidenceGraphEdgeType
    confidence: float = 1.0
    provenance: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    observed_at: Optional[str] = None
    discovered_at: Optional[str] = None
    source_system: str = "generic"
    actor_component: str = "system"
    evidence_references: List[str] = field(default_factory=list)
    derivation_method: str = "DIRECT"
    verification_status: str = "UNVERIFIED"
    supersession: Optional[Dict[str, Any]] = None
    correction: Optional[Dict[str, Any]] = None
    scope: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "relationship_type": self.relationship_type.value if hasattr(self.relationship_type, "value") else str(self.relationship_type),
            "confidence": self.confidence,
            "provenance": dict(self.provenance),
            "created_at": self.created_at,
            "valid_from": self.valid_from,
            "valid_until": self.valid_until,
            "observed_at": self.observed_at,
            "discovered_at": self.discovered_at,
            "source_system": self.source_system,
            "actor_component": self.actor_component,
            "evidence_references": list(self.evidence_references),
            "derivation_method": self.derivation_method,
            "verification_status": self.verification_status,
            "supersession": self.supersession,
            "correction": self.correction,
            "scope": dict(self.scope),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EvidenceGraphEdge:
        return cls(
            edge_id=data.get("edge_id", str(uuid.uuid4())),
            source_node_id=data["source_node_id"],
            target_node_id=data["target_node_id"],
            relationship_type=EvidenceGraphEdgeType(data.get("relationship_type", "DEPENDS_ON")),
            confidence=float(data.get("confidence", 1.0)),
            provenance=dict(data.get("provenance") or {}),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            valid_from=data.get("valid_from"),
            valid_until=data.get("valid_until"),
            observed_at=data.get("observed_at"),
            discovered_at=data.get("discovered_at"),
            source_system=data.get("source_system", "generic"),
            actor_component=data.get("actor_component", "system"),
            evidence_references=list(data.get("evidence_references") or []),
            derivation_method=data.get("derivation_method", "DIRECT"),
            verification_status=data.get("verification_status", "UNVERIFIED"),
            supersession=data.get("supersession"),
            correction=data.get("correction"),
            scope=dict(data.get("scope") or {}),
        )


@dataclass
class EvidenceGraphNodeVersion:
    """Immutable version capture of a node."""
    version_id: str
    node_id: str
    version_number: int
    node_type: EvidenceGraphNodeType
    payload: Dict[str, Any]
    content_hash: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    supersedes_version: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version_id": self.version_id,
            "node_id": self.node_id,
            "version_number": self.version_number,
            "node_type": self.node_type.value if hasattr(self.node_type, "value") else str(self.node_type),
            "payload": dict(self.payload),
            "content_hash": self.content_hash,
            "created_at": self.created_at,
            "supersedes_version": self.supersedes_version,
        }


@dataclass
class EvidenceGraphEdgeVersion:
    """Immutable version capture of an edge."""
    version_id: str
    edge_id: str
    version_number: int
    relationship_type: EvidenceGraphEdgeType
    confidence: float
    metadata_payload: Dict[str, Any]
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version_id": self.version_id,
            "edge_id": self.edge_id,
            "version_number": self.version_number,
            "relationship_type": self.relationship_type.value if hasattr(self.relationship_type, "value") else str(self.relationship_type),
            "confidence": self.confidence,
            "metadata_payload": dict(self.metadata_payload),
            "created_at": self.created_at,
        }


@dataclass
class RevalidationCandidate:
    """Revalidation requirement to feed into Attention/Control Plane."""
    candidate_id: str
    affected_node_id: str
    affected_node_type: str
    reason: str
    upstream_cause_id: str
    severity: ImpactSeverity = ImpactSeverity.DIRECT
    freshness_state: FreshnessState = FreshnessState.STALE
    decision_impact: Optional[str] = None
    mission_impact: Optional[str] = None
    resource_estimate: float = 1.0
    expected_information_value: float = 0.8
    deadline: Optional[str] = None
    required_capability: str = "general_verification"
    recommended_next_step: RevalidationRecommendation = RevalidationRecommendation.REVALIDATE_NOW
    status: str = "PENDING"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "affected_node_id": self.affected_node_id,
            "affected_node_type": self.affected_node_type,
            "reason": self.reason,
            "upstream_cause_id": self.upstream_cause_id,
            "severity": self.severity.value if hasattr(self.severity, "value") else str(self.severity),
            "freshness_state": self.freshness_state.value if hasattr(self.freshness_state, "value") else str(self.freshness_state),
            "decision_impact": self.decision_impact,
            "mission_impact": self.mission_impact,
            "resource_estimate": self.resource_estimate,
            "expected_information_value": self.expected_information_value,
            "deadline": self.deadline,
            "required_capability": self.required_capability,
            "recommended_next_step": self.recommended_next_step.value if hasattr(self.recommended_next_step, "value") else str(self.recommended_next_step),
            "status": self.status,
            "created_at": self.created_at,
        }


@dataclass
class ImpactAssessment:
    """Structured blast-radius assessment output."""
    target_node_id: str
    target_node_type: str
    root_cause_node_id: str
    cause_reason: str
    severity: ImpactSeverity = ImpactSeverity.DIRECT
    direct_impacts: List[Dict[str, Any]] = field(default_factory=list)
    indirect_impacts: List[Dict[str, Any]] = field(default_factory=list)
    impacted_claims: List[str] = field(default_factory=list)
    impacted_verifications: List[str] = field(default_factory=list)
    impacted_beliefs: List[str] = field(default_factory=list)
    impacted_decisions: List[str] = field(default_factory=list)
    impacted_missions: List[str] = field(default_factory=list)
    impacted_situations: List[str] = field(default_factory=list)
    impacted_hypotheses: List[str] = field(default_factory=list)
    impacted_memories: List[str] = field(default_factory=list)
    impacted_strategies: List[str] = field(default_factory=list)
    impacted_self_models: List[str] = field(default_factory=list)
    revalidation_candidates: List[RevalidationCandidate] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_node_id": self.target_node_id,
            "target_node_type": self.target_node_type,
            "root_cause_node_id": self.root_cause_node_id,
            "cause_reason": self.cause_reason,
            "severity": self.severity.value if hasattr(self.severity, "value") else str(self.severity),
            "direct_impacts": self.direct_impacts,
            "indirect_impacts": self.indirect_impacts,
            "impacted_claims": self.impacted_claims,
            "impacted_verifications": self.impacted_verifications,
            "impacted_beliefs": self.impacted_beliefs,
            "impacted_decisions": self.impacted_decisions,
            "impacted_missions": self.impacted_missions,
            "impacted_situations": self.impacted_situations,
            "impacted_hypotheses": self.impacted_hypotheses,
            "impacted_memories": self.impacted_memories,
            "impacted_strategies": self.impacted_strategies,
            "impacted_self_models": self.impacted_self_models,
            "revalidation_candidates": [rc.to_dict() for rc in self.revalidation_candidates],
            "timestamp": self.timestamp,
        }


@dataclass
class ProvenanceGap:
    """Explicit missing upstream provenance relationship."""
    gap_id: str
    affected_node_id: str
    missing_relationship: str
    expected_node_type: str
    reason: str
    severity: ImpactSeverity = ImpactSeverity.POSSIBLE
    recoverable: bool = True
    acquisition_method: Optional[str] = None
    confidence: float = 0.5
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gap_id": self.gap_id,
            "affected_node_id": self.affected_node_id,
            "missing_relationship": self.missing_relationship,
            "expected_node_type": self.expected_node_type,
            "reason": self.reason,
            "severity": self.severity.value if hasattr(self.severity, "value") else str(self.severity),
            "recoverable": self.recoverable,
            "acquisition_method": self.acquisition_method,
            "confidence": self.confidence,
            "created_at": self.created_at,
        }


@dataclass
class SourceConcentrationFinding:
    """Detection of evidence concentration / shared origin."""
    target_node_id: str
    origin_count: int
    dependency_depth: int
    independent_source_estimate: int
    shared_origin_groups: Dict[str, List[str]] = field(default_factory=dict)
    is_high_concentration: bool = False
    details: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_node_id": self.target_node_id,
            "origin_count": self.origin_count,
            "dependency_depth": self.dependency_depth,
            "independent_source_estimate": self.independent_source_estimate,
            "shared_origin_groups": self.shared_origin_groups,
            "is_high_concentration": self.is_high_concentration,
            "details": self.details,
        }


@dataclass
class EvidenceFragilityAssessment:
    """Multi-dimensional evidence fragility assessment."""
    node_id: str
    source_concentration_score: float = 0.0
    provenance_completeness_score: float = 1.0
    freshness_score: float = 1.0
    reproducibility_score: float = 1.0
    dependency_depth: int = 1
    contradiction_exposure_score: float = 0.0
    single_source_dependence: bool = False
    transformation_count: int = 0
    unresolved_gaps_count: int = 0
    dimension_findings: Dict[str, Any] = field(default_factory=dict)
    overall_fragility_label: str = "LOW"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "source_concentration_score": self.source_concentration_score,
            "provenance_completeness_score": self.provenance_completeness_score,
            "freshness_score": self.freshness_score,
            "reproducibility_score": self.reproducibility_score,
            "dependency_depth": self.dependency_depth,
            "contradiction_exposure_score": self.contradiction_exposure_score,
            "single_source_dependence": self.single_source_dependence,
            "transformation_count": self.transformation_count,
            "unresolved_gaps_count": self.unresolved_gaps_count,
            "dimension_findings": dict(self.dimension_findings),
            "overall_fragility_label": self.overall_fragility_label,
            "created_at": self.created_at,
        }


@dataclass
class EvidenceGraphSnapshot:
    """Immutable point-in-time snapshot of graph projection."""
    snapshot_id: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    graph_version: int = 1
    node_count: int = 0
    edge_count: int = 0
    query_scope: Dict[str, Any] = field(default_factory=dict)
    filters: Dict[str, Any] = field(default_factory=dict)
    checksum: str = ""
    creation_reason: str = "AUDIT_SNAPSHOT"
    nodes: List[Dict[str, Any]] = field(default_factory=list)
    edges: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        if not self.checksum:
            content = f"{self.snapshot_id}:{self.timestamp}:{self.node_count}:{self.edge_count}"
            self.checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp,
            "graph_version": self.graph_version,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "query_scope": dict(self.query_scope),
            "filters": dict(self.filters),
            "checksum": self.checksum,
            "creation_reason": self.creation_reason,
            "nodes": self.nodes,
            "edges": self.edges,
        }


@dataclass
class GraphDiff:
    """Structured diff between two graph states or snapshots."""
    base_ref: str
    target_ref: str
    added_nodes: List[Dict[str, Any]] = field(default_factory=list)
    removed_nodes: List[Dict[str, Any]] = field(default_factory=list)
    changed_nodes: List[Dict[str, Any]] = field(default_factory=list)
    added_edges: List[Dict[str, Any]] = field(default_factory=list)
    removed_edges: List[Dict[str, Any]] = field(default_factory=list)
    changed_edges: List[Dict[str, Any]] = field(default_factory=list)
    invalidated_nodes: List[Dict[str, Any]] = field(default_factory=list)
    stale_nodes: List[Dict[str, Any]] = field(default_factory=list)
    superseded_nodes: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_ref": self.base_ref,
            "target_ref": self.target_ref,
            "added_nodes": self.added_nodes,
            "removed_nodes": self.removed_nodes,
            "changed_nodes": self.changed_nodes,
            "added_edges": self.added_edges,
            "removed_edges": self.removed_edges,
            "changed_edges": self.changed_edges,
            "invalidated_nodes": self.invalidated_nodes,
            "stale_nodes": self.stale_nodes,
            "superseded_nodes": self.superseded_nodes,
            "timestamp": self.timestamp,
        }


@dataclass
class GraphHealthAssessment:
    """Health metrics and operational consistency of the evidence graph."""
    provenance_completeness_rate: float = 1.0
    orphan_rate: float = 0.0
    duplicate_rate: float = 0.0
    stale_edge_rate: float = 0.0
    reconciliation_lag_seconds: float = 0.0
    cycle_rate: float = 0.0
    unresolved_gap_rate: float = 0.0
    query_failure_rate: float = 0.0
    snapshot_consistency_ok: bool = True
    sync_state: GraphSyncState = GraphSyncState.GRAPH_CURRENT
    component_health: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provenance_completeness_rate": self.provenance_completeness_rate,
            "orphan_rate": self.orphan_rate,
            "duplicate_rate": self.duplicate_rate,
            "stale_edge_rate": self.stale_edge_rate,
            "reconciliation_lag_seconds": self.reconciliation_lag_seconds,
            "cycle_rate": self.cycle_rate,
            "unresolved_gap_rate": self.unresolved_gap_rate,
            "query_failure_rate": self.query_failure_rate,
            "snapshot_consistency_ok": self.snapshot_consistency_ok,
            "sync_state": self.sync_state.value if hasattr(self.sync_state, "value") else str(self.sync_state),
            "component_health": dict(self.component_health),
            "created_at": self.created_at,
        }
