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
