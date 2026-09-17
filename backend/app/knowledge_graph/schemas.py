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
    PERSON_CONTEXT = "PERSON_CONTEXT"
    ORGANIZATION = "ORGANIZATION"
    PROJECT = "PROJECT"
    REPOSITORY = "REPOSITORY"
    FILE = "FILE"
    DOCUMENT = "DOCUMENT"
    TASK = "TASK"
    GOAL = "GOAL"
    DECISION = "DECISION"
    ACTION = "ACTION"
    CAPABILITY = "CAPABILITY"
    CAPABILITY_VERSION = "CAPABILITY_VERSION"
    TOOL = "TOOL"
    WORKFLOW = "WORKFLOW"
    SERVICE = "SERVICE"
    DEPLOYMENT = "DEPLOYMENT"
    ENVIRONMENT = "ENVIRONMENT"
    RESOURCE = "RESOURCE"
    MEMORY = "MEMORY"
    KNOWLEDGE = "KNOWLEDGE"
    EVIDENCE = "EVIDENCE"
    EVENT = "EVENT"
    INCIDENT = "INCIDENT"
    AGENT = "AGENT"
    SYSTEM = "SYSTEM"
    EXTERNAL_ENTITY = "EXTERNAL_ENTITY"
    HYPOTHESIS = "HYPOTHESIS"
    ASSUMPTION = "ASSUMPTION"
    OBSERVATION = "OBSERVATION"
    CONVERSATION = "CONVERSATION"
    MESSAGE = "MESSAGE"
    MEETING = "MEETING"
    DEVICE = "DEVICE"
    APPLICATION = "APPLICATION"
    COMPONENT = "COMPONENT"
    PREFERENCE = "PREFERENCE"
    SKILL = "SKILL"
    OUTCOME = "OUTCOME"
    LOCATION = "LOCATION"


class RelationshipType(str, Enum):
    OWNS = "OWNS"
    USES = "USES"
    USED_BY = "USED_BY"
    WORKS_ON = "WORKS_ON"
    PART_OF = "PART_OF"
    CHILD_OF = "CHILD_OF"
    PARENT_OF = "PARENT_OF"
    DEPENDS_ON = "DEPENDS_ON"
    TRANSITIVELY_DEPENDS_ON = "TRANSITIVELY_DEPENDS_ON"
    IMPLEMENTS = "IMPLEMENTS"
    DERIVED_FROM = "DERIVED_FROM"
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    SUPERSEDES = "SUPERSEDES"
    REPLACED_BY = "REPLACED_BY"
    RECOVERED_BY = "RECOVERED_BY"
    CAUSES = "CAUSES"
    RESULTS_IN = "RESULTS_IN"
    AFFECTS = "AFFECTS"
    BLOCKS = "BLOCKS"
    BLOCKED_BY = "BLOCKED_BY"
    REQUIRES = "REQUIRES"
    REQUIRES_APPROVAL = "REQUIRES_APPROVAL"
    ALLOCATED_FROM = "ALLOCATED_FROM"
    DEPLOYS_TO = "DEPLOYS_TO"
    RUNS_ON = "RUNS_ON"
    RELATED_TO = "RELATED_TO"
    OBSERVED_IN = "OBSERVED_IN"
    EVIDENCE_FOR = "EVIDENCE_FOR"
    ASSUMES = "ASSUMES"
    VALIDATES = "VALIDATES"
    INVALIDATES = "INVALIDATES"
    EXECUTED_BY = "EXECUTED_BY"
    DECIDED_BY = "DECIDED_BY"
    PLANNED_BY = "PLANNED_BY"
    DECIDED_IN = "DECIDED_IN"
    CREATED = "CREATED"
    MODIFIED = "MODIFIED"
    DISCUSSED_IN = "DISCUSSED_IN"
    MENTIONED_IN = "MENTIONED_IN"
    ASSIGNED_TO = "ASSIGNED_TO"
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


class CertaintyLevel(str, Enum):
    """Rigid certainty levels preventing assumption escalation (Phase 4)."""
    KNOWN = "KNOWN"
    LIKELY = "LIKELY"
    POSSIBLE = "POSSIBLE"
    UNCERTAIN = "UNCERTAIN"
    CONTRADICTED = "CONTRADICTED"
    UNKNOWN = "UNKNOWN"


