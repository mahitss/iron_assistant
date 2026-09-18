"""Domain models, enums, and data structures for Task 116:
Kairo Autonomous Claim Verification, Source Integrity, Evidence Provenance & Verification-Lineage Engine.

Core Architectural Invariant:
SOURCE != DOCUMENT != OBSERVATION != EXTRACTED EVIDENCE != CLAIM != INTERPRETATION != INFERENCE != VERIFICATION != BELIEF != TRUTH != AUTHORIZATION.
A claim may remain: VERIFIED_UNDER_SCOPE, PARTIALLY_VERIFIED, SUPPORTED, CONTRADICTED, INCONCLUSIVE, UNVERIFIABLE, STALE, EXPIRED, SOURCE_UNTRUSTED, EVIDENCE_INSUFFICIENT, or UNKNOWN.
Never fabricate certainty.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any, Dict, List, Optional
import uuid


class VerificationCaseStatus(str, Enum):
    REQUESTED = "REQUESTED"
    QUEUED = "QUEUED"
    SCOPED = "SCOPED"
    CLAIM_PARSED = "CLAIM_PARSED"
    EVIDENCE_DISCOVERING = "EVIDENCE_DISCOVERING"
    EVIDENCE_COLLECTED = "EVIDENCE_COLLECTED"
    PROVENANCE_ANALYZING = "PROVENANCE_ANALYZING"
    INTEGRITY_CHECKING = "INTEGRITY_CHECKING"
    CORROBORATING = "CORROBORATING"
    CONTRADICTION_CHECKING = "CONTRADICTION_CHECKING"
    REPRODUCING = "REPRODUCING"
    VERIFYING = "VERIFYING"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    SUPPORTED = "SUPPORTED"
    VERIFIED_UNDER_SCOPE = "VERIFIED_UNDER_SCOPE"
    CONTRADICTED = "CONTRADICTED"
    INCONCLUSIVE = "INCONCLUSIVE"
    UNVERIFIABLE = "UNVERIFIABLE"
    STALE = "STALE"
    EXPIRED = "EXPIRED"
    REVALIDATION_REQUIRED = "REVALIDATION_REQUIRED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SUPERSEDED = "SUPERSEDED"
    UNKNOWN = "UNKNOWN"


class ClaimType(str, Enum):
    ATOMIC = "ATOMIC"
    COMPOSITE = "COMPOSITE"
    DEPENDENT = "DEPENDENT"
    PREREQUISITE = "PREREQUISITE"
    CAUSAL = "CAUSAL"
    QUANTITATIVE = "QUANTITATIVE"
    TEMPORAL = "TEMPORAL"
    RELATIONAL = "RELATIONAL"


class SourceCategory(str, Enum):
    USER_INPUT = "USER_INPUT"
    USER_FILE = "USER_FILE"
    LOCAL_DATABASE = "LOCAL_DATABASE"
    INTERNAL_SYSTEM = "INTERNAL_SYSTEM"
    TOOL_OUTPUT = "TOOL_OUTPUT"
    AGENT_OUTPUT = "AGENT_OUTPUT"
    MEMORY = "MEMORY"
    KNOWLEDGE_GRAPH = "KNOWLEDGE_GRAPH"
    WORLD_STATE = "WORLD_STATE"
    TELEMETRY = "TELEMETRY"
    WEB_PAGE = "WEB_PAGE"
    API = "API"
    DOCUMENT = "DOCUMENT"
    CODE_REPOSITORY = "CODE_REPOSITORY"
    LOG = "LOG"
    SCREEN_OBSERVATION = "SCREEN_OBSERVATION"
    SIMULATION = "SIMULATION"
    EXPERIMENT = "EXPERIMENT"
    EXTERNAL_DATASET = "EXTERNAL_DATASET"
    GENERATED_CONTENT = "GENERATED_CONTENT"
    UNKNOWN = "UNKNOWN"


class SourceRelationshipType(str, Enum):
    DIRECT_COPY = "DIRECT_COPY"
    CITATION = "CITATION"
    DERIVATION = "DERIVATION"
    COMMON_ORIGIN = "COMMON_ORIGIN"
    SHARED_DATASET = "SHARED_DATASET"
    SHARED_OBSERVATION = "SHARED_OBSERVATION"
    UNKNOWN_DEPENDENCY = "UNKNOWN_DEPENDENCY"
    INDEPENDENT = "INDEPENDENT"
    POSSIBLY_DEPENDENT = "POSSIBLY_DEPENDENT"


class ProvenancePredicate(str, Enum):
    DERIVED_FROM = "DERIVED_FROM"
    EXTRACTED_FROM = "EXTRACTED_FROM"
    TRANSFORMED_FROM = "TRANSFORMED_FROM"
    COPIED_FROM = "COPIED_FROM"
    SUMMARIZED_FROM = "SUMMARIZED_FROM"
    GENERATED_FROM = "GENERATED_FROM"
    OBSERVED_FROM = "OBSERVED_FROM"
    REPORTED_BY = "REPORTED_BY"
    VERIFIED_BY = "VERIFIED_BY"
    CORROBORATED_BY = "CORROBORATED_BY"
    CONTRADICTED_BY = "CONTRADICTED_BY"
    SUPERSEDES = "SUPERSEDES"
    SUPERSEDED_BY = "SUPERSEDED_BY"
    DEPENDS_ON = "DEPENDS_ON"
    SUPPORTED_BY = "SUPPORTED_BY"
    INVALIDATED_BY = "INVALIDATED_BY"


class CorroborationType(str, Enum):
    INDEPENDENT_SUPPORT = "INDEPENDENT_SUPPORT"
    DEPENDENT_SUPPORT = "DEPENDENT_SUPPORT"
    PARTIAL_SUPPORT = "PARTIAL_SUPPORT"
    SUPERFICIAL_MATCH = "SUPERFICIAL_MATCH"
    SEMANTIC_MISMATCH = "SEMANTIC_MISMATCH"
    TEMPORAL_MISMATCH = "TEMPORAL_MISMATCH"
    SCOPE_MISMATCH = "SCOPE_MISMATCH"
    UNKNOWN_INDEPENDENCE = "UNKNOWN_INDEPENDENCE"


class ContradictionType(str, Enum):
    DIRECT_CONTRADICTION = "DIRECT_CONTRADICTION"
    NUMERIC_CONTRADICTION = "NUMERIC_CONTRADICTION"
    TEMPORAL_CONTRADICTION = "TEMPORAL_CONTRADICTION"
    SCOPE_CONTRADICTION = "SCOPE_CONTRADICTION"
    ENTITY_CONTRADICTION = "ENTITY_CONTRADICTION"
    CAUSAL_CONTRADICTION = "CAUSAL_CONTRADICTION"
    VERSION_CONTRADICTION = "VERSION_CONTRADICTION"
    STATE_CONTRADICTION = "STATE_CONTRADICTION"


class VerificationMethodType(str, Enum):
    SOURCE_RETRIEVAL = "SOURCE_RETRIEVAL"
    HASH_COMPARISON = "HASH_COMPARISON"
    CROSS_SOURCE_COMPARISON = "CROSS_SOURCE_COMPARISON"
    DOCUMENT_REPRODUCTION = "DOCUMENT_REPRODUCTION"
    API_REQUERY = "API_REQUERY"
    DATABASE_REQUERY = "DATABASE_REQUERY"
    LOG_CORRELATION = "LOG_CORRELATION"
    TELEMETRY_CORRELATION = "TELEMETRY_CORRELATION"
    TEMPORAL_RECONSTRUCTION = "TEMPORAL_RECONSTRUCTION"
    WORLD_STATE_RECONCILIATION = "WORLD_STATE_RECONCILIATION"
    KNOWLEDGE_GRAPH_CHECK = "KNOWLEDGE_GRAPH_CHECK"
    EXPERIMENT_REPLAY = "EXPERIMENT_REPLAY"
    SIMULATION_CHECK = "SIMULATION_CHECK"
    CODE_REPRODUCTION = "CODE_REPRODUCTION"
    USER_CONFIRMATION = "USER_CONFIRMATION"
    TOOL_REEXECUTION = "TOOL_REEXECUTION"
    STRUCTURED_CONSISTENCY_CHECK = "STRUCTURED_CONSISTENCY_CHECK"
    HYPOTHESIS_DISCRIMINATION = "HYPOTHESIS_DISCRIMINATION"


class ReproducibilityStatus(str, Enum):
    REPRODUCIBLE = "REPRODUCIBLE"
    PARTIALLY_REPRODUCIBLE = "PARTIALLY_REPRODUCIBLE"
    NON_REPRODUCIBLE = "NON_REPRODUCIBLE"
    NOT_ATTEMPTED = "NOT_ATTEMPTED"
    FAILED_REPRODUCTION = "FAILED_REPRODUCTION"


class NegativeEvidenceType(str, Enum):
    OBSERVED_ABSENCE = "OBSERVED_ABSENCE"
    SEARCHED_ABSENCE = "SEARCHED_ABSENCE"
    INSUFFICIENT_COVERAGE = "INSUFFICIENT_COVERAGE"
    UNKNOWN = "UNKNOWN"


@dataclass
class SourceTrustProfile:
    """12-dimension structured trust profile (Section 13). No single opaque score."""
    identity_confidence: float = 0.8
    provenance_quality: float = 0.8
    integrity_confidence: float = 0.85
    historical_consistency: float = 0.8
    correction_behavior: float = 0.7
    reproducibility: float = 0.8
    independence: float = 0.8
    domain_relevance: float = 0.9
    freshness: float = 1.0
    authentication: float = 0.8
    transparency: float = 0.8
    conflict_history: float = 0.1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "identity_confidence": self.identity_confidence,
            "provenance_quality": self.provenance_quality,
            "integrity_confidence": self.integrity_confidence,
            "historical_consistency": self.historical_consistency,
            "correction_behavior": self.correction_behavior,
            "reproducibility": self.reproducibility,
            "independence": self.independence,
            "domain_relevance": self.domain_relevance,
            "freshness": self.freshness,
            "authentication": self.authentication,
            "transparency": self.transparency,
            "conflict_history": self.conflict_history,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SourceTrustProfile:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class EvidenceQualityProfile:
    """13-dimension evidence assessment dimensions (Section 14)."""
    directness: str = "DIRECT"
    relevance: float = 0.9
    specificity: float = 0.85
    freshness: float = 1.0
    completeness: float = 0.8
    provenance_quality: float = 0.85
    integrity: float = 1.0
    reproducibility: float = 0.85
    independence: float = 0.8
    consistency: float = 0.9
    scope_match: float = 0.95
    temporal_match: float = 0.95
    entity_match: float = 0.95

    def to_dict(self) -> Dict[str, Any]:
        return {
            "directness": self.directness,
            "relevance": self.relevance,
            "specificity": self.specificity,
            "freshness": self.freshness,
            "completeness": self.completeness,
            "provenance_quality": self.provenance_quality,
            "integrity": self.integrity,
            "reproducibility": self.reproducibility,
            "independence": self.independence,
            "consistency": self.consistency,
            "scope_match": self.scope_match,
            "temporal_match": self.temporal_match,
            "entity_match": self.entity_match,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EvidenceQualityProfile:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ClaimFragment:
    """Atomic, causal, or temporal fragment decomposed from a statement (Section 4)."""
    fragment_id: str
    claim_id: str
    fragment_type: ClaimType
    statement: str
    subject: str = ""
    predicate: str = ""
    object_val: str = ""
    dependencies: List[str] = field(default_factory=list)
    order_idx: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fragment_id": self.fragment_id,
            "claim_id": self.claim_id,
            "fragment_type": self.fragment_type.value,
            "statement": self.statement,
            "subject": self.subject,
            "predicate": self.predicate,
            "object_val": self.object_val,
            "dependencies": self.dependencies,
            "order_idx": self.order_idx,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ClaimFragment:
        ft = ClaimType(data.get("fragment_type", "ATOMIC"))
        dt = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(timezone.utc)
        return cls(
            fragment_id=data["fragment_id"],
            claim_id=data["claim_id"],
            fragment_type=ft,
            statement=data["statement"],
            subject=data.get("subject", ""),
            predicate=data.get("predicate", ""),
            object_val=data.get("object_val", ""),
            dependencies=data.get("dependencies", []),
            order_idx=data.get("order_idx", 0),
            created_at=dt,
        )


@dataclass
class Claim:
    """Structured representation of a claim (Section 3)."""
    claim_id: str
    version: int
    canonical_text: str
    normalized_text: str
    claim_type: ClaimType
    subject: str = ""
    predicate: str = ""
    object_val: str = ""
    qualifiers: Dict[str, Any] = field(default_factory=dict)
    temporal_scope: Dict[str, Any] = field(default_factory=dict)
    spatial_scope: Dict[str, Any] = field(default_factory=dict)
    entity_scope: List[str] = field(default_factory=list)
    source_scope: Dict[str, Any] = field(default_factory=dict)
    conditions: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    expected_evidence_types: List[str] = field(default_factory=list)
    falsification_conditions: List[str] = field(default_factory=list)
    verification_requirements: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    confidence: float = 0.5
    uncertainty: float = 0.5
    provenance_id: Optional[str] = None
    fragments: List[ClaimFragment] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "version": self.version,
            "canonical_text": self.canonical_text,
            "normalized_text": self.normalized_text,
            "claim_type": self.claim_type.value,
            "subject": self.subject,
            "predicate": self.predicate,
            "object_val": self.object_val,
            "qualifiers": self.qualifiers,
            "temporal_scope": self.temporal_scope,
            "spatial_scope": self.spatial_scope,
            "entity_scope": self.entity_scope,
            "source_scope": self.source_scope,
            "conditions": self.conditions,
            "assumptions": self.assumptions,
            "expected_evidence_types": self.expected_evidence_types,
            "falsification_conditions": self.falsification_conditions,
            "verification_requirements": self.verification_requirements,
            "dependencies": self.dependencies,
            "confidence": self.confidence,
            "uncertainty": self.uncertainty,
            "provenance_id": self.provenance_id,
            "fragments": [f.to_dict() for f in self.fragments],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Claim:
        ct = ClaimType(data.get("claim_type", "ATOMIC"))
        frags = [ClaimFragment.from_dict(f) for f in data.get("fragments", [])]
        ca = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(timezone.utc)
        ua = datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(timezone.utc)
        return cls(
            claim_id=data["claim_id"],
            version=data.get("version", 1),
            canonical_text=data["canonical_text"],
            normalized_text=data["normalized_text"],
            claim_type=ct,
            subject=data.get("subject", ""),
            predicate=data.get("predicate", ""),
            object_val=data.get("object_val", ""),
            qualifiers=data.get("qualifiers", {}),
            temporal_scope=data.get("temporal_scope", {}),
            spatial_scope=data.get("spatial_scope", {}),
            entity_scope=data.get("entity_scope", []),
            source_scope=data.get("source_scope", {}),
            conditions=data.get("conditions", []),
            assumptions=data.get("assumptions", []),
            expected_evidence_types=data.get("expected_evidence_types", []),
            falsification_conditions=data.get("falsification_conditions", []),
            verification_requirements=data.get("verification_requirements", []),
            dependencies=data.get("dependencies", []),
            confidence=data.get("confidence", 0.5),
            uncertainty=data.get("uncertainty", 0.5),
            provenance_id=data.get("provenance_id"),
            fragments=frags,
            created_at=ca,
            updated_at=ua,
        )


@dataclass
class SourceSnapshot:
    """Point-in-time immutable snapshot of a source (Section 6)."""
    snapshot_id: str
    source_id: str
    content_hash: str
    canonical_source_identifier: str = ""
    retrieval_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    observed_version: int = 1
    headers: Dict[str, str] = field(default_factory=dict)
    content_metadata: Dict[str, Any] = field(default_factory=dict)
    content_preview: str = ""
    parser_version: str = "default_v1"
    transformation_chain: List[str] = field(default_factory=list)
    valid_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "source_id": self.source_id,
            "content_hash": self.content_hash,
            "canonical_source_identifier": self.canonical_source_identifier,
            "retrieval_time": self.retrieval_time.isoformat() if self.retrieval_time else None,
            "observed_version": self.observed_version,
            "headers": self.headers,
            "content_metadata": self.content_metadata,
            "content_preview": self.content_preview,
            "parser_version": self.parser_version,
            "transformation_chain": self.transformation_chain,
            "valid_at": self.valid_at.isoformat() if self.valid_at else None,
            "expired_at": self.expired_at.isoformat() if self.expired_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SourceSnapshot:
        rt = datetime.fromisoformat(data["retrieval_time"]) if data.get("retrieval_time") else datetime.now(timezone.utc)
        va = datetime.fromisoformat(data["valid_at"]) if data.get("valid_at") else None
        ea = datetime.fromisoformat(data["expired_at"]) if data.get("expired_at") else None
        return cls(
            snapshot_id=data["snapshot_id"],
            source_id=data["source_id"],
            content_hash=data["content_hash"],
            canonical_source_identifier=data.get("canonical_source_identifier", ""),
            retrieval_time=rt,
            observed_version=data.get("observed_version", 1),
            headers=data.get("headers", {}),
            content_metadata=data.get("content_metadata", {}),
            content_preview=data.get("content_preview", ""),
            parser_version=data.get("parser_version", "default_v1"),
            transformation_chain=data.get("transformation_chain", []),
            valid_at=va,
            expired_at=ea,
        )


@dataclass
class Source:
    """Explicit source identity and multi-dimensional trust metadata (Section 5)."""
    source_id: str
    version: int
    uri: str
    category: SourceCategory
    origin: str = "internal"
    owner: str = ""
    publisher: str = ""
    retrieval_location: str = ""
    retrieval_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    content_hash: str = ""
    auth_state: str = "UNAUTHENTICATED"
    trust_profile: SourceTrustProfile = field(default_factory=SourceTrustProfile)
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "version": self.version,
            "uri": self.uri,
            "category": self.category.value,
            "origin": self.origin,
            "owner": self.owner,
            "publisher": self.publisher,
            "retrieval_location": self.retrieval_location,
            "retrieval_timestamp": self.retrieval_timestamp.isoformat() if self.retrieval_timestamp else None,
            "content_hash": self.content_hash,
            "auth_state": self.auth_state,
            "trust_profile": self.trust_profile.to_dict(),
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Source:
        cat = SourceCategory(data.get("category", "UNKNOWN"))
        tp = SourceTrustProfile.from_dict(data.get("trust_profile", {}))
        rt = datetime.fromisoformat(data["retrieval_timestamp"]) if data.get("retrieval_timestamp") else datetime.now(timezone.utc)
        ca = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(timezone.utc)
        ua = datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(timezone.utc)
        return cls(
            source_id=data["source_id"],
            version=data.get("version", 1),
            uri=data["uri"],
            category=cat,
            origin=data.get("origin", "internal"),
            owner=data.get("owner", ""),
            publisher=data.get("publisher", ""),
            retrieval_location=data.get("retrieval_location", ""),
            retrieval_timestamp=rt,
            content_hash=data.get("content_hash", ""),
            auth_state=data.get("auth_state", "UNAUTHENTICATED"),
            trust_profile=tp,
            is_active=data.get("is_active", True),
            created_at=ca,
            updated_at=ua,
        )


@dataclass
class SourceRelationship:
    """Relationship between sources (copy, citation, derivation) (Section 11)."""
    relationship_id: str
    source_a_id: str
    source_b_id: str
    relationship_type: SourceRelationshipType
    confidence: float = 0.5
    justification: str = ""
    observed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relationship_id": self.relationship_id,
            "source_a_id": self.source_a_id,
            "source_b_id": self.source_b_id,
            "relationship_type": self.relationship_type.value,
            "confidence": self.confidence,
            "justification": self.justification,
            "observed_at": self.observed_at.isoformat() if self.observed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SourceRelationship:
        rt = SourceRelationshipType(data.get("relationship_type", "INDEPENDENT"))
        oa = datetime.fromisoformat(data["observed_at"]) if data.get("observed_at") else datetime.now(timezone.utc)
        ca = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(timezone.utc)
        return cls(
            relationship_id=data["relationship_id"],
            source_a_id=data["source_a_id"],
            source_b_id=data["source_b_id"],
            relationship_type=rt,
            confidence=data.get("confidence", 0.5),
            justification=data.get("justification", ""),
            observed_at=oa,
            created_at=ca,
        )


@dataclass
class EvidenceArtifact:
    """Evidence artifact with precise lineage and quality dimensions (Section 8)."""
    evidence_id: str
    source_id: str
    snapshot_id: Optional[str] = None
    location: str = ""
    offset_range: str = ""
    extraction_method: str = "DIRECT"
    extractor_version: str = "1.0"
    extraction_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    content_hash: str = ""
    content_text: str = ""
    parent_artifact_id: Optional[str] = None
    transformation_chain: List[str] = field(default_factory=list)
    quality_profile: EvidenceQualityProfile = field(default_factory=EvidenceQualityProfile)
    direct_status: bool = True
    is_synthetic: bool = False
    is_simulated: bool = False
    is_counterfactual: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "source_id": self.source_id,
            "snapshot_id": self.snapshot_id,
            "location": self.location,
            "offset_range": self.offset_range,
            "extraction_method": self.extraction_method,
            "extractor_version": self.extractor_version,
            "extraction_timestamp": self.extraction_timestamp.isoformat() if self.extraction_timestamp else None,
            "content_hash": self.content_hash,
            "content_text": self.content_text,
            "parent_artifact_id": self.parent_artifact_id,
            "transformation_chain": self.transformation_chain,
            "quality_profile": self.quality_profile.to_dict(),
            "direct_status": self.direct_status,
            "is_synthetic": self.is_synthetic,
            "is_simulated": self.is_simulated,
            "is_counterfactual": self.is_counterfactual,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EvidenceArtifact:
        qp = EvidenceQualityProfile.from_dict(data.get("quality_profile", {}))
        et = datetime.fromisoformat(data["extraction_timestamp"]) if data.get("extraction_timestamp") else datetime.now(timezone.utc)
        ca = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(timezone.utc)
        return cls(
            evidence_id=data["evidence_id"],
            source_id=data["source_id"],
            snapshot_id=data.get("snapshot_id"),
            location=data.get("location", ""),
            offset_range=data.get("offset_range", ""),
            extraction_method=data.get("extraction_method", "DIRECT"),
            extractor_version=data.get("extractor_version", "1.0"),
            extraction_timestamp=et,
            content_hash=data.get("content_hash", ""),
            content_text=data.get("content_text", ""),
            parent_artifact_id=data.get("parent_artifact_id"),
            transformation_chain=data.get("transformation_chain", []),
            quality_profile=qp,
            direct_status=data.get("direct_status", True),
            is_synthetic=data.get("is_synthetic", False),
            is_simulated=data.get("is_simulated", False),
            is_counterfactual=data.get("is_counterfactual", False),
            created_at=ca,
        )


@dataclass
class EvidenceTransformation:
    """Audit record for transformation operations applied to evidence (Section 9)."""
    transformation_id: str
    input_artifact_ids: List[str]
    output_artifact_id: str
    operation: str
    component: str
    config_fingerprint: str = ""
    is_deterministic: bool = True
    input_hash: str = ""
    output_hash: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transformation_id": self.transformation_id,
            "input_artifact_ids": self.input_artifact_ids,
            "output_artifact_id": self.output_artifact_id,
            "operation": self.operation,
            "component": self.component,
            "config_fingerprint": self.config_fingerprint,
            "is_deterministic": self.is_deterministic,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EvidenceTransformation:
        ts = datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.now(timezone.utc)
        return cls(
            transformation_id=data["transformation_id"],
            input_artifact_ids=data.get("input_artifact_ids", []),
            output_artifact_id=data["output_artifact_id"],
            operation=data["operation"],
            component=data["component"],
            config_fingerprint=data.get("config_fingerprint", ""),
            is_deterministic=data.get("is_deterministic", True),
            input_hash=data.get("input_hash", ""),
            output_hash=data.get("output_hash", ""),
            timestamp=ts,
        )


@dataclass
class ProvenanceLink:
    """W3C-PROV inspired directed provenance link (Section 10)."""
    link_id: str
    from_entity_type: str
    from_entity_id: str
    to_entity_type: str
    to_entity_id: str
    predicate: ProvenancePredicate = ProvenancePredicate.DERIVED_FROM
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "link_id": self.link_id,
            "from_entity_type": self.from_entity_type,
            "from_entity_id": self.from_entity_id,
            "to_entity_type": self.to_entity_type,
            "to_entity_id": self.to_entity_id,
            "predicate": self.predicate.value,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ProvenanceLink:
        pred = ProvenancePredicate(data.get("predicate", "DERIVED_FROM"))
        ca = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(timezone.utc)
        return cls(
            link_id=data["link_id"],
            from_entity_type=data["from_entity_type"],
            from_entity_id=data["from_entity_id"],
            to_entity_type=data["to_entity_type"],
            to_entity_id=data["to_entity_id"],
            predicate=pred,
            metadata=data.get("metadata", {}),
            created_at=ca,
        )


@dataclass
class IndependenceAssessment:
    """Assessment of source independence vs copy/citation chains (Section 11)."""
    source_ids: List[str]
    is_independent: bool
    independence_score: float
    detected_relationships: List[str] = field(default_factory=list)
    dependency_chains: List[str] = field(default_factory=list)
    cycles: List[List[str]] = field(default_factory=list)
    justification: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_ids": self.source_ids,
            "is_independent": self.is_independent,
            "independence_score": self.independence_score,
            "detected_relationships": self.detected_relationships,
            "dependency_chains": self.dependency_chains,
            "cycles": self.cycles,
            "justification": self.justification,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> IndependenceAssessment:
        return cls(
            source_ids=data.get("source_ids", []),
            is_independent=data.get("is_independent", True),
            independence_score=data.get("independence_score", 1.0),
            detected_relationships=data.get("detected_relationships", []),
            dependency_chains=data.get("dependency_chains", []),
            cycles=data.get("cycles", []),
            justification=data.get("justification", ""),
        )


@dataclass
class CorroborationGroup:
    """Group of evidence corroborating a claim (Section 12)."""
    group_id: str
    case_id: str
    claim_id: str
    corroboration_type: CorroborationType
    evidence_ids: List[str] = field(default_factory=list)
    source_ids: List[str] = field(default_factory=list)
    temporal_alignment: float = 1.0
    semantic_alignment: float = 1.0
    scope_alignment: float = 1.0
    independence_assessment: IndependenceAssessment = field(default_factory=lambda: IndependenceAssessment([], True, 1.0))
    summary: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "group_id": self.group_id,
            "case_id": self.case_id,
            "claim_id": self.claim_id,
            "corroboration_type": self.corroboration_type.value,
            "evidence_ids": self.evidence_ids,
            "source_ids": self.source_ids,
            "temporal_alignment": self.temporal_alignment,
            "semantic_alignment": self.semantic_alignment,
            "scope_alignment": self.scope_alignment,
            "independence_assessment": self.independence_assessment.to_dict(),
            "summary": self.summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CorroborationGroup:
        ct = CorroborationType(data.get("corroboration_type", "INDEPENDENT_SUPPORT"))
        ia = IndependenceAssessment.from_dict(data.get("independence_assessment", {}))
        ca = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(timezone.utc)
        return cls(
            group_id=data["group_id"],
            case_id=data["case_id"],
            claim_id=data["claim_id"],
            corroboration_type=ct,
            evidence_ids=data.get("evidence_ids", []),
            source_ids=data.get("source_ids", []),
            temporal_alignment=data.get("temporal_alignment", 1.0),
            semantic_alignment=data.get("semantic_alignment", 1.0),
            scope_alignment=data.get("scope_alignment", 1.0),
            independence_assessment=ia,
            summary=data.get("summary", ""),
            created_at=ca,
        )


@dataclass
class ContradictionRecord:
    """Documented contradiction between claims or evidence (Section 19)."""
    contradiction_id: str
    case_id: str
    contradiction_type: ContradictionType
    claim_a_id: str
    claim_b_id: Optional[str] = None
    evidence_a_id: str = ""
    evidence_b_id: str = ""
    description: str = ""
    severity: float = 1.0
    status: str = "OPEN"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contradiction_id": self.contradiction_id,
            "case_id": self.case_id,
            "contradiction_type": self.contradiction_type.value,
            "claim_a_id": self.claim_a_id,
            "claim_b_id": self.claim_b_id,
            "evidence_a_id": self.evidence_a_id,
            "evidence_b_id": self.evidence_b_id,
            "description": self.description,
            "severity": self.severity,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ContradictionRecord:
        ct = ContradictionType(data.get("contradiction_type", "DIRECT_CONTRADICTION"))
        ca = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(timezone.utc)
        return cls(
            contradiction_id=data["contradiction_id"],
            case_id=data["case_id"],
            contradiction_type=ct,
            claim_a_id=data["claim_a_id"],
            claim_b_id=data.get("claim_b_id"),
            evidence_a_id=data.get("evidence_a_id", ""),
            evidence_b_id=data.get("evidence_b_id", ""),
            description=data.get("description", ""),
            severity=data.get("severity", 1.0),
            status=data.get("status", "OPEN"),
            created_at=ca,
        )


@dataclass
class ReproductionAttempt:
    """Audit record for reproduction attempts (Section 30)."""
    attempt_id: str
    case_id: str
    method: str
    status: ReproducibilityStatus
    environment_fingerprint: str = ""
    input_hash: str = ""
    output_hash: str = ""
    deterministic: bool = True
    seed: Optional[int] = None
    notes: str = ""
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attempt_id": self.attempt_id,
            "case_id": self.case_id,
            "method": self.method,
            "status": self.status.value,
            "environment_fingerprint": self.environment_fingerprint,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "deterministic": self.deterministic,
            "seed": self.seed,
            "notes": self.notes,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ReproductionAttempt:
        st = ReproducibilityStatus(data.get("status", "NOT_ATTEMPTED"))
        ea = datetime.fromisoformat(data["executed_at"]) if data.get("executed_at") else datetime.now(timezone.utc)
        return cls(
            attempt_id=data["attempt_id"],
            case_id=data["case_id"],
            method=data["method"],
            status=st,
            environment_fingerprint=data.get("environment_fingerprint", ""),
            input_hash=data.get("input_hash", ""),
            output_hash=data.get("output_hash", ""),
            deterministic=data.get("deterministic", True),
            seed=data.get("seed"),
            notes=data.get("notes", ""),
            executed_at=ea,
        )


@dataclass
class IntegrityCheck:
    """Cryptographic hash check result (Section 7)."""
    check_id: str
    target_type: str
    target_id: str
    expected_hash: str
    computed_hash: str
    passed: bool
    diff_summary: str = ""
    tamper_indicators: List[str] = field(default_factory=list)
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_id": self.check_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "expected_hash": self.expected_hash,
            "computed_hash": self.computed_hash,
            "passed": self.passed,
            "diff_summary": self.diff_summary,
            "tamper_indicators": self.tamper_indicators,
            "checked_at": self.checked_at.isoformat() if self.checked_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> IntegrityCheck:
        ca = datetime.fromisoformat(data["checked_at"]) if data.get("checked_at") else datetime.now(timezone.utc)
        return cls(
            check_id=data["check_id"],
            target_type=data["target_type"],
            target_id=data["target_id"],
            expected_hash=data["expected_hash"],
            computed_hash=data["computed_hash"],
            passed=data["passed"],
            diff_summary=data.get("diff_summary", ""),
            tamper_indicators=data.get("tamper_indicators", []),
            checked_at=ca,
        )


@dataclass
class VerificationMethod:
    """Pluggable verification method descriptor (Section 15)."""
    method_type: VerificationMethodType
    required_inputs: List[str] = field(default_factory=list)
    cost: float = 0.1
    latency_ms: float = 50.0
    risk: float = 0.05
    is_read_only: bool = True
    requires_approval: bool = False
    has_side_effects: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method_type": self.method_type.value,
            "required_inputs": self.required_inputs,
            "cost": self.cost,
            "latency_ms": self.latency_ms,
            "risk": self.risk,
            "is_read_only": self.is_read_only,
            "requires_approval": self.requires_approval,
            "has_side_effects": self.has_side_effects,
        }


@dataclass
class VerificationResult:
    """Authoritative structured verification result (Section 17)."""
    result_id: str
    case_id: str
    claim_id: str
    status: VerificationCaseStatus
    scope: Dict[str, Any] = field(default_factory=dict)
    justification: str = ""
    evidence_ids: List[str] = field(default_factory=list)
    contradiction_ids: List[str] = field(default_factory=list)
    method_types: List[str] = field(default_factory=list)
    uncertainty_profile: Dict[str, Any] = field(default_factory=dict)
    gaps: List[str] = field(default_factory=list)
    reproducibility_status: ReproducibilityStatus = ReproducibilityStatus.NOT_ATTEMPTED
    validity_window_start: Optional[datetime] = None
    validity_window_end: Optional[datetime] = None
    verified_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "case_id": self.case_id,
            "claim_id": self.claim_id,
            "status": self.status.value,
            "scope": self.scope,
            "justification": self.justification,
            "evidence_ids": self.evidence_ids,
            "contradiction_ids": self.contradiction_ids,
            "method_types": self.method_types,
            "uncertainty_profile": self.uncertainty_profile,
            "gaps": self.gaps,
            "reproducibility_status": self.reproducibility_status.value,
            "validity_window_start": self.validity_window_start.isoformat() if self.validity_window_start else None,
            "validity_window_end": self.validity_window_end.isoformat() if self.validity_window_end else None,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> VerificationResult:
        st = VerificationCaseStatus(data.get("status", "UNKNOWN"))
        rs = ReproducibilityStatus(data.get("reproducibility_status", "NOT_ATTEMPTED"))
        vws = datetime.fromisoformat(data["validity_window_start"]) if data.get("validity_window_start") else None
        vwe = datetime.fromisoformat(data["validity_window_end"]) if data.get("validity_window_end") else None
        va = datetime.fromisoformat(data["verified_at"]) if data.get("verified_at") else datetime.now(timezone.utc)
        ea = datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None
        return cls(
            result_id=data["result_id"],
            case_id=data["case_id"],
            claim_id=data["claim_id"],
            status=st,
            scope=data.get("scope", {}),
            justification=data.get("justification", ""),
            evidence_ids=data.get("evidence_ids", []),
            contradiction_ids=data.get("contradiction_ids", []),
            method_types=data.get("method_types", []),
            uncertainty_profile=data.get("uncertainty_profile", {}),
            gaps=data.get("gaps", []),
            reproducibility_status=rs,
            validity_window_start=vws,
            validity_window_end=vwe,
            verified_at=va,
            expires_at=ea,
        )


@dataclass
class VerificationGap:
    """Missing evidence requirement or unresolved information gap (Section 33)."""
    gap_id: str
    case_id: str
    missing_evidence_desc: str
    impact_reason: str
    affected_claim_id: str
    possible_methods: List[str] = field(default_factory=list)
    expected_info_gain: float = 0.5
    cost: float = 0.1
    risk: float = 0.1
    urgency: float = 0.5
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gap_id": self.gap_id,
            "case_id": self.case_id,
            "missing_evidence_desc": self.missing_evidence_desc,
            "impact_reason": self.impact_reason,
            "affected_claim_id": self.affected_claim_id,
            "possible_methods": self.possible_methods,
            "expected_info_gain": self.expected_info_gain,
            "cost": self.cost,
            "risk": self.risk,
            "urgency": self.urgency,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> VerificationGap:
        ca = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(timezone.utc)
        return cls(
            gap_id=data["gap_id"],
            case_id=data["case_id"],
            missing_evidence_desc=data["missing_evidence_desc"],
            impact_reason=data["impact_reason"],
            affected_claim_id=data["affected_claim_id"],
            possible_methods=data.get("possible_methods", []),
            expected_info_gain=data.get("expected_info_gain", 0.5),
            cost=data.get("cost", 0.1),
            risk=data.get("risk", 0.1),
            urgency=data.get("urgency", 0.5),
            created_at=ca,
        )


@dataclass
class VerificationCase:
    """Primary state machine entity tracking verification cases (Section 2)."""
    case_id: str
    version: int
    title: str
    claim_id: str
    status: VerificationCaseStatus
    scope: Dict[str, Any] = field(default_factory=dict)
    assumptions: List[str] = field(default_factory=list)
    falsification_conditions: List[str] = field(default_factory=list)
    verification_requirements: List[str] = field(default_factory=list)
    resolution_summary: str = ""
    idempotency_key: Optional[str] = None
    correlation_id: Optional[str] = None
    superseded_by_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "version": self.version,
            "title": self.title,
            "claim_id": self.claim_id,
            "status": self.status.value,
            "scope": self.scope,
            "assumptions": self.assumptions,
            "falsification_conditions": self.falsification_conditions,
            "verification_requirements": self.verification_requirements,
            "resolution_summary": self.resolution_summary,
            "idempotency_key": self.idempotency_key,
            "correlation_id": self.correlation_id,
            "superseded_by_id": self.superseded_by_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> VerificationCase:
        st = VerificationCaseStatus(data.get("status", "REQUESTED"))
        ca = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(timezone.utc)
        ua = datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(timezone.utc)
        return cls(
            case_id=data["case_id"],
            version=data.get("version", 1),
            title=data.get("title", ""),
            claim_id=data["claim_id"],
            status=st,
            scope=data.get("scope", {}),
            assumptions=data.get("assumptions", []),
            falsification_conditions=data.get("falsification_conditions", []),
            verification_requirements=data.get("verification_requirements", []),
            resolution_summary=data.get("resolution_summary", ""),
            idempotency_key=data.get("idempotency_key"),
            correlation_id=data.get("correlation_id"),
            superseded_by_id=data.get("superseded_by_id"),
            created_at=ca,
            updated_at=ua,
        )


@dataclass
class VerificationSnapshot:
    """Immutable point-in-time state snapshot (Section 1)."""
    snapshot_id: str
    case_id: str
    snapshot_version: int
    case_state: Dict[str, Any]
    summary: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "case_id": self.case_id,
            "snapshot_version": self.snapshot_version,
            "case_state": self.case_state,
            "summary": self.summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class VerificationEvent:
    """Append-only verification event for auditability (Section 37)."""
    event_id: str
    case_id: str
    event_type: str
    actor: str = "system"
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "case_id": self.case_id,
            "event_type": self.event_type,
            "actor": self.actor,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
