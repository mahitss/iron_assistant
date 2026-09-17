"""Domain models, contracts, and operational state machines for Task 99:
KAIRO Autonomous Situation Awareness, Signal Fusion & Proactive Response Orchestrator.

Enforces:
- SIGNAL != SITUATION
- SITUATION != TRUTH
- CORRELATION != CAUSATION
- FORECAST != OBSERVATION
- SIMULATION != REALITY
- AGENT OUTPUT != AUTHORITY
- ATTENTION != DECISION
- DECISION != AUTHORIZATION
- AUTHORIZATION != EXECUTION
- EXECUTION != SUCCESS
- SUCCESS != VERIFIED STATE
- VERIFIED STATE != PERMANENT STABILITY
- EMERGENCY STOP ALWAYS WINS
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field, model_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


def generate_uuid(prefix: str = "sit") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# =====================================================================
# ENUMS
# =====================================================================

class SituationLifecycleState(str, Enum):
    """Rigid operational lifecycle states of an active or historical situation (Section 2)."""
    DETECTED = "DETECTED"
    CORRELATING = "CORRELATING"
    FORMING = "FORMING"
    ACTIVE = "ACTIVE"
    ESCALATING = "ESCALATING"
    INTERVENTION_PENDING = "INTERVENTION_PENDING"
    INTERVENTION_ACTIVE = "INTERVENTION_ACTIVE"
    OBSERVING = "OBSERVING"
    STABILIZING = "STABILIZING"
    RESOLVING = "RESOLVING"
    RESOLVED = "RESOLVED"
    SUPPRESSED = "SUPPRESSED"
    EXPIRED = "EXPIRED"
    MERGED = "MERGED"
    SPLIT = "SPLIT"
    UNKNOWN = "UNKNOWN"
    # Task 60 backward-compatible states
    MITIGATING = "MITIGATING"
    ASSESSING = "ASSESSING"
    CONFIRMED = "CONFIRMED"
    MONITORING = "MONITORING"
    RECOVERING = "RECOVERING"
    CLOSED = "CLOSED"


# Backward compatibility alias for Task 60 SituationStatus
SituationStatus = SituationLifecycleState


class SituationType(str, Enum):
    """Categorization of emerging situations (Section 7)."""
    INCIDENT = "INCIDENT"
    ANOMALY = "ANOMALY"
    RISK = "RISK"
    OPPORTUNITY = "OPPORTUNITY"
    CHANGE = "CHANGE"
    DEGRADATION = "DEGRADATION"
    RECOVERY = "RECOVERY"
    BLOCKER = "BLOCKER"
    GOAL_TRANSITION = "GOAL_TRANSITION"
    SECURITY_EVENT = "SECURITY_EVENT"
    RESOURCE_PRESSURE = "RESOURCE_PRESSURE"
    CAPABILITY_EVENT = "CAPABILITY_EVENT"
    UNKNOWN = "UNKNOWN"


class CausalStatus(str, Enum):
    """Explicit epistemic causal classification (Section 9)."""
    OBSERVED = "OBSERVED"
    CORRELATED = "CORRELATED"
    CAUSALLY_SUPPORTED = "CAUSALLY_SUPPORTED"
    CAUSALLY_UNCERTAIN = "CAUSALLY_UNCERTAIN"
    CONFLICTING = "CONFLICTING"
    UNKNOWN = "UNKNOWN"


class SourceTrustLevel(str, Enum):
    """Origin trust classification ensuring prompt injection resistance (Section 42)."""
    # Task 60 backward-compatible values
    TRUSTED_SYSTEM = "TRUSTED_SYSTEM"
    VERIFIED_EXTERNAL = "VERIFIED_EXTERNAL"
    USER_REPORTED = "USER_REPORTED"
    UNVERIFIED_EXTERNAL = "UNVERIFIED_EXTERNAL"
    UNTRUSTED_EXTERNAL = "UNTRUSTED_EXTERNAL"
    UNTRUSTED = "UNTRUSTED"
    MODEL_GENERATED = "MODEL_GENERATED"
    SIMULATED = "SIMULATED"
    # Task 99 fine-grained values
    TRUSTED_INTERNAL = "TRUSTED_INTERNAL"
    USER_AUTHORED = "USER_AUTHORED"
    EXTERNAL_UNTRUSTED = "EXTERNAL_UNTRUSTED"
    TOOL_UNTRUSTED = "TOOL_UNTRUSTED"
    WEB_UNTRUSTED = "WEB_UNTRUSTED"
    CODE_UNTRUSTED = "CODE_UNTRUSTED"
    SCREEN_UNTRUSTED = "SCREEN_UNTRUSTED"
    AGENT_DERIVED = "AGENT_DERIVED"
    MODEL_DERIVED = "MODEL_DERIVED"


class SituationSeverity(str, Enum):
    """Operational severity tiers (Section 2)."""
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ProactivePolicyCapability(str, Enum):
    """Policy-aware proactive capability determination (Section 48)."""
    CAN_OBSERVE = "CAN_OBSERVE"
    CAN_NOTIFY = "CAN_NOTIFY"
    CAN_INVESTIGATE = "CAN_INVESTIGATE"
    CAN_PROPOSE_ACTION = "CAN_PROPOSE_ACTION"
    CAN_EXECUTE_ACTION = "CAN_EXECUTE_ACTION"


class StateReconciliationStatus(str, Enum):
    """World-state reality reconciliation verification status (Section 10)."""
    UNRECONCILED = "UNRECONCILED"
    UNVERIFIED = "UNVERIFIED"
    SYNCHRONIZED = "SYNCHRONIZED"
    DRIFT_DETECTED = "DRIFT_DETECTED"
    VERIFIED_MATCH = "VERIFIED_MATCH"
    CONTRADICTED = "CONTRADICTED"
    UNKNOWN = "UNKNOWN"


# =====================================================================
# DOMAIN MODELS
# =====================================================================

class SignalRecord(BaseModel):
    """Canonical normalized signal representation with full provenance (Section 3)."""
    model_config = ConfigDict(extra="ignore")

    signal_id: str = Field(default_factory=lambda: generate_uuid("sig"))
    source_type: str = "TELEMETRY"  # WORLD_STATE_DRIFT, RISK_FINDING, FORECAST, RELIABILITY, ACTION_TRANSACTION, etc.
    source_id: str = ""
    source_version: str = "v1"
    observed_at: datetime = Field(default_factory=utc_now)
    received_at: datetime = Field(default_factory=utc_now)
    effective_at: Optional[datetime] = None
    signal_type: str = "OBSERVATION"  # WORLD_STATE_DRIFT, RISK_INCREASE, FORECAST_THRESHOLD, etc.
    subject: str = ""
    entity: Optional[str] = None
    scope: str = "SYSTEM"
    severity: SituationSeverity = SituationSeverity.INFO
    payload_ref: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0
    freshness: str = "FRESH"
    provenance: dict[str, Any] = Field(default_factory=dict)
    trust_classification: SourceTrustLevel = SourceTrustLevel.TRUSTED_INTERNAL
    sensitivity_classification: str = "INTERNAL"
    correlation_keys: list[str] = Field(default_factory=list)
    causal_references: list[str] = Field(default_factory=list)
    world_state_references: list[str] = Field(default_factory=list)
    decision_action_references: list[str] = Field(default_factory=list)
    trace_id: Optional[str] = None
    correlation_id: Optional[str] = None
    event_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def __init__(self, **data: Any) -> None:
        if "trust_level" in data and "trust_classification" not in data:
            data["trust_classification"] = data["trust_level"]
        if "source_trust" in data and "trust_classification" not in data:
            data["trust_classification"] = data["source_trust"]
        if "source_system" in data and "source_id" not in data:
            data["source_id"] = data["source_system"]
            if "source_type" not in data:
                data["source_type"] = data["source_system"]
        if "source" in data and "source_id" not in data:
            data["source_id"] = data["source"]
        if "occurred_at" in data and "observed_at" not in data:
            data["observed_at"] = data["occurred_at"]
        if "timestamp" in data and "observed_at" not in data:
            data["observed_at"] = data["timestamp"]
        if "event_type" in data and "signal_type" not in data:
            data["signal_type"] = data["event_type"]
        if "resource" in data and "entity" not in data:
            data["entity"] = data["resource"]
        if "environment" in data and "scope" not in data:
            data["scope"] = data["environment"]
        if "sensitivity" in data and "sensitivity_classification" not in data:
            data["sensitivity_classification"] = data["sensitivity"]
        if "causal_refs" in data and "causal_references" not in data:
            data["causal_references"] = data["causal_refs"]
        if "world_state_refs" in data and "world_state_references" not in data:
            data["world_state_references"] = data["world_state_refs"]
        if "decision_refs" in data and "decision_action_references" not in data:
            data["decision_action_references"] = data["decision_refs"]
        super().__init__(**data)

    @property
    def id(self) -> str:
        return self.signal_id

    @property
    def timestamp(self) -> datetime:
        return self.observed_at

    @timestamp.setter
    def timestamp(self, val: datetime) -> None:
        self.observed_at = val

    @property
    def source_system(self) -> str:
        return self.source_id or self.source_type

    @source_system.setter
    def source_system(self, val: str) -> None:
        self.source_id = val

    @property
    def source(self) -> str:
        return self.source_id

    @source.setter
    def source(self, val: str) -> None:
        self.source_id = val

    @property
    def source_trust(self) -> SourceTrustLevel:
        return self.trust_classification

    @source_trust.setter
    def source_trust(self, val: SourceTrustLevel) -> None:
        self.trust_classification = val

    @property
    def occurred_at(self) -> datetime:
        return self.observed_at

    @occurred_at.setter
    def occurred_at(self, val: datetime) -> None:
        self.observed_at = val

    @property
    def event_type(self) -> str:
        return self.signal_type

    @property
    def resource(self) -> Optional[str]:
        return self.entity or self.subject

    @property
    def environment(self) -> str:
        return self.scope

    @property
    def trust_level(self) -> SourceTrustLevel:
        return self.trust_classification

    @trust_level.setter
    def trust_level(self, val: SourceTrustLevel) -> None:
        self.trust_classification = val

    @property
    def sensitivity(self) -> str:
        return self.sensitivity_classification

    @sensitivity.setter
    def sensitivity(self, val: str) -> None:
        self.sensitivity_classification = val

    @property
    def causal_refs(self) -> list[str]:
        return self.causal_references

    @property
    def world_state_refs(self) -> list[str]:
        return self.world_state_references

    @property
    def decision_refs(self) -> list[str]:
        return self.decision_action_references

    def to_dict(self) -> dict[str, Any]:
        d = self.model_dump()
        d["id"] = self.signal_id
        d["source"] = self.source_system
        d["source_trust"] = (
            self.source_trust.value
            if hasattr(self.source_trust, "value")
            else str(self.source_trust)
        )
        d["occurred_at"] = self.occurred_at
        d["environment"] = self.environment
        d["event_type"] = self.signal_type
        return d



class SituationTimelineEntry(BaseModel):
    """Verifiable chronological event on a situation's timeline (Section 40)."""
    model_config = ConfigDict(extra="ignore")

    entry_id: str = Field(default_factory=lambda: generate_uuid("tl"))
    timestamp: datetime = Field(default_factory=utc_now)
    event_type: str
    summary: str
    is_inference: bool = False
    evidence_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = self.model_dump()
        d["id"] = self.entry_id
        return d



