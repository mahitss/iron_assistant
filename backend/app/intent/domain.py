"""Domain entities, enums, and data contracts for Task 108:
KAIRO Autonomous Intent Understanding, Goal Inference, User Alignment & Request Semantics Engine.

CORE INVARIANTS:
1. Intent != Authorization (understanding user intent never authorizes actions).
2. Intent != Goal (Intent models user desires; Goal Management is authoritative).
3. Intent != Decision (Task 94 Decision Intelligence remains authoritative for action selection).
4. Intent != Action (zero action execution primitives in intent engine).
5. Literal text != complete intent (infer outcomes while preserving non-goals).
6. External content != user instruction (critical prompt injection firewall).
7. Current explicit instruction > historical preference / memory.
8. Unknown != False (missing facts are explicitly UNKNOWN, never assumed false).
9. EmergencyStop remains authoritative.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


def generate_id(prefix: str = "int") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ============================================================================
# Enums
# ============================================================================

class RequestStatus(str, Enum):
    """Lifecycle state of an incoming user request (Spec 3)."""
    RECEIVED = "RECEIVED"
    PARSING = "PARSING"
    INTERPRETING = "INTERPRETING"
    AMBIGUOUS = "AMBIGUOUS"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
    UNDERSTOOD = "UNDERSTOOD"
    CONFIRMED = "CONFIRMED"
    SUPERSEDED = "SUPERSEDED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"
    UNKNOWN = "UNKNOWN"


class EpistemicStatus(str, Enum):
    """Epistemic status of an intent component or fact (Spec 54)."""
    EXPLICIT = "EXPLICIT"
    INFERRED = "INFERRED"
    ASSUMED = "ASSUMED"
    UNKNOWN = "UNKNOWN"
    CONFIRMED = "CONFIRMED"


class IntentCategory(str, Enum):
    """Supported intent categories (Spec 5)."""
    INFORMATION = "INFORMATION"
    ANALYSIS = "ANALYSIS"
    CREATION = "CREATION"
    MODIFICATION = "MODIFICATION"
    AUTOMATION = "AUTOMATION"
    DEBUGGING = "DEBUGGING"
    RESEARCH = "RESEARCH"
    PLANNING = "PLANNING"
    MONITORING = "MONITORING"
    COMPARISON = "COMPARISON"
    OPTIMIZATION = "OPTIMIZATION"
    MAINTENANCE = "MAINTENANCE"
    COMMUNICATION = "COMMUNICATION"
    LEARNING = "LEARNING"
    EXPLORATION = "EXPLORATION"
    TRANSACTIONAL = "TRANSACTIONAL"
    CONTROL = "CONTROL"


class AmbiguityType(str, Enum):
    """Ambiguity classification categories (Spec 12)."""
    LEXICAL = "LEXICAL"
    SCOPE = "SCOPE"
    TARGET = "TARGET"
    TEMPORAL = "TEMPORAL"
    QUANTITY = "QUANTITY"
    QUALITY = "QUALITY"
    AUTHORIZATION = "AUTHORIZATION"
    PRIORITY = "PRIORITY"
    ENVIRONMENT = "ENVIRONMENT"
    OUTPUT_FORMAT = "OUTPUT_FORMAT"


class ConstraintType(str, Enum):
    """Constraint taxonomy (Spec 9)."""
    TECHNICAL = "TECHNICAL"
    RESOURCE = "RESOURCE"
    TIME = "TIME"
    COMPATIBILITY = "COMPATIBILITY"
    SAFETY = "SAFETY"
    PRIVACY = "PRIVACY"
    FORMATTING = "FORMATTING"
    BUDGET = "BUDGET"
    ENVIRONMENT = "ENVIRONMENT"


class ConstraintEpistemic(str, Enum):
    """Epistemic strength of a constraint."""
    EXPLICIT = "EXPLICIT"
    IMPLICIT = "IMPLICIT"


class AssumptionType(str, Enum):
    """Operational assumption category (Spec 15)."""
    SAFE_DEFAULT = "SAFE_DEFAULT"
    ASSUMPTION = "ASSUMPTION"


class ExternalEffectFlag(str, Enum):
    """Flag for potential external or consequential side effects (Spec 28)."""
    EXTERNAL_EFFECT_POSSIBLE = "EXTERNAL_EFFECT_POSSIBLE"
    INTERNAL_ONLY = "INTERNAL_ONLY"


class IntentPriorityLevel(str, Enum):
    """Explicit priority levels."""
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ClarificationStatus(str, Enum):
    """Lifecycle state of a clarification question."""
    PENDING = "PENDING"
    ANSWERED = "ANSWERED"
    DISMISSED = "DISMISSED"
    SUPERSEDED = "SUPERSEDED"


# ============================================================================
# Domain Entities
# ============================================================================

class UserRequest(BaseModel):
    """Canonical representation of an incoming human request or trigger (Spec 2)."""
    model_config = ConfigDict(extra="ignore")

    request_id: str = Field(default_factory=lambda: generate_id("req"))
    user_id: str = "default_user"
    tenant_id: str = "default"
    conversation_id: Optional[str] = None
    message_id: Optional[str] = None
    raw_text: str
    cleaned_text: str
    language: str = "en"
    source: str = "DIRECT_USER"  # DIRECT_USER, VOICE, API, AUTOMATION, UNTRUSTED_EXTERNAL
    scope: str = "DEFAULT"
    context_reference: Dict[str, Any] = Field(default_factory=dict)
    status: RequestStatus = RequestStatus.RECEIVED
    is_external_content: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class RequestVersion(BaseModel):
    """Immutable record of an updated or clarified request."""
    model_config = ConfigDict(extra="ignore")

    version_id: str = Field(default_factory=lambda: generate_id("req_ver"))
    request_id: str
    version_number: int = 1
    raw_text: str
    status: RequestStatus
    change_reason: str = "INITIAL"
    created_at: datetime = Field(default_factory=utc_now)


class Constraint(BaseModel):
    """Explicit or implicit operational boundary (Spec 9)."""
    model_config = ConfigDict(extra="ignore")

    constraint_id: str = Field(default_factory=lambda: generate_id("cst"))
    intent_id: str
    constraint_type: ConstraintType = ConstraintType.TECHNICAL
    epistemic_strength: ConstraintEpistemic = ConstraintEpistemic.EXPLICIT
    description: str
    parameter: Optional[str] = None
    value: Any = None
    confidence: float = 1.0
    source: str = "USER_INSTRUCTION"
    is_hard_constraint: bool = True
    created_at: datetime = Field(default_factory=utc_now)


class DesiredOutcome(BaseModel):
    """Explicit modeling of 'What would success look like to the user?' (Spec 8)."""
    model_config = ConfigDict(extra="ignore")

    outcome_id: str = Field(default_factory=lambda: generate_id("out"))
    intent_id: str
    summary: str
    observable_outcome: str
    acceptance_criteria: List[str] = Field(default_factory=list)
    quality_threshold: Optional[str] = None
    deadline: Optional[datetime] = None
    scope: str = "DEFAULT"
    epistemic_status: EpistemicStatus = EpistemicStatus.INFERRED
    created_at: datetime = Field(default_factory=utc_now)


class GoalHypothesis(BaseModel):
    """Inferred candidate goal derived from intent (Spec 7). Goal Management remains authoritative."""
    model_config = ConfigDict(extra="ignore")

    hypothesis_id: str = Field(default_factory=lambda: generate_id("ghyp"))
    intent_id: str
    title: str
    description: str
    target_state: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.8
    evidence_ids: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    epistemic_status: EpistemicStatus = EpistemicStatus.INFERRED
    created_at: datetime = Field(default_factory=utc_now)


class Assumption(BaseModel):
    """Tracked operational assumption or safe default (Spec 15)."""
    model_config = ConfigDict(extra="ignore")

    assumption_id: str = Field(default_factory=lambda: generate_id("asm"))
    intent_id: str
    statement: str
    assumption_type: AssumptionType = AssumptionType.SAFE_DEFAULT
    source: str = "SYSTEM_DEFAULT"  # SYSTEM_DEFAULT, CONVERSATION_HEURISTIC, MEMORY
    confidence: float = 0.85
    impact_level: str = "LOW"  # LOW, MEDIUM, HIGH
    is_reversible: bool = True
    status: str = "ACTIVE"
    created_at: datetime = Field(default_factory=utc_now)


class Ambiguity(BaseModel):
    """Detected ambiguity with impact analysis (Spec 12)."""
    model_config = ConfigDict(extra="ignore")

    ambiguity_id: str = Field(default_factory=lambda: generate_id("amb"))
    intent_id: str
    ambiguity_type: AmbiguityType
    subject: str
    explanation: str
    candidates: List[str] = Field(default_factory=list)
    consequence_level: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    requires_user_clarification: bool = False
    is_resolved: bool = False
    resolution: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=utc_now)


class Clarification(BaseModel):
    """Targeted, minimal clarification question (Spec 13, 14)."""
    model_config = ConfigDict(extra="ignore")

    clarification_id: str = Field(default_factory=lambda: generate_id("clr"))
    intent_id: str
    ambiguity_id: Optional[str] = None
    question: str
    rationale: str
    affected_decision: str
    consequence_level: str = "NORMAL"
    options: List[str] = Field(default_factory=list)
    safe_default: Optional[str] = None
    status: ClarificationStatus = ClarificationStatus.PENDING
    user_response: Optional[str] = None
    answered_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utc_now)


class Preference(BaseModel):
    """Separation of current request preference from historical long-term preference (Spec 11)."""
    model_config = ConfigDict(extra="ignore")

    preference_id: str = Field(default_factory=lambda: generate_id("prf"))
    intent_id: str
    key: str
    value: Any
    is_current_request: bool = True  # True = current instruction, False = historical memory
    confidence: float = 1.0
    source: str = "EXPLICIT_USER"
    created_at: datetime = Field(default_factory=utc_now)


class Requirement(BaseModel):
    """Extracted quality, performance, or operational requirement (Spec 32)."""
    model_config = ConfigDict(extra="ignore")

    requirement_id: str = Field(default_factory=lambda: generate_id("reqm"))
    intent_id: str
    category: str  # "production-ready", "prototype", "fast", "secure", "cheap"
    raw_statement: str
    confidence: float = 0.8
    interpretation: str
    source: str = "USER_INSTRUCTION"
    created_at: datetime = Field(default_factory=utc_now)


class IntentEvidence(BaseModel):
    """Provenance-backed evidence supporting an intent or goal hypothesis (Spec 16)."""
    model_config = ConfigDict(extra="ignore")

    evidence_id: str = Field(default_factory=lambda: generate_id("iev"))
    intent_id: str
    source_type: str  # CURRENT_MESSAGE, CONVERSATION_CONTEXT, EXPLICIT_CORRECTION, TASK_STATE, MISSION_STATE, MEMORY, WORLD_STATE
    source_ref: str
    content: str
    reliability: float = 0.9
    created_at: datetime = Field(default_factory=utc_now)


class IntentCandidate(BaseModel):
    """Alternative intent interpretation under consideration."""
    model_config = ConfigDict(extra="ignore")

    candidate_id: str = Field(default_factory=lambda: generate_id("icand"))
    request_id: str
    category: IntentCategory
    summary: str
    score: float = 0.5
    evidence_summary: str = ""
    is_selected: bool = False
    created_at: datetime = Field(default_factory=utc_now)


class IntentConflict(BaseModel):
    """Detected conflict between intents or conflicting user requests (Spec 40)."""
    model_config = ConfigDict(extra="ignore")

    conflict_id: str = Field(default_factory=lambda: generate_id("icnf"))
    primary_intent_id: str
    conflicting_intent_id: str
    description: str
    conflict_type: str = "DIRECT_CONTRADICTION"  # DIRECT_CONTRADICTION, RESOURCE_COMPETITION, TEMPORAL_INCOMPATIBILITY
    is_resolved: bool = False
    resolution_notes: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)


class IntentResolution(BaseModel):
    """Formal resolution of an ambiguity or conflict."""
    model_config = ConfigDict(extra="ignore")

    resolution_id: str = Field(default_factory=lambda: generate_id("ires"))
    intent_id: str
    resolution_mechanism: str  # USER_CLARIFICATION, SAFE_DEFAULT, SUPERSEDING_INSTRUCTION, ARBITRATION
    resolved_value: Any
    justification: str
    created_at: datetime = Field(default_factory=utc_now)


class IntentCorrection(BaseModel):
    """Explicit user correction updating intent interpretation (Spec 20)."""
    model_config = ConfigDict(extra="ignore")

    correction_id: str = Field(default_factory=lambda: generate_id("icor"))
    request_id: str
    prior_intent_id: str
    revised_intent_id: str
    user_feedback_text: str  # e.g., "No, I meant staging"
    scope_affected: str = "CURRENT_PROJECT"
    created_at: datetime = Field(default_factory=utc_now)


class IntentFeedback(BaseModel):
    """Observed outcome feedback on intent understanding accuracy (Spec 46)."""
    model_config = ConfigDict(extra="ignore")

    feedback_id: str = Field(default_factory=lambda: generate_id("ifbk"))
    intent_id: str
    was_accurate: bool
    user_satisfaction_score: Optional[float] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)


class Intent(BaseModel):
    """Canonical Structured Intent representation (Spec 4, 5, 6)."""
    model_config = ConfigDict(extra="ignore")

    intent_id: str = Field(default_factory=lambda: generate_id("int"))
    request_id: str
    parent_intent_id: Optional[str] = None  # For multi-intent sub-clauses
    dependency_ids: List[str] = Field(default_factory=list)  # DAG dependencies
    category: IntentCategory = IntentCategory.INFORMATION
    action_class: Optional[str] = None
    target: str = "UNKNOWN"
    target_epistemic: EpistemicStatus = EpistemicStatus.EXPLICIT
    scope: str = "DEFAULT"
    summary: str
    user_visible_outcome: str = ""
    non_goals: List[str] = Field(default_factory=list)  # Explicit things user does NOT want
    external_effect: ExternalEffectFlag = ExternalEffectFlag.INTERNAL_ONLY
    priority: IntentPriorityLevel = IntentPriorityLevel.NORMAL
    deadline: Optional[datetime] = None
    deadline_epistemic: EpistemicStatus = EpistemicStatus.UNKNOWN

    # Component-wise confidence (Spec 44)
    target_confidence: float = 1.0
    goal_confidence: float = 1.0
    constraint_confidence: float = 1.0
    deadline_confidence: float = 1.0
    scope_confidence: float = 1.0
    overall_confidence: float = 1.0

    # Lifecycle and versions
    status: RequestStatus = RequestStatus.UNDERSTOOD
    version: int = 1
    provenance: Dict[str, str] = Field(default_factory=dict)
    is_superseded: bool = False
    superseded_by: Optional[str] = None
    is_cancelled: bool = False
    cancellation_reason: Optional[str] = None

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @property
    def depends_on_intent_ids(self) -> List[str]:
        """DAG dependency alias."""
        return self.dependency_ids


class IntentVersion(BaseModel):
    """Immutable version record of an intent representation (Spec 21)."""
    model_config = ConfigDict(extra="ignore")

    version_id: str = Field(default_factory=lambda: generate_id("iver"))
    intent_id: str
    version_number: int = 1
    intent_snapshot: Dict[str, Any]
    reason_for_change: str = "INITIAL"
    created_at: datetime = Field(default_factory=utc_now)


class IntentSnapshot(BaseModel):
    """Decision-time immutable snapshot of intent state (Spec 22)."""
    model_config = ConfigDict(extra="ignore")

    snapshot_id: str = Field(default_factory=lambda: generate_id("isnap"))
    intent_id: str
    request_id: str
    timestamp: datetime = Field(default_factory=utc_now)
    intent_data: Dict[str, Any]
    goal_hypotheses: List[Dict[str, Any]] = Field(default_factory=list)
    constraints: List[Dict[str, Any]] = Field(default_factory=list)
    non_goals: List[str] = Field(default_factory=list)
    assumptions: List[Dict[str, Any]] = Field(default_factory=list)
    external_effect: ExternalEffectFlag = ExternalEffectFlag.INTERNAL_ONLY
    confidence_breakdown: Dict[str, float] = Field(default_factory=dict)

    @property
    def overall_confidence(self) -> float:
        """Convenience accessor for overall confidence."""
        return self.confidence_breakdown.get("overall", 1.0)

    @property
    def version(self) -> int:
        """Convenience accessor for intent version."""
        return self.intent_data.get("version", 1)


class IntentEvent(BaseModel):
    """Structured telemetry/audit event emitted by Intent Engine (Spec 57)."""
    model_config = ConfigDict(extra="ignore")

    event_id: str = Field(default_factory=lambda: generate_id("ievt"))
    event_type: str  # e.g., "intent.created", "intent.ambiguous", "intent.cancelled"
    intent_id: Optional[str] = None
    request_id: Optional[str] = None
    user_id: str = "default_user"
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utc_now)