class ProvenanceClassification(str, Enum):
    """Distinguishes direct observations from deductive or external sources (Phase 3)."""
    OBSERVED = "OBSERVED"
    INFERRED = "INFERRED"
    DERIVED = "DERIVED"
    MODEL_GENERATED = "MODEL_GENERATED"
    EXTERNALLY_SOURCED = "EXTERNALLY_SOURCED"
    SYSTEM_VERIFIED = "SYSTEM_VERIFIED"


class GraphQueryType(str, Enum):
    """Structured graph query patterns supported by the reasoning engine (Phase 10)."""
    DIRECT_RELATION = "DIRECT_RELATION"
    ONE_HOP = "ONE_HOP"
    MULTI_HOP = "MULTI_HOP"
    DEPENDENCY_QUERY = "DEPENDENCY_QUERY"
    IMPACT_QUERY = "IMPACT_QUERY"
    EVIDENCE_QUERY = "EVIDENCE_QUERY"
    LINEAGE_QUERY = "LINEAGE_QUERY"
    TEMPORAL_QUERY = "TEMPORAL_QUERY"
    ANCESTRY_QUERY = "ANCESTRY_QUERY"
    DESCENDANT_QUERY = "DESCENDANT_QUERY"
    SHORTEST_VERIFIED_PATH = "SHORTEST_VERIFIED_PATH"
    RELATED_ENTITY_QUERY = "RELATED_ENTITY_QUERY"


class ConflictResolutionState(str, Enum):
    """State of a contradiction or conflict edge (Phase 22)."""
    CONFLICTED = "CONFLICTED"
    RESOLVED = "RESOLVED"
    UNRESOLVED = "UNRESOLVED"
    SUPERSEDED = "SUPERSEDED"


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

class GraphProvenanceSchema(BaseModel):
    """Structured epistemic provenance record (Phase 3)."""
    model_config = ConfigDict(extra="ignore")

    source_id: str = ""
    source_type: str = "SYSTEM"
    classification: ProvenanceClassification = ProvenanceClassification.OBSERVED
    extraction_method: str = "SYSTEM"
    timestamp: datetime = Field(default_factory=utc_now)


class KnowledgeNodeSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    node_id: str = Field(default_factory=generate_uuid)
    node_type: NodeType = NodeType.KNOWLEDGE
    canonical_name: str = ""
    canonical_key: str = ""
    label: str = ""
    aliases: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    scope: ScopeType = ScopeType.PRIVATE
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    provenance: Union[GraphProvenanceSchema, Dict[str, Any]] = Field(default_factory=dict)
    confidence: float = 1.0
    certainty: CertaintyLevel = CertaintyLevel.KNOWN
    sensitivity: str = "INTERNAL"
    validity_start: Optional[datetime] = None
    validity_end: Optional[datetime] = None
    version: int = 1
    fingerprint: str = ""
    status: str = "ACTIVE"
    user_id: str = "default_user"
    project_id: Optional[str] = None

    def __init__(self, **data: Any) -> None:
        if "id" in data and "node_id" not in data:
            data["node_id"] = data["id"]
        if "name" in data and "canonical_name" not in data:
            data["canonical_name"] = data["name"]
        if not data.get("canonical_name") and data.get("canonical_key"):
            data["canonical_name"] = data["canonical_key"]
        if not data.get("canonical_name") and data.get("node_id"):
            data["canonical_name"] = data["node_id"]
        if not data.get("canonical_key") and data.get("canonical_name"):
            data["canonical_key"] = data["canonical_name"].strip().lower()
        if not data.get("label") and data.get("canonical_name"):
            data["label"] = data["canonical_name"]
        super().__init__(**data)

    @property
    def id(self) -> str:
        return self.node_id


class KnowledgeEdgeSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    edge_id: str = Field(default_factory=generate_uuid)
    source_node_id: str
    relationship: RelationshipType
    target_node_id: str
    confidence: float = 1.0
    certainty: CertaintyLevel = CertaintyLevel.KNOWN
    provenance: Union[GraphProvenanceSchema, Dict[str, Any]] = Field(default_factory=dict)
    provenance_type: ProvenanceClassification = ProvenanceClassification.OBSERVED
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    scope: ScopeType = ScopeType.PRIVATE
    status: str = "ACTIVE"
    version: int = 1
    metadata_fingerprint: str = ""
    derivation_rule: Optional[str] = None
    parent_edge_ids: List[str] = Field(default_factory=list)
    user_id: str = "default_user"
    project_id: Optional[str] = None

    def __init__(self, **data: Any) -> None:
        if "id" in data and "edge_id" not in data:
            data["edge_id"] = data["id"]
        if "relation_type" in data and "relationship" not in data:
            data["relationship"] = data["relation_type"]
        if "relationship_type" in data and "relationship" not in data:
            data["relationship"] = data["relationship_type"]
        if "source_node" in data and "source_node_id" not in data:
            data["source_node_id"] = data["source_node"]
        if "target_node" in data and "target_node_id" not in data:
            data["target_node_id"] = data["target_node"]
        super().__init__(**data)

    @property
    def id(self) -> str:
        return self.edge_id

    @property
    def relationship_type(self) -> RelationshipType:
        return self.relationship

    @property
    def source_node(self) -> str:
        return self.source_node_id

    @property
    def target_node(self) -> str:
        return self.target_node_id


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
    execution_time_ms: float = 0.0

    @property
    def depth_reached(self) -> int:
        return self.traversal_depth

    @property
    def path_found(self) -> bool:
        return len(self.nodes) > 0 and (len(self.edges) > 0 or len(self.nodes) == 1)

    @property
    def path(self) -> List[Dict[str, Any]]:
        result = []
        for i, node in enumerate(self.nodes):
            edge = self.edges[i] if i < len(self.edges) else None
            result.append({"node_id": node.node_id, "node": node, "edge": edge})
        return result

    def __getitem__(self, item: str) -> Any:
        if item == "path_found":
            return self.path_found
        if item == "path":
            return self.path
        if hasattr(self, item):
            return getattr(self, item)
        raise KeyError(item)


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


# =====================================================================
# TASK 97 GRAPH REASONING & RELATIONSHIP INTELLIGENCE SCHEMAS
# =====================================================================

class GraphTraversalLimits(BaseModel):
    """Hard safety bounds preventing combinatorial graph explosions (Phase 11)."""
    model_config = ConfigDict(extra="ignore")

    max_depth: int = 5
    max_nodes: int = 200
    max_edges: int = 500
    max_execution_time_seconds: float = 3.0
    max_branching_factor: int = 25
    max_execution_time_ms: float = 3000.0


class GraphQueryRequest(BaseModel):
    """Structured graph query request specification (Phase 10)."""
    model_config = ConfigDict(extra="ignore")

    query_type: GraphQueryType = GraphQueryType.DIRECT_RELATION
    start_node_id: Optional[str] = None
    target_node_id: Optional[str] = None
    relationship_types: Optional[List[RelationshipType]] = None
    min_confidence: float = 0.0
    certainty_filter: Optional[List[CertaintyLevel]] = None
    as_of: Optional[datetime] = None
    limits: GraphTraversalLimits = Field(default_factory=GraphTraversalLimits)
    user_id: str = "default_user"
    scope: Optional[Any] = None
    allowed_sensitivities: Optional[List[str]] = None


class ImpactedNodeRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    node_id: str
    canonical_name: str = ""
    node_type: str = ""
    depth: int = 1
    relationship: str = ""
    confidence: float = 1.0
    criticality: str = "LOW"

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item, None)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)


