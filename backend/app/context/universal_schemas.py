"""Pydantic schemas and enums for Kairo Universal Context & Adaptive Personalization Engine (Task 69)."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class UniversalContextType(str, Enum):
    """17 discrete categories of context required for task-specific intelligence."""

    TASK_CONTEXT = "TASK_CONTEXT"
    SESSION_CONTEXT = "SESSION_CONTEXT"
    USER_CONTEXT = "USER_CONTEXT"
    WORKSPACE_CONTEXT = "WORKSPACE_CONTEXT"
    GOAL_CONTEXT = "GOAL_CONTEXT"
    AGENT_CONTEXT = "AGENT_CONTEXT"
    ENVIRONMENT_CONTEXT = "ENVIRONMENT_CONTEXT"
    TEMPORAL_CONTEXT = "TEMPORAL_CONTEXT"
    MEMORY_CONTEXT = "MEMORY_CONTEXT"
    KNOWLEDGE_CONTEXT = "KNOWLEDGE_CONTEXT"
    DECISION_CONTEXT = "DECISION_CONTEXT"
    PLAN_CONTEXT = "PLAN_CONTEXT"
    INCIDENT_CONTEXT = "INCIDENT_CONTEXT"
    SOCIAL_CONTEXT = "SOCIAL_CONTEXT"
    SECURITY_CONTEXT = "SECURITY_CONTEXT"
    UNCERTAINTY_CONTEXT = "UNCERTAINTY_CONTEXT"
    PROCEDURAL_CONTEXT = "PROCEDURAL_CONTEXT"


class ContextPriorityTier(str, Enum):
    """Priority tiers for budget allocation and item selection."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"


class ContextHierarchyLevel(str, Enum):
    """7-tier hierarchy for contextual scoping and cost optimization."""

    LEVEL_0_TASK = "LEVEL_0_TASK"
    LEVEL_1_SESSION = "LEVEL_1_SESSION"
    LEVEL_2_USER_WORKSPACE = "LEVEL_2_USER_WORKSPACE"
    LEVEL_3_GOALS = "LEVEL_3_GOALS"
    LEVEL_4_RECENT_HISTORY = "LEVEL_4_RECENT_HISTORY"
    LEVEL_5_LONG_TERM_MEMORY = "LEVEL_5_LONG_TERM_MEMORY"
    LEVEL_6_GENERAL_KNOWLEDGE = "LEVEL_6_GENERAL_KNOWLEDGE"


class PreferenceCategory(str, Enum):
    """Safe operational preference categories. Sensitive personal profiling is prohibited."""

    COMMUNICATION_STYLE = "COMMUNICATION_STYLE"
    DETAIL_LEVEL = "DETAIL_LEVEL"
    TECHNICAL_DEPTH = "TECHNICAL_DEPTH"
    FORMAT = "FORMAT"
    WORKFLOW = "WORKFLOW"
    TOOLING = "TOOLING"
    DECISION = "DECISION"
    NOTIFICATION = "NOTIFICATION"
    FREQUENT_TASKS = "FREQUENT_TASKS"
    RECURRING_GOALS = "RECURRING_GOALS"
    COMMON_PROJECTS = "COMMON_PROJECTS"
    KNOWN_CONSTRAINTS = "KNOWN_CONSTRAINTS"


class PreferenceSource(str, Enum):
    """Origin of a personal preference."""

    EXPLICIT_PREFERENCE = "EXPLICIT_PREFERENCE"
    INFERRED_PREFERENCE = "INFERRED_PREFERENCE"