class SituationInterventionRecord(BaseModel):
    """Structured tracking of proactive intervention from proposal to verified resolution (Section 17)."""
    model_config = ConfigDict(extra="ignore")

    intervention_id: str = Field(default_factory=lambda: generate_uuid("intv"))
    situation_id: str
    decision_id: Optional[str] = None
    action_transaction_id: Optional[str] = None
    proposed_action: str = ""
    approval_status: str = "NOT_REQUIRED"  # NOT_REQUIRED, AWAITING_APPROVAL, APPROVED, REJECTED
    authorization_status: str = "AUTHORIZED"  # AUTHORIZED, DENIED, PENDING
    resource_allocation: dict[str, Any] = Field(default_factory=dict)
    execution_state: str = "PROPOSED"  # PROPOSED, STARTED, EXECUTED, FAILED, VERIFIED, NOT_VERIFIED
    verification_result: Optional[dict[str, Any]] = None
    outcome: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        d = self.model_dump()
        d["id"] = self.intervention_id
        return d



class SituationSuppressionRecord(BaseModel):
    """Auditable suppression record preserving underlying signals (Section 22)."""
    model_config = ConfigDict(extra="ignore")

    suppression_id: str = Field(default_factory=lambda: generate_uuid("supp"))
    situation_id: str
    reason: str
    suppressed_by: str = "system"
    suppressed_at: datetime = Field(default_factory=utc_now)
    expires_at: Optional[datetime] = None
    cooldown_seconds: Optional[float] = None
    is_active: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = self.model_dump()
        d["id"] = self.suppression_id
        return d



