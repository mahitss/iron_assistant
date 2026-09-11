"""Domain schemas for Kairo Autonomous Attention & Cognitive Resource Allocation Engine (Task 70).

Enforces:
- Attention != Priority != Action
- 12-state attention lifecycle
- Independent dimensions (importance, urgency, risk, novelty, uncertainty, goal alignment)
- Cognitive resource budgeting (reasoning capacity, tool quota, agent slots, context budget)
- Preemption decisions with context preservation
- Fairness aging and anti-thrashing hysteresis
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class AttentionState(StrEnum):
    """Explicit 12-state attention lifecycle."""

    UNSEEN = "UNSEEN"
    OBSERVED = "OBSERVED"
    QUEUED = "QUEUED"
    ATTENDING = "ATTENDING"
    MONITORING = "MONITORING"
    DEFERRED = "DEFERRED"
    DELEGATED = "DELEGATED"
    PAUSED = "PAUSED"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"
    EXPIRED = "EXPIRED"
    BLOCKED = "BLOCKED"


class AttentionThreshold(StrEnum):
    """Granular thresholds determining scheduling and interrupt eligibility."""

    IGNORE = "IGNORE"  # < 0.20
    LOW = "LOW"  # 0.20 - 0.39
    NORMAL = "NORMAL"  # 0.40 - 0.69
    HIGH = "HIGH"  # 0.70 - 0.84
    CRITICAL = "CRITICAL"  # >= 0.85


class AttentionMode(StrEnum):
    """System-wide operational focus mode."""

    FOCUS_MODE = "FOCUS_MODE"  # Dampens non-critical interrupts
    NORMAL_MODE = "NORMAL_MODE"  # Standard dynamic scheduling
    EMERGENCY_MODE = "EMERGENCY_MODE"  # High-urgency priority overrides


class NotificationPriority(StrEnum):
    """Human attention resource consumption tier."""

    SILENT = "SILENT"
    LOG = "LOG"
    DIGEST = "DIGEST"
    NOTIFY = "NOTIFY"
    URGENT_NOTIFY = "URGENT_NOTIFY"


class AttentionScoreBreakdown(BaseModel):
    """Explainable factor attribution for deterministic attention scoring."""

    importance: float = Field(default=0.0, ge=0.0, le=1.0)
    urgency: float = Field(default=0.0, ge=0.0, le=1.0)
    risk: float = Field(default=0.0, ge=0.0, le=1.0)
    goal_alignment: float = Field(default=0.0, ge=0.0, le=1.0)
    deadline_pressure: float = Field(default=0.0, ge=0.0, le=1.0)
    dependency_impact: float = Field(default=0.0, ge=0.0, le=1.0)
    novelty: float = Field(default=0.0, ge=0.0, le=1.0)
    uncertainty: float = Field(default=0.0, ge=0.0, le=1.0)
    change_magnitude: float = Field(default=0.0, ge=0.0, le=1.0)

    # Penalties
    resource_cost_penalty: float = Field(default=0.0, ge=0.0, le=1.0)
    redundancy_penalty: float = Field(default=0.0, ge=0.0, le=1.0)
    staleness_penalty: float = Field(default=0.0, ge=0.0, le=1.0)

    # Composite & Explainability
    composite_score: float = Field(default=0.0, ge=0.0, le=1.0)
    contributing_factors: list[str] = Field(default_factory=list)
    explanation: str = Field(default="")


class CognitiveResourceBudget(BaseModel):
    """Real-time cognitive resource capacity & allocation model."""

    reasoning_capacity_pct: float = Field(default=100.0, ge=0.0, le=100.0)
    active_tool_calls: int = Field(default=0, ge=0)
    max_tool_calls: int = Field(default=10, ge=1)
    active_agent_slots: int = Field(default=0, ge=0)
    max_agent_slots: int = Field(default=5, ge=1)
    compute_budget_pct: float = Field(default=100.0, ge=0.0, le=100.0)
    context_token_budget: int = Field(default=128000, ge=1000)
    context_tokens_used: int = Field(default=0, ge=0)
    human_attention_slots: int = Field(default=1, ge=0)
    human_attention_used: int = Field(default=0, ge=0)
    execution_slots_used: int = Field(default=0, ge=0)
    max_execution_slots: int = Field(default=4, ge=1)

    @property
    def has_reasoning_capacity(self) -> bool:
        return self.reasoning_capacity_pct > 15.0

    @property
    def available_agent_slots(self) -> int:
        return max(0, self.max_agent_slots - self.active_agent_slots)

    @property
    def available_tool_slots(self) -> int:
        return max(0, self.max_tool_calls - self.active_tool_calls)


class PreemptionDecision(BaseModel):
    """Audit and execution decision for preempting active attention focus."""

    should_interrupt: bool
    incoming_id: str
    current_id: str | None = None
    incoming_score: float = 0.0
    current_score: float = 0.0
    urgency_delta: float = 0.0
    interrupt_cost: float = 0.0
    reason: str
    state_preserved: bool = False
    snapshot_id: str | None = None


class AttentionCandidate(BaseModel):
    """First-class Attention Candidate domain model."""

    attention_id: str = Field(default_factory=lambda: f"attn-{uuid4().hex[:12]}")
    source_type: str = Field(default="event")  # incident, goal, mission, event, prediction, task
    source_id: str = Field(default_factory=lambda: f"src-{uuid4().hex[:8]}")
    tenant_id: str = Field(default="default")
    workspace_id: str = Field(default="default")
    event_type: str = Field(default="general")
    title: str
    description: str = Field(default="")

    # Independent Dimensions
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    urgency: float = Field(default=0.5, ge=0.0, le=1.0)
    severity: str = Field(default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    risk: float = Field(default=0.3, ge=0.0, le=1.0)
    relevance: float = Field(default=0.5, ge=0.0, le=1.0)
    novelty: float = Field(default=0.0, ge=0.0, le=1.0)
    uncertainty: float = Field(default=0.2, ge=0.0, le=1.0)
    change_magnitude: float = Field(default=0.0, ge=0.0, le=1.0)
    goal_alignment: float = Field(default=0.5, ge=0.0, le=1.0)
    deadline_pressure: float = Field(default=0.0, ge=0.0, le=1.0)
    dependency_impact: float = Field(default=0.0, ge=0.0, le=1.0)

    # Subsystem Cross-References
    goal_refs: list[str] = Field(default_factory=list)
    mission_refs: list[str] = Field(default_factory=list)
    task_refs: list[str] = Field(default_factory=list)
    incident_refs: list[str] = Field(default_factory=list)
    decision_refs: list[str] = Field(default_factory=list)

    deadline: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    observed_at: datetime = Field(default_factory=utc_now)
    last_updated_at: datetime = Field(default_factory=utc_now)

    # Estimates & Capabilities
    estimated_effort: float = Field(default=1.0, ge=0.1)
    estimated_duration_sec: int = Field(default=300, ge=1)
    required_capabilities: list[str] = Field(default_factory=list)
    required_agents: list[str] = Field(default_factory=list)
    required_tools: list[str] = Field(default_factory=list)

    # Lifecycle & Scoring State
    current_state: AttentionState = Field(default=AttentionState.UNSEEN)
    attention_score: float = Field(default=0.0, ge=0.0, le=1.0)
    threshold: AttentionThreshold = Field(default=AttentionThreshold.LOW)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    reason: str = Field(default="")
    provenance: dict[str, Any] = Field(default_factory=dict)

    # Preemption, Delegation & Aging Tracking
    context_snapshot_id: str | None = None
    delegated_to: str | None = None
    delegation_history: list[dict[str, Any]] = Field(default_factory=list)
    deferral_count: int = Field(default=0, ge=0)
    aging_boost: float = Field(default=0.0, ge=0.0)
    interruption_count: int = Field(default=0, ge=0)
    is_adversarial_suppressed: bool = False


class AttentionCandidateCreate(BaseModel):
    """Payload for submitting or evaluating a new attention candidate."""

    source_type: str = "event"
    source_id: str | None = None
    tenant_id: str = "default"
    workspace_id: str = "default"
    event_type: str = "general"
    title: str
    description: str = ""
    importance: float = 0.5
    urgency: float = 0.5
    severity: str = "MEDIUM"
    risk: float = 0.3
    relevance: float = 0.5
    novelty: float = 0.0
    uncertainty: float = 0.2
    change_magnitude: float = 0.0
    goal_alignment: float = 0.5
    deadline: datetime | None = None
    goal_refs: list[str] = Field(default_factory=list)
    mission_refs: list[str] = Field(default_factory=list)
    task_refs: list[str] = Field(default_factory=list)
    incident_refs: list[str] = Field(default_factory=list)
    decision_refs: list[str] = Field(default_factory=list)
    estimated_effort: float = 1.0
    estimated_duration_sec: int = 300
    required_capabilities: list[str] = Field(default_factory=list)
    required_agents: list[str] = Field(default_factory=list)
    required_tools: list[str] = Field(default_factory=list)
    confidence: float = 0.8
    reason: str = ""
    provenance: dict[str, Any] = Field(default_factory=dict)


class AttentionCandidateUpdate(BaseModel):
    """Partial update payload for an attention candidate."""

    title: str | None = None
    description: str | None = None
    importance: float | None = None
    urgency: float | None = None
    severity: str | None = None
    risk: float | None = None
    relevance: float | None = None
    novelty: float | None = None
    uncertainty: float | None = None
    change_magnitude: float | None = None
    goal_alignment: float | None = None
    deadline: datetime | None = None
    current_state: AttentionState | None = None
    reason: str | None = None
    delegated_to: str | None = None


class AttentionSnapshot(BaseModel):
    """Point-in-time snapshot of the cognitive attention engine state."""

    snapshot_id: str = Field(default_factory=lambda: f"attsnap-{uuid4().hex[:12]}")
    tenant_id: str = "default"
    timestamp: datetime = Field(default_factory=utc_now)
    mode: AttentionMode = AttentionMode.NORMAL_MODE
    current_focus_id: str | None = None
    stack_ids: list[str] = Field(default_factory=list)
    queue_summary: list[dict[str, Any]] = Field(default_factory=list)
    resource_budget: CognitiveResourceBudget = Field(default_factory=CognitiveResourceBudget)
    active_goal_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AttentionHealthMetrics(BaseModel):
    """Operational telemetry and health metrics for cognitive attention."""

    active_attention_items: int = 0
    queued_items: int = 0
    critical_items: int = 0
    deferred_items: int = 0
    delegated_items: int = 0
    average_attention_duration_sec: float = 0.0
    interruption_rate: float = 0.0
    false_interruptions: int = 0
    missed_critical_events: int = 0
    attention_switch_rate: float = 0.0
    goal_starvation_rate: float = 0.0
    resource_utilization_pct: float = 0.0
    attention_efficiency_score: float = 1.0
    notification_rate: float = 0.0
    notification_noise_ratio: float = 0.0
    escalation_rate: float = 0.0
    de_escalation_rate: float = 0.0
