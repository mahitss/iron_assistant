"""Pydantic schemas and typed abstractions for Kairo Knowledge Fabric."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeType(str, Enum):
    """Categorization of workspace knowledge entities."""

    PROJECT = "PROJECT"
    CONVERSATION = "CONVERSATION"
    MEMORY = "MEMORY"
    DOCUMENT = "DOCUMENT"
    REPOSITORY = "REPOSITORY"
    COMMIT = "COMMIT"
    ISSUE = "ISSUE"
    PULL_REQUEST = "PULL_REQUEST"
    WORKFLOW = "WORKFLOW"
    WORKFLOW_RUN = "WORKFLOW_RUN"
    AGENT_TASK = "AGENT_TASK"
    RESEARCH_RESULT = "RESEARCH_RESULT"
    WEB_SOURCE = "WEB_SOURCE"
    NOTIFICATION = "NOTIFICATION"
    DEVICE = "DEVICE"
    TASK = "TASK"
    DECISION = "DECISION"


class KnowledgeRelationType(str, Enum):
    """Immutable, allowlisted relationship edge types."""

    BELONGS_TO = "BELONGS_TO"
    RELATED_TO = "RELATED_TO"
    DERIVED_FROM = "DERIVED_FROM"
    REFERENCES = "REFERENCES"
    CREATED_BY = "CREATED_BY"
    DEPENDS_ON = "DEPENDS_ON"
    CAUSED = "CAUSED"
    RESOLVES = "RESOLVES"
    BLOCKS = "BLOCKS"
    MENTIONS = "MENTIONS"
    OCCURRED_IN = "OCCURRED_IN"
    LINKED_TO = "LINKED_TO"
    SUPERSEDES = "SUPERSEDES"
    DUPLICATES = "DUPLICATES"


class KnowledgeSourceType(str, Enum):
    """Authoritative provenance categories ranked by trust ordering."""

    USER_EXPLICIT = "USER_EXPLICIT"
    VERIFIED_FIRST_PARTY_SOURCE = "VERIFIED_FIRST_PARTY_SOURCE"
    DIRECT_TOOL_RESULT = "DIRECT_TOOL_RESULT"
    CONVERSATION = "CONVERSATION"
    GITHUB = "GITHUB"
    WEB = "WEB"
    AGENT_RESULT = "AGENT_RESULT"
    SYSTEM_DERIVED = "SYSTEM_DERIVED"


class DecisionStatus(str, Enum):
    """Lifecycle state of an architectural or project decision."""

    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    REJECTED = "REJECTED"


class IndexJobStatus(str, Enum):
    """Status of background ingestion or indexing."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


# --- Knowledge Node Schemas ---


class KnowledgeNodeCreate(BaseModel):
    """Payload to create or index a new knowledge node."""

    type: KnowledgeType
    source_id: str = Field(..., min_length=1, max_length=256)
    title: str = Field(..., min_length=1, max_length=256)
    summary: str = Field(..., min_length=1)
    content: str | None = None
    project_id: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    source_type: KnowledgeSourceType = KnowledgeSourceType.SYSTEM_DERIVED
    source_url: str | None = None


class KnowledgeNodeUpdate(BaseModel):
    """Payload to update an existing knowledge node."""

    title: str | None = Field(default=None, max_length=256)
    summary: str | None = None
    content: str | None = None
    status: str | None = None
    project_id: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    metadata: dict[str, Any] | None = None


class KnowledgeNodeResponse(BaseModel):
    """Public representation of a Knowledge Node."""

    id: str
    user_id: str
    type: KnowledgeType
    source_id: str
    project_id: str | None = None
    title: str
    summary: str
    content: str | None = None
    status: str
    confidence: float
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime
    last_verified_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict, alias="node_metadata")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# --- Knowledge Edge Schemas ---


class KnowledgeEdgeCreate(BaseModel):
    """Payload to create an explicit knowledge relationship edge."""

    source_node_id: str
    target_node_id: str
    relation_type: KnowledgeRelationType
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: str = Field(default="SYSTEM_DERIVED", max_length=128)


class KnowledgeEdgeResponse(BaseModel):
    """Public representation of a Knowledge Edge."""

    id: str
    user_id: str
    source_node_id: str
    target_node_id: str
    relation_type: KnowledgeRelationType
    confidence: float
    source: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Knowledge Source Schemas ---


class KnowledgeSourceResponse(BaseModel):
    """Public provenance source representation."""

    id: str
    user_id: str
    source_type: KnowledgeSourceType
    source_id: str
    source_url: str | None = None
    title: str | None = None
    project_id: str | None = None
    confidence: float
    created_at: datetime
    meta: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


# --- Search Schemas ---


class KnowledgeSearchRequest(BaseModel):
    """Query filters for hybrid knowledge search."""

    query: str = Field(..., min_length=1)
    project_id: str | None = None
    type: KnowledgeType | None = None
    source_type: KnowledgeSourceType | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    limit: int = Field(default=15, ge=1, le=50)


