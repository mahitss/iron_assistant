"""Pydantic schemas and enums for Kairo Unified Command, Intent, and Control Layer (Task 35)."""

from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class IntentType(str, Enum):
    """Supported structured intent categories (Spec 4)."""
    QUESTION = "QUESTION"
    REQUEST = "REQUEST"
    TASK = "TASK"
    SEARCH = "SEARCH"
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    CONTROL = "CONTROL"
    NAVIGATE = "NAVIGATE"
    ANALYZE = "ANALYZE"
    SUMMARIZE = "SUMMARIZE"
    COMPARE = "COMPARE"
    EXPLAIN = "EXPLAIN"
    AUTOMATE = "AUTOMATE"
    REMIND = "REMIND"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    CANCEL = "CANCEL"
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    RETRY = "RETRY"


class AmbiguityLevel(str, Enum):
    """Ambiguity severity classification (Spec 40)."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IntentRiskLevel(str, Enum):
    """Action risk classification (Spec 38)."""
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ResolutionMethod(str, Enum):
    """Provenance mechanism used to resolve references and entities (Spec 73)."""
    EXPLICIT = "EXPLICIT"
    CONTEXT = "CONTEXT"
    EXACT_MATCH = "EXACT_MATCH"
    ALIAS = "ALIAS"
    FUZZY_MATCH = "FUZZY_MATCH"
    MODEL_INFERENCE = "MODEL_INFERENCE"


class IntentErrorState(str, Enum):
    """Intent evaluation, resolution, and error states (Spec 121)."""
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


class ClarificationOption(BaseModel):
    """Interactive option presented to the user when resolving ambiguity (Spec 45, 46)."""
    id: str
    label: str
    description: str | None = None
    value: str | None = None


class AmbiguityReport(BaseModel):
    """Structured report on candidate ambiguity and missing information (Spec 39)."""
    ambiguous: bool = False
    level: AmbiguityLevel = AmbiguityLevel.LOW
    candidates: list[dict[str, Any]] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    reason: str | None = None
    resolution_options: list[ClarificationOption] = Field(default_factory=list)


class IntentEntity(BaseModel):
    """Resolved entity reference linked to a system or project resource (Spec 24-27)."""
    entity_type: str
    entity_id: str | None = None
    name: str
    resolution_method: ResolutionMethod = ResolutionMethod.EXPLICIT
    confidence: float = 1.0
    scope: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IntentTarget(BaseModel):
    """Action target with stable entity ID and scope (Spec 29)."""
    entity_type: str
    stable_entity_id: str | None = None
    name: str
    scope: str | None = None
    environment: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IntentConstraints(BaseModel):
    """Extracted execution constraints, negations, conditions, and budgets (Spec 104-110)."""
    deadline: datetime | None = None
    allowed_scope: str | None = None
    disallowed_scope: str | None = None
    environment: str | None = None
    disallowed_environments: list[str] = Field(default_factory=list)
    format: str | None = None
    budget_limit: float | None = None
    hard_negations: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)


class CommandAttachment(BaseModel):
    """Multimodal attachment accompanying command (Spec 9, 10)."""
    type: str  # image, document, audio, screen, video
    name: str
    url: str | None = None
    data_base64: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CommandSchema(BaseModel):
    """Normalized Command object (Spec 2)."""
    model_config = ConfigDict(from_attributes=True)

    command_id: str
    user_id: str
    session_id: str | None = None
    conversation_id: str | None = None
    text: str
    original_text: str
    attachments: list[CommandAttachment] = Field(default_factory=list)
    created_at: datetime
    source_interface: str = "WEB"
    project_hint: str | None = None


class IntentSchema(BaseModel):
    """Structured Intent object (Spec 3)."""
    model_config = ConfigDict(from_attributes=True)

    intent_id: str
    source_command_id: str
    type: IntentType
    objective: str
    entities: list[IntentEntity] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    target: IntentTarget | None = None
    constraints: IntentConstraints = Field(default_factory=IntentConstraints)
    requested_action: str | None = None
    confidence: float = 1.0
    ambiguity: AmbiguityReport = Field(default_factory=AmbiguityReport)
    risk: IntentRiskLevel = IntentRiskLevel.NORMAL
    status: str = "READY"
    next_action: str | None = None
    created_at: datetime | None = None


# ---------------- API Request & Response Schemas ----------------


class CommandCreateRequest(BaseModel):
    """Request payload to submit a natural-language command (Spec 122)."""
    text: str = Field(..., min_length=1, description="Natural language command")
    session_id: str | None = Field(None, description="Optional active session identifier")
    conversation_id: str | None = Field(None, description="Optional conversation context identifier")
    attachments: list[CommandAttachment] = Field(default_factory=list, description="Attached media or screen context")
    source_interface: str = Field("WEB", description="Source interface: WEB, DESKTOP, VOICE, MOBILE, API")
    project_hint: str | None = Field(None, description="Optional active project name or ID")
    clarification_response: str | None = Field(None, description="Answer to a prior clarification question")


class CommandResolveRequest(BaseModel):
    """Request payload to resolve an intent without executing (Spec 122, 123)."""
    text: str = Field(..., min_length=1, description="Natural language command to analyze")
    session_id: str | None = None
    conversation_id: str | None = None
    attachments: list[CommandAttachment] = Field(default_factory=list)
    source_interface: str = "WEB"
    project_hint: str | None = None


class CommandResponse(BaseModel):
    """Response containing parsed command, structured intent, and execution/clarification state (Spec 122)."""
    command_id: str
    intent: IntentSchema
    ambiguity: AmbiguityReport
    execution_summary: dict[str, Any] | None = None