class ImpactAnalysisResult(BaseModel):
    """Structured downstream impact analysis result (Phase 15)."""
    model_config = ConfigDict(extra="ignore")

    root_node_id: str
    impacted_nodes: List[Union[Dict[str, Any], ImpactedNodeRecord]] = Field(default_factory=list)
    propagation_paths: List[List[str]] = Field(default_factory=list)
    depth: int = 0
    risk_criticality: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    total_affected: int = 0
    summary: str = ""

    @property
    def origin_node(self) -> str:
        return self.root_node_id

    @property
    def max_propagation_depth(self) -> int:
        return self.depth

    @property
    def overall_risk_severity(self) -> str:
        return self.risk_criticality

    @property
    def revalidation_candidates(self) -> List[str]:
        candidates = []
        for item in self.impacted_nodes:
            nid = item.get("node_id") if isinstance(item, dict) else getattr(item, "node_id", None)
            crit = item.get("criticality") if isinstance(item, dict) else getattr(item, "criticality", "")
            ntype = item.get("node_type") if isinstance(item, dict) else getattr(item, "node_type", "")
            if crit in ("HIGH", "CRITICAL") or ntype in ("CAPABILITY", "WORKFLOW", "DECISION"):
                if nid and nid not in candidates:
                    candidates.append(nid)
        return candidates


class LineageStepRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    node_id: str
    node_type: str = ""
    relationship: str = "ROOT"
    provenance: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item, None)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)


class LineageReconstructionResult(BaseModel):
    """Full operational lineage reconstruction across Kairo subsystems (Phases 17-21)."""
    model_config = ConfigDict(extra="ignore")

    lineage_type: str  # DECISION, ACTION, MEMORY, AGENT, CONTEXT
    root_id: str
    steps: List[Union[Dict[str, Any], LineageStepRecord]] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)
    is_complete: bool = True
    provenance_chain: List[str] = Field(default_factory=list)
    summary: str = ""

    @property
    def target_node(self) -> str:
        return self.root_id


class GraphSnapshot(BaseModel):
    """Point-in-time immutable reference snapshot of graph state (Phase 32)."""
    model_config = ConfigDict(extra="ignore")

    snapshot_id: str = Field(default_factory=generate_uuid)
    snapshot_type: str = "CURRENT"  # CURRENT, HISTORICAL, TASK, DECISION, INCIDENT
    label: str = ""
    node_count: int = 0
    edge_count: int = 0
    node_ids: List[str] = Field(default_factory=list)
    edge_ids: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def __init__(self, **data: Any) -> None:
        if "label" not in data and "snapshot_type" in data:
            data["label"] = data["snapshot_type"]
        super().__init__(**data)


class GraphDiffResult(BaseModel):
    """Comparative delta between two graph states (Phase 33)."""
    model_config = ConfigDict(extra="ignore")

    snapshot_a_id: str
    snapshot_b_id: str
    added_nodes: List[str] = Field(default_factory=list)
    removed_nodes: List[str] = Field(default_factory=list)
    changed_nodes: List[str] = Field(default_factory=list)
    added_edges: List[str] = Field(default_factory=list)
    removed_edges: List[str] = Field(default_factory=list)
    changed_edges: List[str] = Field(default_factory=list)


class InferenceRuleRecord(BaseModel):
    """Deterministic, bounded inference rule contract (Phase 13)."""
    model_config = ConfigDict(extra="ignore")

    rule_id: str
    name: str
    premise_relations: List[RelationshipType]
    derived_relation: RelationshipType
    confidence_decay: float = 0.9
    transitive: bool = False


class ConflictRecord(BaseModel):
    """Explicit contradiction edge and dialectic resolution state (Phase 22)."""
    model_config = ConfigDict(extra="ignore")

    conflict_id: str = Field(default_factory=generate_uuid)
    source_node_id: str = ""
    target_node_id: str = ""
    conflict_type: str = "DIRECT_CONTRADICTION"
    resolution_state: ConflictResolutionState = ConflictResolutionState.UNRESOLVED
    evidence_refs: List[str] = Field(default_factory=list)
    detected_at: datetime = Field(default_factory=utc_now)
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    reason: str = ""
    confidence: float = 1.0

    def __init__(self, **data: Any) -> None:
        if "node_a" in data and "source_node_id" not in data:
            data["source_node_id"] = data["node_a"]
        if "node_b" in data and "target_node_id" not in data:
            data["target_node_id"] = data["node_b"]
        if "status" in data and "resolution_state" not in data:
            data["resolution_state"] = data["status"]
        super().__init__(**data)

    @property
    def node_a(self) -> str:
        return self.source_node_id

    @property
    def node_b(self) -> str:
        return self.target_node_id

    @property
    def status(self) -> ConflictResolutionState:
        return self.resolution_state