class KnowledgeSearchResultItem(BaseModel):
    """Search hit representation with provenance and relevance."""

    id: str
    title: str
    summary: str
    type: KnowledgeType
    project_id: str | None = None
    source_id: str
    source_type: str | None = None
    source_url: str | None = None
    timestamp: datetime
    relevance: float
    confidence: float
    status: str = "ACTIVE"
    explanation: str | None = None


class KnowledgeSearchResponse(BaseModel):
    """Top-level search result payload."""

    query: str
    total_matches: int
    results: list[KnowledgeSearchResultItem]


# --- Timeline Schemas ---


class KnowledgeTimelineItem(BaseModel):
    """Chronological event in project history."""

    node_id: str
    timestamp: datetime
    title: str
    summary: str
    type: KnowledgeType
    source_id: str
    source_type: str | None = None
    project_id: str | None = None
    status: str = "ACTIVE"


class KnowledgeTimelineResponse(BaseModel):
    """Chronologically sorted timeline of workspace events."""

    project_id: str | None = None
    total_events: int
    events: list[KnowledgeTimelineItem]


# --- Decisions Schemas ---


class DecisionCreate(BaseModel):
    """Payload to record an architectural or design decision."""

    decision: str = Field(..., min_length=3, max_length=500, description="Decision summary or title")
    rationale: str | None = Field(default=None, description="Detailed reasoning and context")
    project_id: str | None = None
    source: str = Field(default="USER_EXPLICIT", description="Decision origin")


class DecisionSupersedeRequest(BaseModel):
    """Payload to supersede an existing decision with a new decision."""

    new_decision: str = Field(..., min_length=3, max_length=500)
    rationale: str | None = None
    reason: str | None = None


class DecisionResponse(BaseModel):
    """Representation of an architectural decision."""

    id: str
    decision: str
    rationale: str | None = None
    project_id: str | None = None
    status: DecisionStatus
    source: str
    created_at: datetime
    updated_at: datetime
    superseded_by: str | None = None


# --- Document & Indexing Schemas ---


class DocumentUploadResponse(BaseModel):
    """Response after initiating document ingestion."""

    job_id: str
    document_id: str
    filename: str
    status: IndexJobStatus
    chunks_created: int = 0
    message: str


class IndexingJobResponse(BaseModel):
    """Status report for a background indexing job."""

    id: str
    job_type: str
    status: IndexJobStatus
    node_id: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Graph Schemas ---


class KnowledgeGraphResponse(BaseModel):
    """Bounded subgraph representation for visual and programmatic traversal."""

    root_node_id: str
    nodes: list[KnowledgeNodeResponse]
    edges: list[KnowledgeEdgeResponse]
    depth_reached: int


# ============================================================================
# RAG V2 SCHEMAS (Task 40)
# ============================================================================


class RAGSourceType(str, Enum):
    """Supported source origins in Kairo RAG V2."""

    DOCUMENT = "DOCUMENT"
    PDF = "PDF"
    MARKDOWN = "MARKDOWN"
    CODE = "CODE"
    GITHUB = "GITHUB"
    WEBSITE = "WEBSITE"
    NOTE = "NOTE"
    CONVERSATION = "CONVERSATION"
    IMAGE_OCR = "IMAGE_OCR"
    AUDIO_TRANSCRIPT = "AUDIO_TRANSCRIPT"
    VIDEO_TRANSCRIPT = "VIDEO_TRANSCRIPT"
    STRUCTURED_DATA = "STRUCTURED_DATA"
    MEMORY = "MEMORY"
    WORLD_STATE = "WORLD_STATE"
    RESEARCH = "RESEARCH"


class ChunkContentType(str, Enum):
    """Semantic category of an extracted chunk."""

    HEADING = "HEADING"
    PARAGRAPH = "PARAGRAPH"
    CODE_BLOCK = "CODE_BLOCK"
    TABLE = "TABLE"
    LIST = "LIST"
    EQUATION = "EQUATION"
    IMAGE_CAPTION = "IMAGE_CAPTION"
    TRANSCRIPT_SEGMENT = "TRANSCRIPT_SEGMENT"
    STRUCTURED_ROW = "STRUCTURED_ROW"
    SYMBOL_DEF = "SYMBOL_DEF"


class FreshnessState(str, Enum):
    """Observation and content freshness classification."""

    FRESH = "FRESH"
    RECENT = "RECENT"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class TrustTier(str, Enum):
    """Authoritative source trust ordering hierarchy."""

    USER_UPLOAD = "USER_UPLOAD"          # 100
    AUTHORIZED_GITHUB = "AUTHORIZED_GITHUB"  # 90
    PROJECT_KNOWLEDGE = "PROJECT_KNOWLEDGE"  # 85
    OFFICIAL_DOCS = "OFFICIAL_DOCS"      # 80
    WORLD_MODEL = "WORLD_MODEL"          # 75
    RECENT_WEB = "RECENT_WEB"            # 60
    LONG_TERM_MEMORY = "LONG_TERM_MEMORY" # 50
    CONVERSATION = "CONVERSATION"        # 45


