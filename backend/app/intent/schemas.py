"""Pydantic schemas and enums for Kairo Unified Command, Intent, Goals, and Safe Motivation Engine (Tasks 35 & 48)."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, ConfigDict, Field


class IntentType(str, Enum):
    """Supported structured intent categories (Spec 4)."""

    QUESTION = "QUESTION"
    REQUEST = "REQUEST"
    COMMAND = "COMMAND"
    TASK = "TASK"
    INFORMATION = "INFORMATION"
    RESEARCH = "RESEARCH"
    CREATE = "CREATE"
    MODIFY = "MODIFY"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    AUTOMATE = "AUTOMATE"
    SCHEDULE = "SCHEDULE"
    REMIND = "REMIND"
    ANALYZE = "ANALYZE"
    DEBUG = "DEBUG"
    CODE = "CODE"
    DEPLOY = "DEPLOY"
    COMMUNICATE = "COMMUNICATE"
    SEARCH = "SEARCH"
    COMPARE = "COMPARE"
    PLAN = "PLAN"
    EXPLAIN = "EXPLAIN"
    SUMMARIZE = "SUMMARIZE"
    MONITOR = "MONITOR"
    NOTIFY = "NOTIFY"
    NAVIGATE = "NAVIGATE"
    CONTROL = "CONTROL"
    TRANSACT = "TRANSACT"
    CANCEL = "CANCEL"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    RETRY = "RETRY"


class IntentStatus(str, Enum):
    """9 standardized lifecycle states for structured intent (Spec 3)."""

    DETECTED = "DETECTED"
    INTERPRETED = "INTERPRETED"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class GoalStatus(str, Enum):
    """Lifecycle states for desired user outcomes (Spec 9)."""

    ACTIVE = "ACTIVE"
    IN_PROGRESS = "IN_PROGRESS"
    ACHIEVED = "ACHIEVED"
    BLOCKED = "BLOCKED"
    ABANDONED = "ABANDONED"
    CANCELLED = "CANCELLED"


class UrgencyLevel(str, Enum):
    """Urgency classification (Spec 39)."""

    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AmbiguityLevel(str, Enum):
    """Ambiguity severity classification (Spec 56)."""

    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IntentRiskLevel(str, Enum):
    """Action risk classification (Spec 43, 44)."""

    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ResolutionMethod(str, Enum):
    """Provenance mechanism used to resolve references and entities."""

    EXPLICIT = "EXPLICIT"
    CONTEXT = "CONTEXT"
    EXACT_MATCH = "EXACT_MATCH"
    ALIAS = "ALIAS"
    FUZZY_MATCH = "FUZZY_MATCH"
    MODEL_INFERENCE = "MODEL_INFERENCE"


class AssumptionType(str, Enum):
    """Classification of assumptions made during intent extraction (Spec 51)."""

    EXPLICIT = "EXPLICIT"
    CONTEXTUAL = "CONTEXTUAL"
    INFERRED = "INFERRED"
    DEFAULT = "DEFAULT"


class MotivationCategory(str, Enum):
    """Safe, non-psychological functional motivation signals (Spec 78)."""

    EFFICIENCY = "EFFICIENCY"
    LEARNING = "LEARNING"
    COMPLETION = "COMPLETION"
    QUALITY = "QUALITY"
    SAFETY = "SAFETY"
    CONVENIENCE = "CONVENIENCE"
    TIME_SAVING = "TIME_SAVING"
    EXPLORATION = "EXPLORATION"
    CREATION = "CREATION"


class ConstraintType(str, Enum):
    """Hard non-negotiable vs soft tradeable constraint (Spec 16, 17)."""

    HARD = "HARD"
    SOFT = "SOFT"


class ConstraintCategory(str, Enum):
    """10 constraint categories (Spec 15)."""

    TIME = "TIME"
    BUDGET = "BUDGET"
    TECHNOLOGY = "TECHNOLOGY"
    LOCATION = "LOCATION"
    SCOPE = "SCOPE"
    QUALITY = "QUALITY"
    PRIVACY = "PRIVACY"
    SECURITY = "SECURITY"
    FORMAT = "FORMAT"
    DEPENDENCIES = "DEPENDENCIES"


class ConstraintPriority(str, Enum):
    """Constraint hierarchy priority ranking (Spec 19, 121)."""

    SAFETY = "SAFETY"
    POLICY = "POLICY"
    AUTHORIZATION = "AUTHORIZATION"
    EXPLICIT_USER = "EXPLICIT_USER"
    PROJECT = "PROJECT"
    PREFERENCE = "PREFERENCE"
    DEFAULT = "DEFAULT"


class PreferenceConfidence(str, Enum):
    """Confidence level of inferred or stated user preference (Spec 21)."""

    EXPLICIT = "EXPLICIT"
    STRONGLY_ESTABLISHED = "STRONGLY_ESTABLISHED"
    WEAKLY_INFERRED = "WEAKLY_INFERRED"
    UNKNOWN = "UNKNOWN"


class PreferenceScope(str, Enum):
    """Applicability boundary of user preference (Spec 22)."""

    GLOBAL = "GLOBAL"
    PROJECT = "PROJECT"
    TASK = "TASK"
    SESSION = "SESSION"
    TEMPORARY = "TEMPORARY"


class IntentErrorState(str, Enum):
    """Intent evaluation, resolution, and error states."""

    READY = "READY"
    INTENT_UNCLEAR = "INTENT_UNCLEAR"
    REFERENCE_AMBIGUOUS = "REFERENCE_AMBIGUOUS"
    TARGET_NOT_FOUND = "TARGET_NOT_FOUND"
    TARGET_UNAUTHORIZED = "TARGET_UNAUTHORIZED"
    CAPABILITY_UNAVAILABLE = "CAPABILITY_UNAVAILABLE"
    MISSING_PARAMETER = "MISSING_PARAMETER"
    CONFLICTING_CONSTRAINTS = "CONFLICTING_CONSTRAINTS"
    ACTION_NOT_ALLOWED = "ACTION_NOT_ALLOWED"
    WAITING_USER = "WAITING_USER"


# ---------------- Domain Dataclasses / Schemas ----------------


class ClarificationOption(BaseModel):
    id: str
    label: str
    description: Optional[str] = None
    value: Optional[str] = None


class AmbiguityReport(BaseModel):
    ambiguous: bool = False
    level: AmbiguityLevel = AmbiguityLevel.LOW
    candidates: List[Dict[str, Any]] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    reason: Optional[str] = None
    resolution_options: List[ClarificationOption] = Field(default_factory=list)


class IntentEntity(BaseModel):
    entity_type: str
    entity_id: Optional[str] = None
    name: str
    resolution_method: ResolutionMethod = ResolutionMethod.EXPLICIT
    confidence: float = 1.0
    scope: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IntentTarget(BaseModel):
    entity_type: str
    stable_entity_id: Optional[str] = None
    name: str
    scope: Optional[str] = None
    environment: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConstraintItem(BaseModel):
    """Individual constraint definition (Spec 15-19)."""

    name: str
    category: ConstraintCategory = ConstraintCategory.SCOPE
    constraint_type: ConstraintType = ConstraintType.HARD
    value: Any = None
    priority: int = 1
    description: str = ""


class IntentConstraints(BaseModel):
    deadline: Optional[datetime] = None
    allowed_scope: Optional[str] = None
    disallowed_scope: Optional[str] = None
    environment: Optional[str] = None
    disallowed_environments: List[str] = Field(default_factory=list)
    format: Optional[str] = None
    budget_limit: Optional[float] = None
    hard_negations: List[str] = Field(default_factory=list)
    conditions: List[str] = Field(default_factory=list)
    items: List[ConstraintItem] = Field(default_factory=list)


class CommandAttachment(BaseModel):
    type: str  # image, document, audio, screen, video
    name: str
    url: Optional[str] = None
    data_base64: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ObjectiveSchema(BaseModel):
    objective_id: str
    description: str
    target_metric: Optional[str] = None
    target_value: Optional[str] = None
    is_inferred: bool = False
    status: str = "PENDING"


class GoalSchema(BaseModel):
    """Structured Goal representing desired outcome, distinct from execution tasks (Spec 9, 10)."""

    goal_id: str
    intent_id: str
    description: str
    desired_state: Dict[str, Any] = Field(default_factory=dict)
    success_criteria: List[Dict[str, Any]] = Field(default_factory=list)
    objectives: List[ObjectiveSchema] = Field(default_factory=list)
    scope: Dict[str, Any] = Field(default_factory=dict)
    constraints: List[ConstraintItem] = Field(default_factory=list)
    priority: UrgencyLevel = UrgencyLevel.NORMAL
    deadline: Optional[datetime] = None
    owner: str = "user"
    status: GoalStatus = GoalStatus.ACTIVE
    created_at: Optional[datetime] = None


class AssumptionSchema(BaseModel):
    assumption_id: str
    statement: str
    source: AssumptionType = AssumptionType.INFERRED
    confidence: float = 0.7
    impact: str = "LOW"
    status: str = "ACTIVE"


class ClarificationRequestSchema(BaseModel):
    """Targeted, minimal question requested from user to resolve ambiguity (Spec 58-62)."""

    clarification_id: str
    intent_id: str
    question: str
    reason: str
    affected_decision: str
    options: List[str] = Field(default_factory=list)
    default_if_any: Optional[str] = None
    status: str = "PENDING"
    response: Optional[str] = None


class MotivationSignalSchema(BaseModel):
    """Safe functional motivation signal (Spec 76-80)."""

    motivation_id: str
    category: MotivationCategory
    confidence: float = 0.8
    evidence: List[str] = Field(default_factory=list)


class IntentGraphNode(BaseModel):
    id: str
    node_type: str  # INTENT, GOAL, OBJECTIVE, CONSTRAINT, TASK, OUTCOME
    label: str
    data: Dict[str, Any] = Field(default_factory=dict)


class IntentGraphEdge(BaseModel):
    source: str
    target: str
    relationship: str  # CREATES, CONSTRAINS, SATISFIES, DEPENDS_ON


class IntentGraphSchema(BaseModel):
    graph_id: str
    intent_id: str
    goal_id: Optional[str] = None
    nodes: List[IntentGraphNode] = Field(default_factory=list)
    edges: List[IntentGraphEdge] = Field(default_factory=list)


class TradeoffOption(BaseModel):
    name: str
    description: str
    pros: List[str] = Field(default_factory=list)
    cons: List[str] = Field(default_factory=list)
    estimated_cost: Optional[str] = None
    estimated_time: Optional[str] = None


class TradeoffAnalysisSchema(BaseModel):
    analysis_id: str
    conflicting_goals: List[str] = Field(default_factory=list)
    options: List[TradeoffOption] = Field(default_factory=list)
    recommended_option: Optional[str] = None
    requires_user_decision: bool = True


class CommandSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    command_id: str
    user_id: str
    session_id: Optional[str] = None
    conversation_id: Optional[str] = None
    text: str
    original_text: str
    attachments: List[CommandAttachment] = Field(default_factory=list)
    created_at: datetime
    source_interface: str = "WEB"
    project_hint: Optional[str] = None


class IntentSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    intent_id: str
    source_command_id: str
    type: IntentType
    objective: str
    entities: List[IntentEntity] = Field(default_factory=list)
    references: List[str] = Field(default_factory=list)
    target: Optional[IntentTarget] = None
    constraints: IntentConstraints = Field(default_factory=IntentConstraints)
    requested_action: Optional[str] = None
    confidence: float = 1.0
    ambiguity: AmbiguityReport = Field(default_factory=AmbiguityReport)
    risk: IntentRiskLevel = IntentRiskLevel.NORMAL
    status: str = "READY"
    next_action: Optional[str] = None
    created_at: Optional[datetime] = None


class IntentDetailedResponse(BaseModel):
    """Comprehensive Intent object honoring all Spec 2 fields."""

    intent_id: str
    source: str
    raw_input: str
    normalized_intent: str
    intent_type: IntentType
    goal: Optional[GoalSchema] = None
    objectives: List[ObjectiveSchema] = Field(default_factory=list)
    constraints: List[ConstraintItem] = Field(default_factory=list)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    entities: List[IntentEntity] = Field(default_factory=list)
    context_refs: List[str] = Field(default_factory=list)
    assumptions: List[AssumptionSchema] = Field(default_factory=list)
    ambiguity: AmbiguityReport = Field(default_factory=AmbiguityReport)
    confidence: float = 1.0
    urgency: UrgencyLevel = UrgencyLevel.NORMAL
    scope: Dict[str, Any] = Field(default_factory=dict)
    provenance: Dict[str, str] = Field(default_factory=dict)
    status: IntentStatus = IntentStatus.INTERPRETED
    created_at: str


# ---------------- API Request & Response Schemas ----------------


class CommandCreateRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Natural language command")
    session_id: Optional[str] = Field(None, description="Optional active session identifier")
    conversation_id: Optional[str] = Field(None, description="Optional conversation context identifier")
    attachments: List[CommandAttachment] = Field(default_factory=list, description="Attached media or screen context")
    source_interface: str = Field("WEB", description="Source interface: WEB, DESKTOP, VOICE, MOBILE, API")
    project_hint: Optional[str] = Field(None, description="Optional active project name or ID")
    clarification_response: Optional[str] = Field(None, description="Answer to a prior clarification question")


class CommandResolveRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Natural language command to analyze")
    session_id: Optional[str] = None
    conversation_id: Optional[str] = None
    attachments: List[CommandAttachment] = Field(default_factory=list)
    source_interface: str = "WEB"
    project_hint: Optional[str] = None


class CommandResponse(BaseModel):
    command_id: str
    intent: IntentSchema
    ambiguity: AmbiguityReport
    execution_summary: Optional[Dict[str, Any]] = None


class UserCorrectionRequest(BaseModel):
    intent_id: str
    correction_text: str = Field(..., description="'That's not what I meant' explanation")
    revised_objective: Optional[str] = None


class ClarificationAnswerRequest(BaseModel):
    clarification_id: str
    selected_option: Optional[str] = None
    freeform_answer: Optional[str] = None


class IntentRevocationRequest(BaseModel):
    intent_id: str
    reason: Optional[str] = None
