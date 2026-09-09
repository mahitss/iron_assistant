"""Pydantic v2 schemas and enums for Kairo Personal Knowledge Graph & Relationship Memory Engine (Task 50)."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import uuid
from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


def generate_uuid() -> str:
    return str(uuid.uuid4())


# =====================================================================
# ENUMS
# =====================================================================

class NodeType(str, Enum):
    USER = "USER"
    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    PROJECT = "PROJECT"
    REPOSITORY = "REPOSITORY"
    FILE = "FILE"
    DOCUMENT = "DOCUMENT"
    TASK = "TASK"
    GOAL = "GOAL"
    DECISION = "DECISION"
    CONVERSATION = "CONVERSATION"
    MESSAGE = "MESSAGE"
    MEETING = "MEETING"
    DEVICE = "DEVICE"
    APPLICATION = "APPLICATION"
    SERVICE = "SERVICE"
    DEPLOYMENT = "DEPLOYMENT"
    ENVIRONMENT = "ENVIRONMENT"
    EVENT = "EVENT"
    PREFERENCE = "PREFERENCE"
    SKILL = "SKILL"
    KNOWLEDGE = "KNOWLEDGE"
    OUTCOME = "OUTCOME"
    RESOURCE = "RESOURCE"
    LOCATION = "LOCATION"


class RelationshipType(str, Enum):
    OWNS = "OWNS"
    USES = "USES"
    WORKS_ON = "WORKS_ON"
    PART_OF = "PART_OF"
    DEPENDS_ON = "DEPENDS_ON"
    CREATED = "CREATED"
    MODIFIED = "MODIFIED"
    DISCUSSED_IN = "DISCUSSED_IN"
    MENTIONED_IN = "MENTIONED_IN"
    ASSIGNED_TO = "ASSIGNED_TO"
    BLOCKS = "BLOCKS"
    BLOCKED_BY = "BLOCKED_BY"
    DEPLOYS_TO = "DEPLOYS_TO"
    RUNS_ON = "RUNS_ON"
    RELATED_TO = "RELATED_TO"
    DERIVED_FROM = "DERIVED_FROM"
    RESULTED_IN = "RESULTED_IN"
    DECIDED_IN = "DECIDED_IN"
    PREFERS = "PREFERS"
    KNOWS = "KNOWS"
    COLLABORATES_WITH = "COLLABORATES_WITH"
    CONTACTED = "CONTACTED"
    ATTENDED = "ATTENDED"
    SCHEDULED_FOR = "SCHEDULED_FOR"
    LOCATED_AT = "LOCATED_AT"
    HAS_SKILL = "HAS_SKILL"
    HAS_ROLE = "HAS_ROLE"
    HAS_PREFERENCE = "HAS_PREFERENCE"
    HAS_OUTCOME = "HAS_OUTCOME"


class AssertionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    CONTRADICTED = "CONTRADICTED"
    RETRACTED = "RETRACTED"
    EXPIRED = "EXPIRED"
    UNVERIFIED = "UNVERIFIED"


class DecisionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class MemoryType(str, Enum):
    EPISODIC = "EPISODIC"
    SEMANTIC = "SEMANTIC"
    PROCEDURAL = "PROCEDURAL"
    PREFERENCE = "PREFERENCE"
    PROJECT = "PROJECT"
    RELATIONSHIP = "RELATIONSHIP"
    DECISION = "DECISION"
    OUTCOME = "OUTCOME"


class ProvenanceType(str, Enum):
    USER = "USER"
    SYSTEM = "SYSTEM"
    DOCUMENT = "DOCUMENT"
    MESSAGE = "MESSAGE"
    MEETING = "MEETING"
    EVENT = "EVENT"
    API = "API"
    OBSERVATION = "OBSERVATION"
    VERIFICATION = "VERIFICATION"
    LEARNING = "LEARNING"
    IMPORT = "IMPORT"


class ScopeType(str, Enum):
    PRIVATE = "PRIVATE"
    PROJECT = "PROJECT"
    ORGANIZATION = "ORGANIZATION"
    GLOBAL = "GLOBAL"


class TemporalState(str, Enum):
    CURRENT = "CURRENT"
    HISTORICAL = "HISTORICAL"
    INFERRED = "INFERRED"
    UNKNOWN = "UNKNOWN"


class ConfidenceTier(str, Enum):
    EXPLICIT = "EXPLICIT"
    VERIFIED = "VERIFIED"
    OBSERVED = "OBSERVED"
    INFERRED = "INFERRED"


class PreferenceCategory(str, Enum):
    COMMUNICATION = "COMMUNICATION"
    TECHNICAL = "TECHNICAL"
    WORKFLOW = "WORKFLOW"
    FORMATTING = "FORMATTING"
    NOTIFICATION = "NOTIFICATION"
    TOOL = "TOOL"
    ENVIRONMENT = "ENVIRONMENT"


class SkillConfidence(str, Enum):
    CLAIMED = "CLAIMED"
    DEMONSTRATED = "DEMONSTRATED"
    VERIFIED = "VERIFIED"


# =====================================================================
# CORE SCHEMAS
# =====================================================================

class KnowledgeNodeSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    node_id: str = Field(default_factory=generate_uuid)
    node_type: NodeType = NodeType.KNOWLEDGE
    canonical_name: str
    aliases: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    scope: ScopeType = ScopeType.PRIVATE
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0
    status: str = "ACTIVE"
    user_id: str = "default_user"
    project_id: Optional[str] = None


class KnowledgeEdgeSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    edge_id: str = Field(default_factory=generate_uuid)
    source_node_id: str
    relationship: RelationshipType
    target_node_id: str
    confidence: float = 1.0
    provenance: Dict[str, Any] = Field(default_factory=dict)
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    scope: ScopeType = ScopeType.PRIVATE
    status: str = "ACTIVE"
    user_id: str = "default_user"
    project_id: Optional[str] = None


class AssertionSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    assertion_id: str = Field(default_factory=generate_uuid)
    subject: str
    predicate: str
    object: str
    source: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utc_now)
    confidence: float = 1.0
    status: AssertionStatus = AssertionStatus.ACTIVE
    scope: ScopeType = ScopeType.PRIVATE
    user_id: str = "default_user"
    is_inferred: bool = False


class DecisionSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    decision_id: str = Field(default_factory=generate_uuid)
    question: str
    decision: str
    alternatives: List[str] = Field(default_factory=list)
    rationale_reference: Optional[str] = None
    owner: str
    timestamp: datetime = Field(default_factory=utc_now)
    scope: ScopeType = ScopeType.PROJECT
    confidence: float = 1.0
    status: DecisionStatus = DecisionStatus.ACTIVE
    user_id: str = "default_user"
    project_id: Optional[str] = None


class PreferenceMemorySchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    preference_id: str = Field(default_factory=generate_uuid)
    category: PreferenceCategory = PreferenceCategory.TECHNICAL
    value: Dict[str, Any]
    scope: ScopeType = ScopeType.PRIVATE
    confidence: float = 1.0
    source: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    last_confirmed: datetime = Field(default_factory=utc_now)
    expires_at: Optional[datetime] = None
    user_id: str = "default_user"
    project_id: Optional[str] = None
    is_temporary: bool = False


class OutcomeSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    outcome_id: str = Field(default_factory=generate_uuid)
    related_goal_id: str
    result: Dict[str, Any]
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    verified: bool = False
    timestamp: datetime = Field(default_factory=utc_now)
    user_id: str = "default_user"


class ContradictionSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    contradiction_id: str = Field(default_factory=generate_uuid)
    subject: str
    conflicting_assertions: List[Dict[str, Any]] = Field(default_factory=list)
    detected_at: datetime = Field(default_factory=utc_now)
    resolution: Optional[Dict[str, Any]] = None
    status: str = "DETECTED"
    user_id: str = "default_user"


class GraphQueryResultSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    nodes: List[KnowledgeNodeSchema] = Field(default_factory=list)
    edges: List[KnowledgeEdgeSchema] = Field(default_factory=list)
    explanations: List[str] = Field(default_factory=list)
    path_confidence: float = 1.0
    traversal_depth: int = 1
    total_nodes_visited: int = 0


class EntitySummarySchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    entity_id: str
    canonical_name: str
    node_type: NodeType
    summary_text: str
    key_relationships: List[Dict[str, Any]] = Field(default_factory=list)
    recent_changes: List[str] = Field(default_factory=list)
    active_decisions: List[str] = Field(default_factory=list)
    stale_flags: List[str] = Field(default_factory=list)