TRUST_WEIGHTS: dict[str, float] = {
    TrustTier.USER_UPLOAD: 1.0,
    TrustTier.AUTHORIZED_GITHUB: 0.90,
    TrustTier.PROJECT_KNOWLEDGE: 0.85,
    TrustTier.OFFICIAL_DOCS: 0.80,
    TrustTier.WORLD_MODEL: 0.75,
    TrustTier.RECENT_WEB: 0.60,
    TrustTier.LONG_TERM_MEMORY: 0.50,
    TrustTier.CONVERSATION: 0.45,
}


class ChunkMetadata(BaseModel):
    """Fine-grained provenance and positional metadata for each chunk."""

    chunk_id: str
    document_id: str
    page: int | None = None
    section: str | None = None
    section_id: str | None = None
    headings: list[str] = Field(default_factory=list)
    content_type: ChunkContentType = ChunkContentType.PARAGRAPH
    start_time: float | None = None
    end_time: float | None = None
    speaker: str | None = None
    file_path: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    commit_hash: str | None = None
    source_url: str | None = None
    user_id: str = "default_user"
    project_id: str | None = None
    freshness: FreshnessState = FreshnessState.FRESH
    source_type: RAGSourceType = RAGSourceType.DOCUMENT
    trust_tier: TrustTier = TrustTier.USER_UPLOAD
    custom_metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentChunk(BaseModel):
    """Single semantic unit extracted and indexed."""

    id: str
    content: str
    metadata: ChunkMetadata
    embedding: list[float] | None = None
    content_hash: str = ""

    model_config = ConfigDict(from_attributes=True)


class Citation(BaseModel):
    """Perplexity-level verified citation linked to authoritative origin."""

    id: str
    source_type: RAGSourceType
    source_id: str
    title: str
    citation_label: str
    snippet: str
    source_url: str | None = None
    page_number: int | None = None
    section_name: str | None = None
    file_path: str | None = None
    line_range: str | None = None
    commit_hash: str | None = None
    relevance_score: float = 1.0


class RetrievedChunk(BaseModel):
    """Reranked and scored chunk ready for context assembly."""

    chunk: DocumentChunk
    score: float
    semantic_score: float = 0.0
    lexical_score: float = 0.0
    freshness_score: float = 1.0
    metadata_score: float = 1.0
    citation: Citation | None = None


class RetrieverPlan(BaseModel):
    """Execution plan generated by RetrieverPlanner."""

    query: str
    intent: str = "GENERAL"
    selected_sources: list[RAGSourceType] = Field(default_factory=list)
    filter_project_id: str | None = None
    requires_code: bool = False
    requires_multimodal: bool = False
    requires_fresh_web: bool = False
    max_chunks: int = 10
    reasoning: str = ""


class RAGQueryRequest(BaseModel):
    """User or agent query requesting grounded context."""

    query: str = Field(..., min_length=1)
    project_id: str | None = None
    user_id: str | None = None
    device_id: str | None = None
    allowed_sources: list[RAGSourceType] | None = None
    top_k: int = Field(default=8, ge=1, le=50)
    max_context_tokens: int = Field(default=4000, ge=100, le=32000)
    include_citations: bool = True
    deduplicate: bool = True
    rerank: bool = True
    compress: bool = True
    min_relevance: float = Field(default=0.1, ge=0.0, le=1.0)


class GroundedContext(BaseModel):
    """Full grounded context package delivered to Model Context."""

    query: str
    context_text: str
    chunks: list[RetrievedChunk]
    citations: list[Citation]
    sources_used: list[str]
    tokens_used: int
    plan: RetrieverPlan
    retrieval_latency_ms: float = 0.0


class CodeSymbol(BaseModel):
    """AST-extracted symbol in code intelligence."""

    name: str
    type: str  # FUNCTION, CLASS, METHOD, MODULE, VARIABLE, IMPORT
    file_path: str
    start_line: int
    end_line: int
    signature: str | None = None
    docstring: str | None = None
    parent_symbol: str | None = None
    language: str = "python"


class CodeDependency(BaseModel):
    """Dependency link in the code graph."""

    source_file: str
    target_file: str
    source_symbol: str | None = None
    target_symbol: str | None = None
    dependency_type: str = "IMPORTS"  # IMPORTS, CALLS, EXTENDS, INSTANTIATES


class EntityNode(BaseModel):
    """Entity node in knowledge graph."""

    name: str
    entity_type: str = "CONCEPT"
    aliases: list[str] = Field(default_factory=list)
    mentions_count: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)


class RelationEdge(BaseModel):
    """Directed relation edge between entities in knowledge graph."""

    source: str
    relation_type: str = "RELATED_TO"
    target: str
    weight: float = 1.0
    evidence_chunks: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

