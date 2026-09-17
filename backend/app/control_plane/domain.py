"""Domain models, contracts, and lifecycle state machines for Kairo Autonomous Cognitive Control Plane (Task 102).

Enforces:
- Control Plane is an orchestrator, NOT an authority.
- 19 rigid cycle states: CREATED -> OBSERVING -> RECONCILING -> ASSESSING -> CONTEXT_BUILDING ->
  PLANNING_REQUESTED -> DECISION_REQUESTED -> WAITING -> AUTHORIZED -> EXECUTING -> VERIFYING ->
  LEARNING -> COMPLETED / NO_ACTION / BLOCKED / PAUSED / CANCELLED / FAILED / UNKNOWN.
- Unified operating loop contracts.
- First-class WAITING and NO_ACTION with structured reasons.
- Bounded budget envelopes and loop-guard tracking.
- EmergencyStop absolute primacy.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


def _now_utc() -> str:
    return datetime.now(UTC).isoformat()


def _uuid_hex(prefix: str = "cycle", length: int = 12) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:length]}"


class ControlCycleStatus(str, Enum):
    """Rigid operational lifecycle states of a Control Cycle."""
    CREATED = "CREATED"
    OBSERVING = "OBSERVING"
    RECONCILING = "RECONCILING"
    ASSESSING = "ASSESSING"
    CONTEXT_BUILDING = "CONTEXT_BUILDING"
    PLANNING_REQUESTED = "PLANNING_REQUESTED"
    DECISION_REQUESTED = "DECISION_REQUESTED"
    WAITING = "WAITING"
    AUTHORIZED = "AUTHORIZED"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    LEARNING = "LEARNING"
    COMPLETED = "COMPLETED"
    NO_ACTION = "NO_ACTION"
    BLOCKED = "BLOCKED"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class TriggerType(str, Enum):
    """Event domain triggers initiating a control cycle."""
    USER_REQUEST = "USER_REQUEST"
    NEW_SITUATION = "NEW_SITUATION"
    SITUATION_ESCALATION = "SITUATION_ESCALATION"
    MISSION_CHANGE = "MISSION_CHANGE"
    GOAL_CHANGE = "GOAL_CHANGE"
    WORLD_STATE_DRIFT = "WORLD_STATE_DRIFT"
    FORECAST_THRESHOLD = "FORECAST_THRESHOLD"
    RISK_ESCALATION = "RISK_ESCALATION"
    RELIABILITY_DEGRADATION = "RELIABILITY_DEGRADATION"
    ACTION_COMPLETION = "ACTION_COMPLETION"
    ACTION_FAILURE = "ACTION_FAILURE"
    ACTION_UNKNOWN = "ACTION_UNKNOWN"
    CAPABILITY_CHANGE = "CAPABILITY_CHANGE"
    DEPENDENCY_CHANGE = "DEPENDENCY_CHANGE"
    RESOURCE_CHANGE = "RESOURCE_CHANGE"
    APPROVAL_RECEIVED = "APPROVAL_RECEIVED"
    APPROVAL_REJECTED = "APPROVAL_REJECTED"
    AGENT_RESULT = "AGENT_RESULT"
    SCHEDULED_REVIEW = "SCHEDULED_REVIEW"
    RECOVERY_EVENT = "RECOVERY_EVENT"
    SELF_MODEL_CHANGE = "SELF_MODEL_CHANGE"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class WaitingReason(str, Enum):
    """Explicit structured reasons a control cycle is suspended."""
    WAITING_FOR_USER = "WAITING_FOR_USER"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    WAITING_FOR_DEPENDENCY = "WAITING_FOR_DEPENDENCY"
    WAITING_FOR_WORLD_STATE = "WAITING_FOR_WORLD_STATE"
    WAITING_FOR_VERIFICATION = "WAITING_FOR_VERIFICATION"
    WAITING_FOR_RESOURCE = "WAITING_FOR_RESOURCE"
    WAITING_FOR_CAPABILITY = "WAITING_FOR_CAPABILITY"
    WAITING_FOR_EXTERNAL_EVENT = "WAITING_FOR_EXTERNAL_EVENT"
    WAITING_FOR_SCHEDULE = "WAITING_FOR_SCHEDULE"


class NoActionReason(str, Enum):
    """Explicit structured reasons for deliberate NO_ACTION conclusion."""
    NO_MEANINGFUL_CHANGE = "NO_MEANINGFUL_CHANGE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    STALE_STATE = "STALE_STATE"
    USER_PREFERENCE = "USER_PREFERENCE"
    GOVERNANCE_RESTRICTION = "GOVERNANCE_RESTRICTION"
    LOW_IMPACT = "LOW_IMPACT"
    ACTION_COST_TOO_HIGH = "ACTION_COST_TOO_HIGH"
    MISSION_ALREADY_PROGRESSING = "MISSION_ALREADY_PROGRESSING"
    WAITING_FOR_DEPENDENCY = "WAITING_FOR_DEPENDENCY"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    EMERGENCY_STOP_ACTIVE = "EMERGENCY_STOP_ACTIVE"
    OBSERVATION_REQUIRED = "OBSERVATION_REQUIRED"


class ControlMode(str, Enum):
    """Derived supervisory autonomy mode from authoritative constraints."""
    NORMAL = "NORMAL"
    OBSERVATION_ONLY = "OBSERVATION_ONLY"
    ASSISTED = "ASSISTED"
    PROPOSAL_ONLY = "PROPOSAL_ONLY"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    BOUNDED_AUTONOMY = "BOUNDED_AUTONOMY"
    DEGRADED = "DEGRADED"
    RECOVERY = "RECOVERY"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class CyclePriority(int, Enum):
    """Execution priority ranking for control queue."""
    EMERGENCY = 1
    CRITICAL = 2
    HIGH = 3
    NORMAL = 4
    LOW = 5


class BudgetEnvelope(BaseModel):
    """Strict resource and execution limits allocated to a single cycle."""
    model_config = ConfigDict(extra="ignore")

    max_duration_s: float = 60.0
    max_model_calls: int = 5
    max_agent_calls: int = 3
    max_tool_calls: int = 10
    max_planning_attempts: int = 2
    max_decision_attempts: int = 2
    max_retries: int = 3

    consumed_duration_s: float = 0.0
    consumed_model_calls: int = 0
    consumed_agent_calls: int = 0
    consumed_tool_calls: int = 0
    consumed_planning_attempts: int = 0
    consumed_decision_attempts: int = 0
    consumed_retries: int = 0

    def is_exhausted(self) -> bool:
        return (
            self.consumed_duration_s >= self.max_duration_s
            or self.consumed_model_calls >= self.max_model_calls
            or self.consumed_agent_calls >= self.max_agent_calls
            or self.consumed_tool_calls >= self.max_tool_calls
            or self.consumed_retries >= self.max_retries
        )


class ControlSnapshot(BaseModel):
    """Immutable state snapshot captured at the start of a control cycle."""
    model_config = ConfigDict(extra="ignore")

    snapshot_id: str = Field(default_factory=lambda: _uuid_hex("csnap"))
    created_at: str = Field(default_factory=_now_utc)
    world_state_ref: str = "world_current"
    self_model_ref: str = "self_current"
    active_situations: List[str] = Field(default_factory=list)
    active_missions: List[str] = Field(default_factory=list)
    active_goals: List[str] = Field(default_factory=list)
    attention_items: List[str] = Field(default_factory=list)
    reliability_state: str = "HEALTHY"
    resource_saturation_pct: float = 0.0
    emergency_stop_state: bool = False
    freshness: str = "CURRENT"  # CURRENT, RECENT, STALE, CONFLICTING, UNKNOWN


class ControlCycle(BaseModel):
    """A first-class, versioned unit of bounded cognitive orchestration."""
    model_config = ConfigDict(extra="ignore")

    cycle_id: str = Field(default_factory=lambda: _uuid_hex("cycle"))
    status: ControlCycleStatus = ControlCycleStatus.CREATED
    priority: CyclePriority = CyclePriority.NORMAL
    control_mode: ControlMode = ControlMode.BOUNDED_AUTONOMY
    started_at: str = Field(default_factory=_now_utc)
    completed_at: Optional[str] = None
    trigger_type: TriggerType = TriggerType.USER_REQUEST
    trigger_payload: Dict[str, Any] = Field(default_factory=dict)
    coalesced_triggers: List[Dict[str, Any]] = Field(default_factory=list)
    scope: str = "SYSTEM"

    # Cross-subsystem authoritative references
    objective_ref: Optional[str] = None
    mission_ref: Optional[str] = None
    situation_ref: Optional[str] = None
    world_state_ref: Optional[str] = None
    self_state_ref: Optional[str] = None
    context_ref: Optional[str] = None
    plan_ref: Optional[str] = None
    decision_ref: Optional[str] = None
    action_ref: Optional[str] = None
    verification_ref: Optional[str] = None

    # Results & Deliberate Exits
    result: Optional[str] = None
    reason: Optional[str] = None
    waiting_reason: Optional[WaitingReason] = None
    no_action_reason: Optional[NoActionReason] = None
    budget: BudgetEnvelope = Field(default_factory=BudgetEnvelope)

    # Loop guard fingerprints
    decision_fingerprint: Optional[str] = None
    action_fingerprint: Optional[str] = None
    failure_fingerprint: Optional[str] = None

    trace_id: str = Field(default_factory=lambda: _uuid_hex("trace"))
    correlation_id: str = Field(default_factory=lambda: _uuid_hex("corr"))
    version: str = "1.0.0"
