"""Canonical Domain Contracts for Kairo Autonomous Cognitive Memory & Lifelong Learning Fabric (Task 103).

Enforces:
- MEMORY != TRUTH
- MEMORY != CURRENT STATE
- MEMORY != AUTHORIZATION
- MEMORY != POLICY
- MEMORY != GOAL
- MEMORY != DECISION
- MEMORY != CAUSALITY
- MEMORY != REALITY
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


def _now_utc() -> str:
    """Returns current ISO 8601 UTC timestamp."""
    return datetime.now(UTC).isoformat()


def _uuid_hex(prefix: str, length: int = 12) -> str:
    """Generates prefixed unique hex identifier."""
    return f"{prefix}_{uuid.uuid4().hex[:length]}"


class ExperienceSource(str, Enum):
    """Authoritative source classification for raw operational experiences."""
    USER_INTERACTION = "USER_INTERACTION"
    MISSION_OUTCOME = "MISSION_OUTCOME"
    SITUATION = "SITUATION"
    DECISION = "DECISION"
    ACTION = "ACTION"
    VERIFICATION = "VERIFICATION"
    FAILURE = "FAILURE"
    RECOVERY = "RECOVERY"
    CAPABILITY_USAGE = "CAPABILITY_USAGE"
    AGENT_COLLABORATION = "AGENT_COLLABORATION"
    WORKFLOW_EXECUTION = "WORKFLOW_EXECUTION"
    WORLD_STATE_CHANGE = "WORLD_STATE_CHANGE"
    FORECAST_OUTCOME = "FORECAST_OUTCOME"
    PREDICTION_ERROR = "PREDICTION_ERROR"
    USER_FEEDBACK = "USER_FEEDBACK"
    USER_CORRECTION = "USER_CORRECTION"
    OBSERVATION = "OBSERVATION"


class ExperienceTrust(str, Enum):
    """Provenance and epistemological trust levels for experiences."""
    OBSERVED = "OBSERVED"
    USER_CONFIRMED = "USER_CONFIRMED"
    SYSTEM_VERIFIED = "SYSTEM_VERIFIED"
    ACTION_VERIFIED = "ACTION_VERIFIED"
    WORLD_STATE_VERIFIED = "WORLD_STATE_VERIFIED"
    MODEL_DERIVED = "MODEL_DERIVED"
    AGENT_DERIVED = "AGENT_DERIVED"
    EXTERNAL_UNTRUSTED = "EXTERNAL_UNTRUSTED"
    TOOL_DERIVED = "TOOL_DERIVED"
    INFERRED = "INFERRED"
    UNKNOWN = "UNKNOWN"


class MemoryType(str, Enum):
    """15 canonical cognitive memory taxonomy types."""
    EPISODIC = "EPISODIC"
    SEMANTIC = "SEMANTIC"
    PROCEDURAL = "PROCEDURAL"
    PREFERENCE = "PREFERENCE"
    ENVIRONMENTAL = "ENVIRONMENTAL"
    CAPABILITY = "CAPABILITY"
    MISSION = "MISSION"
    DECISION = "DECISION"
    FAILURE = "FAILURE"
    RECOVERY = "RECOVERY"
    PATTERN = "PATTERN"
    CONSTRAINT = "CONSTRAINT"
    FACTUAL = "FACTUAL"
    TEMPORAL = "TEMPORAL"
    RELATIONAL = "RELATIONAL"


class MemoryLifecycleState(str, Enum):
    """Full lifecycle state progression for durable memory entities."""
    EPISODE = "EPISODE"
    CANDIDATE = "CANDIDATE"
    VERIFIED = "VERIFIED"
    CONSOLIDATED = "CONSOLIDATED"
    ACTIVE = "ACTIVE"
    STALE = "STALE"
    SUPERSEDED = "SUPERSEDED"
    CONFLICTED = "CONFLICTED"
    RETIRED = "RETIRED"


class FreshnessState(str, Enum):
    """Temporal validity and freshness states."""
    CURRENT = "CURRENT"
    RECENT = "RECENT"
    STALE = "STALE"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"


class MemoryScope(str, Enum):
    """Multi-tenant security and operational scope boundaries."""
    GLOBAL = "GLOBAL"
    USER = "USER"
    PROJECT = "PROJECT"
    MISSION = "MISSION"
    CAPABILITY = "CAPABILITY"
    ENVIRONMENT = "ENVIRONMENT"
    SESSION = "SESSION"
    TASK = "TASK"
    WORKFLOW = "WORKFLOW"


class MemoryErrorType(str, Enum):
    """Metacognitive error classification for memory failures."""
    STALE = "STALE"
    INCORRECT = "INCORRECT"
    CONTRADICTORY = "CONTRADICTORY"
    MISSCOPED = "MISSCOPED"
    OVERGENERALIZED = "OVERGENERALIZED"
    UNDERGENERALIZED = "UNDERGENERALIZED"
    LOW_PROVENANCE = "LOW_PROVENANCE"
    DUPLICATE = "DUPLICATE"
    MISRETRIEVED = "MISRETRIEVED"
    MISAPPLIED = "MISAPPLIED"
    UNKNOWN = "UNKNOWN"


class Experience(BaseModel):
    """First-class representation of a meaningful historical occurrence."""
    model_config = ConfigDict(extra="ignore")

    experience_id: str = Field(default_factory=lambda: _uuid_hex("exp"))
    source_type: ExperienceSource = ExperienceSource.OBSERVATION
    source_id: Optional[str] = None
    scope: MemoryScope = MemoryScope.PROJECT
    occurred_at: str = Field(default_factory=_now_utc)
    recorded_at: str = Field(default_factory=_now_utc)
    actor: str = "kairo_system"
    summary: str
    structured_facts: Dict[str, Any] = Field(default_factory=dict)
    outcome: str = "SUCCESS"  # SUCCESS, FAILURE, PARTIAL_SUCCESS, DEGRADATION, UNKNOWN
    confidence: float = 0.8
    provenance: Dict[str, Any] = Field(default_factory=dict)
    trust_classification: ExperienceTrust = ExperienceTrust.OBSERVED
    importance: float = 0.5
    recurrence_count: int = 1

    # Cross-subsystem authoritative linkages
    related_entities: List[str] = Field(default_factory=list)
    related_goals: List[str] = Field(default_factory=list)
    related_missions: List[str] = Field(default_factory=list)
    related_capabilities: List[str] = Field(default_factory=list)
    related_situations: List[str] = Field(default_factory=list)
    related_decisions: List[str] = Field(default_factory=list)
    related_actions: List[str] = Field(default_factory=list)
    verification_references: List[str] = Field(default_factory=list)
    world_state_references: List[str] = Field(default_factory=list)

    version: str = "1.0.0"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CognitiveMemoryItem(BaseModel):
    """Durable, validated, and structured knowledge item in the lifelong learning fabric."""
    model_config = ConfigDict(extra="ignore")

    memory_id: str = Field(default_factory=lambda: _uuid_hex("mem"))
    memory_type: MemoryType = MemoryType.EPISODIC
    lifecycle_state: MemoryLifecycleState = MemoryLifecycleState.ACTIVE
    scope: MemoryScope = MemoryScope.PROJECT
    scope_id: Optional[str] = None  # project_id, mission_id, or user_id

    content: str
    structured_data: Dict[str, Any] = Field(default_factory=dict)

    confidence: float = 0.7
    importance: float = 0.5
    freshness: FreshnessState = FreshnessState.CURRENT
    trust_classification: ExperienceTrust = ExperienceTrust.OBSERVED

    # Temporal bounding
    observed_at: str = Field(default_factory=_now_utc)
    valid_from: str = Field(default_factory=_now_utc)
    valid_until: Optional[str] = None
    last_verified_at: Optional[str] = None
    decay_rate_days: float = 30.0  # Fast decay for environment (1-7d), slow for procedures (90d)

    # Lineage and versioning
    version: int = 1
    superseded_by: Optional[str] = None
    supersedes: Optional[str] = None
    source_experience_ids: List[str] = Field(default_factory=list)
    contradicting_memory_ids: List[str] = Field(default_factory=list)
    related_entities: List[str] = Field(default_factory=list)

    # Procedural metadata (if PROCEDURAL)
    preconditions: List[str] = Field(default_factory=list)
    procedure_steps: List[str] = Field(default_factory=list)
    expected_outcome: Optional[str] = None
    verification_criteria: List[str] = Field(default_factory=list)
    exceptions: List[str] = Field(default_factory=list)

    # Evidence and provenance details
    confidence_evidence: str = ""
    evidence_experience_ids: List[str] = Field(default_factory=list)
    verification_references: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Telemetry
    access_count: int = 0
    application_count: int = 0
    useful_count: int = 0
    error_count: int = 0
    created_at: str = Field(default_factory=_now_utc)
    updated_at: str = Field(default_factory=_now_utc)

    @property
    def provenance_trust(self) -> ExperienceTrust:
        return self.trust_classification

    @property
    def predecessor_id(self) -> Optional[str]:
        return self.supersedes

    @property
    def lineage_ids(self) -> List[str]:
        chain = []
        if self.supersedes:
            chain.append(self.supersedes)
        chain.append(self.memory_id)
        if self.superseded_by:
            chain.append(self.superseded_by)
        return chain

    @property
    def provenance_trail(self) -> List[str]:
        return [f"Captured at {self.observed_at} from {len(self.source_experience_ids)} experience(s) ({self.trust_classification.value})"]


class MemoryConflict(BaseModel):
    """Dialectic contradiction between opposing or incompatible memories."""
    model_config = ConfigDict(extra="ignore")

    conflict_id: str = Field(default_factory=lambda: _uuid_hex("mconf"))
    memory_a_id: str
    memory_b_id: str
    memory_a_claim: str
    memory_b_claim: str
    scope: MemoryScope = MemoryScope.PROJECT
    status: str = "ACTIVE"  # ACTIVE, RESOLVED_A_WINS, RESOLVED_B_WINS, BOTH_STALE
    entity_reference: str = "SYSTEM"
    discrepancy_summary: str = ""
    detected_at: str = Field(default_factory=_now_utc)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    current_world_state_ref: Optional[str] = None
    world_state_arbitration: Optional[str] = None  # Which claim current world-state empirically supports


class MemoryPattern(BaseModel):
    """Consolidated recurrence abstraction extracted from repeated verified experiences."""
    model_config = ConfigDict(extra="ignore")

    pattern_id: str = Field(default_factory=lambda: _uuid_hex("pat"))
    pattern_type: MemoryType = MemoryType.PATTERN
    title: str
    description: str
    scope: MemoryScope = MemoryScope.PROJECT
    recurrence_count: int = 1
    confidence: float = 0.8
    first_seen: str = Field(default_factory=_now_utc)
    last_seen: str = Field(default_factory=_now_utc)
    source_experience_ids: List[str] = Field(default_factory=list)
    exceptions: List[str] = Field(default_factory=list)
    context_conditions: Dict[str, Any] = Field(default_factory=dict)


class MemoryContextPack(BaseModel):
    """Bounded, high-density context pack for consumption by reasoning engines."""
    model_config = ConfigDict(extra="ignore")

    pack_id: str = Field(default_factory=lambda: _uuid_hex("pack"))
    query: str
    scope: MemoryScope = MemoryScope.PROJECT
    assembled_at: str = Field(default_factory=_now_utc)
    relevant_memories: List[Dict[str, Any]] = Field(default_factory=list)
    verified_procedures: List[Dict[str, Any]] = Field(default_factory=list)
    active_conflicts: List[Dict[str, Any]] = Field(default_factory=list)
    known_exceptions: List[str] = Field(default_factory=list)
    world_state_overrides: List[str] = Field(default_factory=list)
    total_items: int = 0

    @property
    def memories(self) -> List[Dict[str, Any]]:
        return self.relevant_memories

    @property
    def freshness_distribution(self) -> Dict[str, int]:
        dist: Dict[str, int] = {}
        for m in self.relevant_memories:
            f = m.get("freshness", "CURRENT")
            dist[f] = dist.get(f, 0) + 1
        return dist if dist else {"CURRENT": 0}



class MemoryApplicationRecord(BaseModel):
    """Telemetry tracking when memory is retrieved and applied by a reasoning consumer."""
    model_config = ConfigDict(extra="ignore")

    application_id: str = Field(default_factory=lambda: _uuid_hex("appl"))
    memory_id: str
    consumer: str  # DECISION_ENGINE, MISSION_CONTROL, PLANNING, SITUATION_AWARENESS
    context_summary: str
    applied_at: str = Field(default_factory=_now_utc)
    decision_ref: Optional[str] = None
    action_ref: Optional[str] = None


class MemoryFeedbackRecord(BaseModel):
    """Metacognitive feedback measuring whether memory application helped or caused error."""
    model_config = ConfigDict(extra="ignore")

    feedback_id: str = Field(default_factory=lambda: _uuid_hex("mfbk"))
    memory_id: str
    application_id: Optional[str] = None
    was_useful: bool = True
    caused_error: bool = False
    error_type: Optional[MemoryErrorType] = None
    empirical_outcome: str = "SUCCESS"
    notes: Optional[str] = None
    recorded_at: str = Field(default_factory=_now_utc)


class MemorySnapshot(BaseModel):
    """Point-in-time immutable snapshot of cognitive memory state for replay and audit."""
    model_config = ConfigDict(extra="ignore")

    snapshot_id: str = Field(default_factory=lambda: _uuid_hex("msnap"))
    created_at: str = Field(default_factory=_now_utc)
    total_memories: int = 0
    active_count: int = 0
    stale_count: int = 0
    conflicted_count: int = 0
    pattern_count: int = 0
    memory_ids: List[str] = Field(default_factory=list)
    conflict_ids: List[str] = Field(default_factory=list)
    pattern_ids: List[str] = Field(default_factory=list)
