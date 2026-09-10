"""Pydantic v2 schemas and domain models for Knowledge Synthesis & Research Intelligence Engine (Task 63)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# --- Enums ---


class ResearchMode(str, Enum):
    QUICK = "QUICK"
    STANDARD = "STANDARD"
    DEEP = "DEEP"
    COMPREHENSIVE = "COMPREHENSIVE"
    CONTINUOUS = "CONTINUOUS"


class SourceType(str, Enum):
    OFFICIAL_DOCUMENTATION = "OFFICIAL_DOCUMENTATION"
    ACADEMIC_PAPER = "ACADEMIC_PAPER"
    GOVERNMENT_PUBLICATION = "GOVERNMENT_PUBLICATION"
    TECHNICAL_REPORT = "TECHNICAL_REPORT"
    DATASET = "DATASET"
    BOOK = "BOOK"
    NEWS = "NEWS"
    COMPANY_DOCUMENTATION = "COMPANY_DOCUMENTATION"
    REPOSITORY = "REPOSITORY"
    FORUM = "FORUM"
    USER_DOCUMENT = "USER_DOCUMENT"
    WEB_PAGE = "WEB_PAGE"
    DATABASE = "DATABASE"
    API = "API"
    INTERNAL_SYSTEM = "INTERNAL_SYSTEM"
    STRUCTURED_API_DATA = "STRUCTURED_API_DATA"


class SourceTrustLevel(str, Enum):
    VERY_HIGH = "VERY_HIGH"
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"
    VERY_LOW = "VERY_LOW"
    PRIMARY_VERIFIED = "PRIMARY_VERIFIED"
    PEER_REVIEWED = "PEER_REVIEWED"
    REPUTABLE_SECONDARY = "REPUTABLE_SECONDARY"
    PRACTITIONER = "PRACTITIONER"
    COMMUNITY = "COMMUNITY"
    UNVERIFIED = "UNVERIFIED"


class ClaimType(str, Enum):
    OBSERVED = "OBSERVED"
    REPORTED = "REPORTED"
    MEASURED = "MEASURED"
    INFERRED = "INFERRED"
    CAUSAL = "CAUSAL"
    PREDICTED = "PREDICTED"
    HYPOTHETICAL = "HYPOTHETICAL"
    NORMATIVE = "NORMATIVE"
    OPINION = "OPINION"


class EvidenceType(str, Enum):
    MEASUREMENT = "MEASUREMENT"
    EXPERIMENT = "EXPERIMENT"
    OBSERVATION = "OBSERVATION"
    DATASET = "DATASET"
    CITATION = "CITATION"
    EXPERT_ASSESSMENT = "EXPERT_ASSESSMENT"
    DOCUMENT_STATEMENT = "DOCUMENT_STATEMENT"
    SYSTEM_TELEMETRY = "SYSTEM_TELEMETRY"
    VERIFIED_OUTCOME = "VERIFIED_OUTCOME"
    DIRECT_MEASUREMENT = "DIRECT_MEASUREMENT"
    CONTROLLED_EXPERIMENT = "CONTROLLED_EXPERIMENT"
    REPRODUCED_RESULT = "REPRODUCED_RESULT"
    PRIMARY_DOCUMENT = "PRIMARY_DOCUMENT"
    SECONDARY_REPORT = "SECONDARY_REPORT"
    EXPERT_OPINION = "EXPERT_OPINION"
    MODEL_INFERENCE = "MODEL_INFERENCE"
    UNVERIFIED_ASSERTION = "UNVERIFIED_ASSERTION"


class EvidenceStrength(str, Enum):
    DIRECT_MEASUREMENT = "DIRECT_MEASUREMENT"
    CONTROLLED_EXPERIMENT = "CONTROLLED_EXPERIMENT"
    REPRODUCED_RESULT = "REPRODUCED_RESULT"
    PRIMARY_DOCUMENT = "PRIMARY_DOCUMENT"
    SECONDARY_REPORT = "SECONDARY_REPORT"
    EXPERT_OPINION = "EXPERT_OPINION"
    MODEL_INFERENCE = "MODEL_INFERENCE"
    UNVERIFIED_ASSERTION = "UNVERIFIED_ASSERTION"
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"
    UNVERIFIED = "UNVERIFIED"


class EvidenceDirectness(str, Enum):
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"
    TERTIARY = "TERTIARY"
    DIRECT = "DIRECT"
    INDIRECT = "INDIRECT"
    CIRCUMSTANTIAL = "CIRCUMSTANTIAL"


class ConflictType(str, Enum):
    CONTRADICTORY_DATA = "CONTRADICTORY_DATA"
    METHODOLOGY_DIFFERENCE = "METHODOLOGY_DIFFERENCE"
    ENVIRONMENT_DIFFERENCE = "ENVIRONMENT_DIFFERENCE"
    TEMPORAL_DIVERGENCE = "TEMPORAL_DIVERGENCE"
    DIRECT_CONTRADICTION = "DIRECT_CONTRADICTION"
    MEASUREMENT_DISCREPANCY = "MEASUREMENT_DISCREPANCY"
    SCOPE_MISMATCH = "SCOPE_MISMATCH"


class ConflictStatus(str, Enum):
    UNRESOLVED = "UNRESOLVED"
    RESOLVED = "RESOLVED"
    EXPLAINED = "EXPLAINED"
    DETECTED = "DETECTED"


class ConfidenceLevel(str, Enum):
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"
    UNKNOWN = "UNKNOWN"


class HypothesisStatus(str, Enum):
    PROPOSED = "PROPOSED"
    SUPPORTED = "SUPPORTED"
    WEAKLY_SUPPORTED = "WEAKLY_SUPPORTED"
    DISPUTED = "DISPUTED"
    REJECTED = "REJECTED"
    UNRESOLVED = "UNRESOLVED"


class SessionStatus(str, Enum):
    INITIALIZING = "INITIALIZING"
    PLANNING = "PLANNING"
    INGESTING = "INGESTING"
    ANALYZING = "ANALYZING"
    SYNTHESIZING = "SYNTHESIZING"
    COMPLETED = "COMPLETED"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    FAILED = "FAILED"


# --- Domain Models ---


class Source(BaseModel):
    model_config = ConfigDict(extra="ignore")

    source_id: str = Field(default_factory=lambda: f"src_{uuid.uuid4().hex[:8]}")
    source_type: SourceType
    title: str
    publisher: str = "Unknown"
    author: str = "Unknown"
    url_or_reference: str = ""
    published_at: datetime | None = None
    retrieved_at: datetime = Field(default_factory=_now_utc)
    last_modified: datetime | None = None
    language: str = "en"
    domain: str = "general"
    trust_level: SourceTrustLevel = SourceTrustLevel.UNVERIFIED
    authority_score: float = 0.5  # 0.0 - 1.0
    freshness_score: float = 1.0  # 0.0 - 1.0
    relevance_score: float = 0.8  # 0.0 - 1.0
    is_primary: bool = False
    is_retracted: bool = False
    citations: list[str] = Field(default_factory=list)
    lineage: list[str] = Field(default_factory=list)  # source_ids this derives from
    provenance: dict[str, Any] = Field(default_factory=dict)

    @property
    def retracted(self) -> bool:
        return self.is_retracted

    @property
    def retraction_reason(self) -> str | None:
        return self.provenance.get("retraction_reason")


class DocumentChunk(BaseModel):
    model_config = ConfigDict(extra="ignore")

    chunk_id: str = Field(default_factory=lambda: f"chk_{uuid.uuid4().hex[:8]}")
    document_id: str
    content: str
    section: str | None = None
    page: int | None = None
    start_line: int | None = None
    end_line: int | None = None
    chunk_type: str = "paragraph"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def text(self) -> str:
        return self.content


class Document(BaseModel):
    model_config = ConfigDict(extra="ignore")

    document_id: str = Field(default_factory=lambda: f"doc_{uuid.uuid4().hex[:8]}")
    source_id: str
    title: str
    format: str = "text"  # markdown, pdf, html, json, csv, text
    raw_content: str = ""
    chunks: list[DocumentChunk] = Field(default_factory=list)
    content_hash: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now_utc)

    @property
    def content(self) -> str:
        return self.raw_content

    @content.setter
    def content(self, value: str) -> None:
        self.raw_content = value


class ClaimStatus(str, Enum):
    ACTIVE = "ACTIVE"
    VERIFIED = "VERIFIED"
    SUPERSEDED = "SUPERSEDED"
    DISPUTED = "DISPUTED"
    RETRACTED = "RETRACTED"


class Claim(BaseModel):
    model_config = ConfigDict(extra="ignore")

    claim_id: str = Field(default_factory=lambda: f"clm_{uuid.uuid4().hex[:8]}")
    subject: str
    predicate: str
    object: str
    claim_text: str
    claim_type: ClaimType = ClaimType.REPORTED
    source_id: str
    document_id: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.MODERATE
    scope: str = "general"
    status: ClaimStatus = ClaimStatus.ACTIVE
    valid_from: datetime = Field(default_factory=_now_utc)
    valid_until: datetime | None = None
    superseded_by: str | None = None
    created_at: datetime = Field(default_factory=_now_utc)


class Evidence(BaseModel):
    model_config = ConfigDict(extra="ignore")

    evidence_id: str = Field(default_factory=lambda: f"evd_{uuid.uuid4().hex[:8]}")
    claim_id: str
    source_id: str
    document_id: str | None = None
    excerpt_reference: str
    location: str = ""  # section/page
    evidence_type: EvidenceType = EvidenceType.PRIMARY_DOCUMENT
    strength: EvidenceStrength = EvidenceStrength.MODERATE
    directness: EvidenceDirectness = EvidenceDirectness.DIRECT
    independence_score: float = 1.0  # 0.0 - 1.0
    timestamp: datetime = Field(default_factory=_now_utc)
    provenance: dict[str, Any] = Field(default_factory=dict)


class ConflictRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    conflict_id: str = Field(default_factory=lambda: f"cfl_{uuid.uuid4().hex[:8]}")
    claim_a_id: str
    claim_b_id: str
    claim_a_text: str = ""
    claim_b_text: str = ""
    conflict_type: ConflictType = ConflictType.DIRECT_CONTRADICTION
    description: str = ""
    discrepancy_factors: list[str] = Field(default_factory=list)
    discrepancy_factor: str = ""
    status: ConflictStatus = ConflictStatus.DETECTED
    resolution_notes: str | None = None
    detected_at: datetime = Field(default_factory=_now_utc)


class UncertaintyRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    session_id: str = Field(default_factory=lambda: f"sess_{uuid.uuid4().hex[:8]}")
    known: list[str] = Field(default_factory=list)
    unknown: list[str] = Field(default_factory=list)
    uncertain: list[str] = Field(default_factory=list)
    disputed: list[str] = Field(default_factory=list)
    assumed: list[str] = Field(default_factory=list)
    inferred: list[str] = Field(default_factory=list)

    def __getitem__(self, item: str) -> list[str]:
        return getattr(self, item)


class KnowledgeGap(BaseModel):
    model_config = ConfigDict(extra="ignore")

    gap_id: str = Field(default_factory=lambda: f"gap_{uuid.uuid4().hex[:8]}")
    description: str
    importance: str = "HIGH"  # CRITICAL, HIGH, MEDIUM, LOW
    impact: str
    required_evidence: str
    recommended_research: list[str] = Field(default_factory=list)


class ResearchHypothesis(BaseModel):
    model_config = ConfigDict(extra="ignore")

    hypothesis_id: str = Field(default_factory=lambda: f"hyp_{uuid.uuid4().hex[:8]}")
    statement: str
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    supporting_evidence_refs: list[str] = Field(default_factory=list)
    counter_evidence_refs: list[str] = Field(default_factory=list)
    confidence: float = 0.5


class ResearchPlan(BaseModel):
    model_config = ConfigDict(extra="ignore")

    plan_id: str = Field(default_factory=lambda: f"pln_{uuid.uuid4().hex[:8]}")
    question: str
    sub_questions: list[str] = Field(default_factory=list)
    hypotheses: list[ResearchHypothesis] = Field(default_factory=list)
    search_strategy: str = "MULTI_DOMAIN"
    source_strategy: str = "PRIMARY_FIRST"
    evidence_requirements: list[str] = Field(default_factory=list)
    verification_strategy: str = "CROSS_SOURCE_CORRELATION"
    stop_conditions: list[str] = Field(default_factory=list)
    known_gaps: list[str] = Field(default_factory=list)
    expected_cost: float = 0.0


class QualityScore(BaseModel):
    model_config = ConfigDict(extra="ignore")

    source_quality: float = 0.85
    source_diversity: float = 0.80
    source_independence: float = 0.90
    evidence_strength: float = 0.85
    freshness: float = 0.95
    coverage: float = 0.80
    conflict_resolution: float = 1.0
    uncertainty: float = 0.85
    reproducibility: float = 0.90
    composite_score: float = 0.87

    @property
    def overall_score(self) -> float:
        return self.composite_score


class DecisionEvidencePackage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    package_id: str = Field(default_factory=lambda: f"dep_{uuid.uuid4().hex[:8]}")
    question: str
    options: list[str] = Field(default_factory=list)
    evidence_by_option: dict[str, list[str]] = Field(default_factory=dict)
    evidence_summary: list[str] = Field(default_factory=list)
    tradeoffs: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    recommendation_inputs: list[str] = Field(default_factory=list)


class ResearchTrace(BaseModel):
    model_config = ConfigDict(extra="ignore")

    session_id: str
    plan: ResearchPlan | None = None
    queries_executed: list[str] = Field(default_factory=list)
    sources_evaluated: int = 0
    claims_extracted: int = 0
    conflicts_found: int = 0
    synthesis_steps: list[str] = Field(default_factory=list)
    duration_ms: float = 0.0
    budget_used: float = 0.0


class SynthesisResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    session_id: str
    question: str
    executive_summary: str
    established_findings: list[str] = Field(default_factory=list)
    important_evidence: list[Evidence] = Field(default_factory=list)
    conflicting_evidence: list[ConflictRecord] = Field(default_factory=list)
    uncertainties: UncertaintyRecord | None = None
    assumptions: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    recommended_next_research: list[str] = Field(default_factory=list)
    affected_knowledge: list[str] = Field(default_factory=list)
    affected_decisions: list[str] = Field(default_factory=list)
    affected_plans: list[str] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    quality_score: QualityScore = Field(default_factory=QualityScore)
    decision_package: DecisionEvidencePackage | None = None
    trace: ResearchTrace | None = None


# --- Requests and API Models ---


class ResearchRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    question: str
    objective: str = "Knowledge Synthesis"
    scope: str = "global"
    mode: ResearchMode = ResearchMode.STANDARD
    domains: list[str] = Field(default_factory=lambda: ["general"])
    required_depth: int = 2
    required_sources: list[str] = Field(default_factory=list)
    excluded_sources: list[str] = Field(default_factory=list)
    max_cost: float = 5.0
    max_duration_seconds: int = 120
    tenant_id: str = "default"
    actor: str = "RESEARCHER"


class IngestDocumentRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str
    content: str
    format: str = "markdown"
    source_type: SourceType = SourceType.USER_DOCUMENT
    source_id: str | None = None
    url_or_reference: str = "manual_upload"
    publisher: str = "User"
    author: str = "User"
    is_primary: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    tenant_id: str = "default"


class VerifyClaimRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    claim_id: str
    verification_evidence: str
    is_verified: bool = True
    actor: str = "VERIFIER"