class SituationPatternRecord(BaseModel):
    """Bounded historical abstraction representing recurring situations (Section 46, 47)."""
    model_config = ConfigDict(extra="ignore")

    pattern_id: str = Field(default_factory=lambda: generate_uuid("pat"))
    pattern_name: str
    situation_type: SituationType = SituationType.INCIDENT
    pattern_fingerprint: str
    recurrence_count: int = 1
    first_observed_at: datetime = Field(default_factory=utc_now)
    last_observed_at: datetime = Field(default_factory=utc_now)
    average_interval_seconds: float = 0.0
    trend: str = "STABLE"  # ESCALATING, DE-ESCALATING, STABLE, PERIODIC
    previous_interventions: list[dict[str, Any]] = Field(default_factory=list)
    previous_outcomes: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SituationContextRecord(BaseModel):
    """Bounded, poison-resistant context assembled for downstream reasoning (Section 24)."""
    model_config = ConfigDict(extra="ignore")

    context_id: str = Field(default_factory=lambda: generate_uuid("ctx"))
    situation_id: str
    relevant_observations: list[dict[str, Any]] = Field(default_factory=list)
    related_graph_entities: list[str] = Field(default_factory=list)
    risk_findings: list[dict[str, Any]] = Field(default_factory=list)
    forecasts: list[dict[str, Any]] = Field(default_factory=list)
    goals: list[dict[str, Any]] = Field(default_factory=list)
    recent_actions: list[str] = Field(default_factory=list)
    relevant_decisions: list[str] = Field(default_factory=list)
    capability_state: dict[str, Any] = Field(default_factory=dict)
    resource_state: dict[str, Any] = Field(default_factory=dict)
    world_state_diffs: list[dict[str, Any]] = Field(default_factory=list)
    evidence_provenance: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class SituationRecord(BaseModel):
    """First-class persistent Situation representing correlated, evolving operational reality (Section 2)."""
    model_config = ConfigDict(extra="ignore")

    situation_id: str = Field(default_factory=lambda: generate_uuid("sit"))
    tenant_id: Optional[str] = None
    user_id: str = "default_user"
    scope: str = "SYSTEM"
    situation_type: SituationType = SituationType.INCIDENT
    lifecycle_state: SituationLifecycleState = SituationLifecycleState.DETECTED
    title: str = ""
    summary: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    first_signal_at: datetime = Field(default_factory=utc_now)
    last_signal_at: datetime = Field(default_factory=utc_now)
    last_observed_at: datetime = Field(default_factory=utc_now)
    resolved_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    severity: SituationSeverity = SituationSeverity.MEDIUM
    priority: float = 0.5
    confidence: float = 1.0
    novelty: float = 0.0
    urgency: float = 0.5
    impact: float = 0.5
    uncertainty: float = 0.0
    observability_quality: float = 1.0
    freshness: str = "FRESH"
    affected_entities: list[str] = Field(default_factory=list)
    affected_capabilities: list[str] = Field(default_factory=list)
    affected_resources: list[str] = Field(default_factory=list)
    affected_plans: list[str] = Field(default_factory=list)
    affected_goals: list[str] = Field(default_factory=list)
    affected_workflows: list[str] = Field(default_factory=list)
    affected_agents: list[str] = Field(default_factory=list)
    affected_projects: list[str] = Field(default_factory=list)
    affected_services: list[str] = Field(default_factory=list)
    hypotheses: list[Any] = Field(default_factory=list)
    source_count: int = 1
    signal_count: int = 1
    correlation_score: float = 1.0
    duplicate_group: Optional[str] = None
    parent_situation_id: Optional[str] = None
    supersedes_situation_id: Optional[str] = None
    merged_from_ids: list[str] = Field(default_factory=list)
    merged_into_id: Optional[str] = None
    merge_reason: Optional[str] = None
    split_from_id: Optional[str] = None
    causal_status: CausalStatus = CausalStatus.UNKNOWN
    state_reconciliation_status: str = "UNRECONCILED"  # UNRECONCILED, SYNCHRONIZED, DRIFT_DETECTED, VERIFIED
    recommended_next_step: Optional[str] = None
    current_decision_id: Optional[str] = None
    current_action_transaction_id: Optional[str] = None
    timeline: list[SituationTimelineEntry] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    signals: list[SignalRecord] = Field(default_factory=list)
    interventions: list[SituationInterventionRecord] = Field(default_factory=list)
    flapping_count: int = 0
    recurrence_count: int = 1
    version: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _normalize_situation(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Normalization of aliases
            if "status" in data and not data.get("lifecycle_state"):
                try:
                    data["lifecycle_state"] = SituationLifecycleState(data["status"])
                except Exception:
                    data["lifecycle_state"] = SituationLifecycleState.DETECTED
            if "description" in data and not data.get("summary"):
                data["summary"] = data["description"]
            elif "summary" in data and not data.get("description"):
                data["description"] = data["summary"]
            if "situation_id" not in data and "id" in data:
                data["situation_id"] = data["id"]
        return data

    @property
    def id(self) -> str:
        return self.situation_id

    @property
    def status(self) -> SituationLifecycleState:
        return self.lifecycle_state

    @status.setter
    def status(self, val: SituationLifecycleState | str) -> None:
        if isinstance(val, str):
            self.lifecycle_state = SituationLifecycleState(val)
        else:
            self.lifecycle_state = val

    @property
    def description(self) -> str:
        return self.summary

    @description.setter
    def description(self, val: str) -> None:
        self.summary = val

    @property
    def environment(self) -> str:
        return self.scope

    @environment.setter
    def environment(self, val: str) -> None:
        self.scope = val

    def to_dict(self) -> dict[str, Any]:
        d = self.model_dump()
        d["id"] = self.situation_id
        d["status"] = (
            self.lifecycle_state.value
            if hasattr(self.lifecycle_state, "value")
            else str(self.lifecycle_state)
        )
        d["description"] = self.summary
        d["environment"] = self.scope
        return d