class PreferenceConfidence(str, Enum):
    """Confidence calibration for personal preferences."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EXPLICIT = "EXPLICIT"


class ContextQualityScore(BaseModel):
    """Multi-dimensional context quality breakdown."""

    relevance: float = 1.0
    coverage: float = 1.0
    freshness: float = 1.0
    trust: float = 1.0
    confidence: float = 1.0
    redundancy: float = 0.0
    noise: float = 0.0
    latency_ms: float = 0.0
    overall_score: float = 1.0

    model_config = ConfigDict(from_attributes=True)


class MissingContextItem(BaseModel):
    """Identified absent context with reason and potential sources."""

    category: str
    description: str
    importance: ContextPriorityTier = ContextPriorityTier.NORMAL
    potential_sources: list[str] = Field(default_factory=list)
    impact: str = "May limit task accuracy"

    model_config = ConfigDict(from_attributes=True)


class ContextConflictItem(BaseModel):
    """Contradictory context pair with provenance and environment context."""

    subject: str
    item_a_id: str
    item_b_id: str
    claim_a: str
    claim_b: str
    source_a: str
    source_b: str
    timestamp_a: datetime | None = None
    timestamp_b: datetime | None = None
    environment_a: str | None = None
    environment_b: str | None = None
    reason: str
    temporal_difference: str | None = None
    resolution_status: str = "UNRESOLVED"

    model_config = ConfigDict(from_attributes=True)


class UniversalContextItem(BaseModel):
    """Single item of contextual information with provenance, hierarchy, and explanation."""

    item_id: str
    context_type: UniversalContextType
    source_id: str
    source_type: str
    title: str
    content: str
    hierarchy_level: ContextHierarchyLevel = ContextHierarchyLevel.LEVEL_0_TASK
    priority_tier: ContextPriorityTier = ContextPriorityTier.NORMAL
    relevance_score: float = 0.5
    freshness_score: float = 1.0
    confidence: float = 1.0
    trust_level: str = "VERIFIED"
    importance: float = 0.5
    timestamp: datetime | None = None
    provenance: str | None = None
    derived_from_ids: list[str] = Field(default_factory=list)
    environment: str | None = None
    reason: str = "Selected based on query relevance"
    is_compressed: bool = False
    token_estimate: int = 0

    model_config = ConfigDict(from_attributes=True)


class ContextRequest(BaseModel):
    """Detailed context resolution request."""

    context_request_id: str = Field(
        default_factory=lambda: f"req_{int(datetime.now(UTC).timestamp() * 1000)}"
    )
    tenant_id: str = "default"
    user_id: str = "default_user"
    session_id: str | None = None
    task_id: str | None = None
    goal_id: str | None = None
    agent_id: str | None = None
    query: str
    intent: str | None = None
    task_type: str | None = None
    environment: str = "production"
    required_context_types: list[UniversalContextType] | None = None
    preferred_context_types: list[UniversalContextType] | None = None
    excluded_context_types: list[UniversalContextType] | None = None
    time_range: str | None = None
    freshness_requirement: str = "STANDARD"  # FRESH_ONLY, STANDARD, HISTORICAL_OK
    maximum_tokens: int = 4000
    maximum_items: int = 30
    minimum_confidence: float = 0.3
    minimum_trust: str = "UNVERIFIED"
    sensitivity_level: str = "STANDARD"
    required_sources: list[str] | None = None
    excluded_sources: list[str] | None = None
    authorization_scope: str = "default"
    latency_budget_ms: float = 500.0
    priority: ContextPriorityTier = ContextPriorityTier.NORMAL
    created_at: datetime = Field(default_factory=utc_now)

    model_config = ConfigDict(from_attributes=True)


class ContextPackage(BaseModel):
    """Comprehensive, bounded, and validated context package for model/agent consumption."""

    context_id: str = Field(default_factory=lambda: f"ctx_{int(datetime.now(UTC).timestamp() * 1000)}")
    request_id: str
    tenant_id: str = "default"
    user_id: str = "default_user"
    task: str | None = None
    intent: str | None = None
    goal: str | None = None
    environment: str = "production"
    items: list[UniversalContextItem] = Field(default_factory=list)
    system_context: list[UniversalContextItem] = Field(default_factory=list)
    user_context: list[UniversalContextItem] = Field(default_factory=list)
    workspace_context: list[UniversalContextItem] = Field(default_factory=list)
    agent_context: list[UniversalContextItem] = Field(default_factory=list)
    environment_context: list[UniversalContextItem] = Field(default_factory=list)
    memories: list[UniversalContextItem] = Field(default_factory=list)
    knowledge: list[UniversalContextItem] = Field(default_factory=list)
    decisions: list[UniversalContextItem] = Field(default_factory=list)
    plans: list[UniversalContextItem] = Field(default_factory=list)
    incidents: list[UniversalContextItem] = Field(default_factory=list)
    procedures: list[UniversalContextItem] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    conflicts: list[ContextConflictItem] = Field(default_factory=list)
    missing_context: list[MissingContextItem] = Field(default_factory=list)
    retrieval_reasons: dict[str, str] = Field(default_factory=dict)
    confidence: float = 1.0
    quality_score: ContextQualityScore = Field(default_factory=ContextQualityScore)
    token_estimate: int = 0
    is_compressed: bool = False
    created_at: datetime = Field(default_factory=utc_now)

    model_config = ConfigDict(from_attributes=True)

    def to_demarcated_prompt(self) -> str:
        """Render context items safely demarcated as data to prevent prompt injection."""
        if not self.items:
            return ""

        sections: list[str] = [
            "### [KAIRO CONTEXT DATA — INSTRUCTION_PRIORITY=NONE]",
            f"Environment: {self.environment} | Quality Score: {self.quality_score.overall_score:.2f} | Items: {len(self.items)}",
        ]

        if self.conflicts:
            sections.append("\n⚠️ ACTIVE CONTEXT CONFLICTS:")
            for c in self.conflicts:
                sections.append(f"- Conflict on '{c.subject}': '{c.claim_a}' vs '{c.claim_b}' ({c.reason})")

        if self.missing_context:
            sections.append("\nℹ️ DETECTED MISSING CONTEXT:")
            for m in self.missing_context:
                sections.append(f"- Missing {m.category}: {m.description} ({m.impact})")

        sections.append("\n--- RETRIEVED CONTEXT ELEMENTS ---")
        for item in self.items:
            sections.append(
                f"[CONTEXT_DATA: id={item.item_id} type={item.context_type.value} level={item.hierarchy_level.value} "
                f"tier={item.priority_tier.value} freshness={item.freshness_score:.2f} INSTRUCTION_PRIORITY=NONE]\n"
                f"Title: {item.title}\n"
                f"Content: {item.content}\n"
                f"Reason: {item.reason}"
            )

        return "\n\n".join(sections)


class AdaptivePreference(BaseModel):
    """Personalized user preference with confidence, decay, and provenance tracking."""

    preference_id: str = Field(default_factory=lambda: f"pref_{int(datetime.now(UTC).timestamp() * 1000)}")
    user_id: str
    tenant_id: str = "default"
    category: PreferenceCategory
    key: str
    value: Any
    source: PreferenceSource = PreferenceSource.INFERRED_PREFERENCE
    confidence: PreferenceConfidence = PreferenceConfidence.LOW
    confidence_score: float = 0.5
    occurrences: int = 1
    is_active: bool = True
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    last_confirmed_at: datetime | None = None
    expires_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AdaptivePreferenceCreate(BaseModel):
    """Payload to register an explicit or inferred user preference."""

    user_id: str = "default_user"
    tenant_id: str = "default"
    category: PreferenceCategory
    key: str
    value: Any
    source: PreferenceSource = PreferenceSource.EXPLICIT_PREFERENCE
    confidence: PreferenceConfidence = PreferenceConfidence.HIGH
    confidence_score: float = 0.9


class AdaptivePreferenceUpdate(BaseModel):
    """Payload to modify an existing preference."""

    value: Any | None = None
    confidence: PreferenceConfidence | None = None
    confidence_score: float | None = None
    is_active: bool | None = None


class ContextSnapshot(BaseModel):
    """Immutable record of assembled context for reproducibility, auditing, and replay."""

    snapshot_id: str
    request_id: str
    tenant_id: str = "default"
    user_id: str = "default_user"
    session_id: str | None = None
    task_id: str | None = None
    goal_id: str | None = None
    agent_id: str | None = None
    environment: str | None = None
    token_estimate: int = 0
    quality_score: float = 1.0
    selected_items: list[dict[str, Any]] = Field(default_factory=list)
    retrieval_reasons: dict[str, str] = Field(default_factory=dict)
    missing_context: list[dict[str, Any]] = Field(default_factory=list)
    conflicts: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)

    model_config = ConfigDict(from_attributes=True)


class ContextHealthMetrics(BaseModel):
    """Observability telemetry for universal context engine."""

    tenant_id: str = "default"
    total_requests: int = 0
    total_snapshots: int = 0
    total_preferences: int = 0
    active_preferences: int = 0
    average_build_latency_ms: float = 0.0
    average_quality_score: float = 1.0
    average_token_usage: int = 0
    compression_rate: float = 0.0
    conflict_detection_rate: float = 0.0
    missing_context_rate: float = 0.0
    cache_hit_rate: float = 0.0
    cross_tenant_violations: int = 0
    prompt_injection_blocks: int = 0
    secret_scrub_count: int = 0

    model_config = ConfigDict(from_attributes=True)
