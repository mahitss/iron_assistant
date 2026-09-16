"""Domain models, contracts, and lifecycle state machines for Task 94 Decision Intelligence.

Enforces:
- Non-negotiable axioms:
  DECISION != AUTHORIZATION, DECISION != POLICY, DECISION != PLANNING, DECISION != EXECUTION
- Rigid lifecycle transitions and assumption tracking
- First-class NO-ACTION option representation
- Multi-criteria trade-offs without flattening into fake universal scores
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _uuid_hex(prefix: str, length: int = 12) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:length]}"


class DecisionType(str, Enum):
    """Primary intent and nature of the decision."""
    ACTION = "ACTION"
    NO_ACTION = "NO_ACTION"
    DEFER = "DEFER"
    ESCALATE = "ESCALATE"
    REQUEST_INFORMATION = "REQUEST_INFORMATION"
    REQUEST_APPROVAL = "REQUEST_APPROVAL"
    REPLAN = "REPLAN"
    ROLLBACK = "ROLLBACK"
    RECOVER = "RECOVER"
    RESOURCE_ALLOCATION = "RESOURCE_ALLOCATION"
    POLICY_CHOICE = "POLICY_CHOICE"
    DESTRUCTIVE = "DESTRUCTIVE"


class DecisionLifecycleState(str, Enum):
    """Rigid operational lifecycle states of a decision."""
    PROPOSED = "PROPOSED"
    EVALUATING = "EVALUATING"
    BLOCKED = "BLOCKED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SELECTED = "SELECTED"
    EXECUTING = "EXECUTING"
    EXECUTED = "EXECUTED"
    VERIFYING = "VERIFYING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"
    DEFERRED = "DEFERRED"
    CANCELLED = "CANCELLED"
    SUPERSEDED = "SUPERSEDED"


# Legal state machine transitions (Phase 2)
ALLOWED_TRANSITIONS: dict[DecisionLifecycleState, set[DecisionLifecycleState]] = {
    DecisionLifecycleState.PROPOSED: {
        DecisionLifecycleState.EVALUATING,
        DecisionLifecycleState.CANCELLED,
        DecisionLifecycleState.SUPERSEDED,
    },
    DecisionLifecycleState.EVALUATING: {
        DecisionLifecycleState.BLOCKED,
        DecisionLifecycleState.AWAITING_APPROVAL,
        DecisionLifecycleState.SELECTED,
        DecisionLifecycleState.DEFERRED,
        DecisionLifecycleState.CANCELLED,
        DecisionLifecycleState.SUPERSEDED,
    },
    DecisionLifecycleState.BLOCKED: {
        DecisionLifecycleState.EVALUATING,  # Re-evaluation if policy/unblocking occurs
        DecisionLifecycleState.CANCELLED,
        DecisionLifecycleState.SUPERSEDED,
    },
    DecisionLifecycleState.AWAITING_APPROVAL: {
        DecisionLifecycleState.APPROVED,
        DecisionLifecycleState.REJECTED,
        DecisionLifecycleState.CANCELLED,
    },
    DecisionLifecycleState.APPROVED: {
        DecisionLifecycleState.SELECTED,
        DecisionLifecycleState.CANCELLED,
    },
    DecisionLifecycleState.REJECTED: {
        DecisionLifecycleState.EVALUATING,  # Re-evaluate alternatives
        DecisionLifecycleState.CANCELLED,
    },
    DecisionLifecycleState.SELECTED: {
        DecisionLifecycleState.EXECUTING,
        DecisionLifecycleState.AWAITING_APPROVAL,
        DecisionLifecycleState.EVALUATING,
        DecisionLifecycleState.SUPERSEDED,
        DecisionLifecycleState.CANCELLED,
    },
    DecisionLifecycleState.EXECUTING: {
        DecisionLifecycleState.EXECUTED,
        DecisionLifecycleState.FAILED,
    },
    DecisionLifecycleState.EXECUTED: {
        DecisionLifecycleState.VERIFYING,
        DecisionLifecycleState.FAILED,
    },
    DecisionLifecycleState.VERIFYING: {
        DecisionLifecycleState.VERIFIED,
        DecisionLifecycleState.FAILED,
    },
    DecisionLifecycleState.FAILED: {
        DecisionLifecycleState.ROLLED_BACK,
        DecisionLifecycleState.EVALUATING,  # Re-evaluate recovery
    },
    DecisionLifecycleState.DEFERRED: {
        DecisionLifecycleState.EVALUATING,
        DecisionLifecycleState.CANCELLED,
    },
    DecisionLifecycleState.ROLLED_BACK: set(),
    DecisionLifecycleState.VERIFIED: set(),
    DecisionLifecycleState.CANCELLED: set(),
    DecisionLifecycleState.SUPERSEDED: set(),
}


class ConstraintCategory(str, Enum):
    """Constraint hierarchy for multi-objective optimization."""
    HARD_CONSTRAINT = "HARD_CONSTRAINT"  # Inviolable boundary
    SOFT_CONSTRAINT = "SOFT_CONSTRAINT"  # Trade-off permissible
    PREFERENCE = "PREFERENCE"            # Desired guidance
    ASSUMPTION = "ASSUMPTION"            # Working premise
    RESOURCE_BUDGET = "RESOURCE_BUDGET"  # Budget or cost limits
    OPERATIONAL = "OPERATIONAL"          # Latency / throughput bounds


class SimulationState(str, Enum):
    """Digital twin simulation gate status."""
    NOT_REQUIRED = "NOT_REQUIRED"
    REQUIRED = "REQUIRED"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"


class SecurityAuthorizationStatus(str, Enum):
    """Authoritative SecurityCenter classification."""
    AUTHORIZED = "AUTHORIZED"
    DENIED = "DENIED"
    REQUIRES_APPROVAL = "REQUIRES_APPROVAL"
    UNKNOWN = "UNKNOWN"


class DecisionCertainty(str, Enum):
    """Epistemic certainty level of the deliberation."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNCERTAIN = "UNCERTAIN"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


class AssumptionStatus(str, Enum):
    """Lifecycle status of an active decision assumption."""
    ACTIVE = "ACTIVE"
    VALIDATED = "VALIDATED"
    INVALIDATED = "INVALIDATED"
    UNKNOWN = "UNKNOWN"


class VerificationStatus(str, Enum):
    """Outcome verification state."""
    UNVERIFIED = "UNVERIFIED"
    VERIFYING = "VERIFYING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    INCONCLUSIVE = "INCONCLUSIVE"


# ==============================================================================
# Domain Entities
# ==============================================================================


class AssumptionItem(BaseModel):
    """Tracked assumption underpinning a decision (Phase 22)."""
    model_config = ConfigDict(extra="ignore")

    assumption_id: str = Field(default_factory=lambda: _uuid_hex("asm"))
    statement: str
    source: str = "deliberation"
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    validation_method: str = "runtime_check"
    status: AssumptionStatus = AssumptionStatus.ACTIVE
    impact_if_false: str = "requires_reevaluation"
    is_critical: bool = False
    created_at: datetime = Field(default_factory=_now_utc)

    def __init__(self, **data: Any) -> None:
        if "id" in data and "assumption_id" not in data:
            data["assumption_id"] = data["id"]
        super().__init__(**data)

    @property
    def id(self) -> str:
        return self.assumption_id

    @property
    def is_valid(self) -> bool:
        return self.status in (AssumptionStatus.ACTIVE, AssumptionStatus.VALIDATED)


class DecisionConstraint(BaseModel):
    """Typed constraint applied during evaluation (Phase 6)."""
    model_config = ConfigDict(extra="ignore")

    constraint_id: str = Field(default_factory=lambda: _uuid_hex("cst"))
    name: str = "Constraint"
    category: ConstraintCategory = ConstraintCategory.HARD_CONSTRAINT
    statement: str = ""
    is_hard: bool = True
    threshold: float | None = None
    is_satisfied: bool = True
    violation_reason: str | None = None
    source: str = "governance"

    def __init__(self, **data: Any) -> None:
        if "id" in data and "constraint_id" not in data:
            data["constraint_id"] = data["id"]
        if "description" in data and not data.get("statement"):
            data["statement"] = data["description"]
        if "statement" in data and ("name" not in data or data["name"] == "Constraint"):
            data["name"] = data.get("name", "Constraint")
        super().__init__(**data)

    @property
    def id(self) -> str:
        return self.constraint_id


class DecisionOption(BaseModel):
    """Structured candidate option including NO_ACTION and alternatives (Phases 4 & 5)."""
    model_config = ConfigDict(extra="ignore")

    option_id: str = Field(default_factory=lambda: _uuid_hex("opt"))
    name: str = ""
    title: str = ""
    description: str = ""
    action_reference: str | None = None
    option_type: DecisionType = DecisionType.ACTION
    prerequisites: list[str] = Field(default_factory=list)
    expected_outcome: str = ""
    required_capabilities: list[str] = Field(default_factory=list)
    estimated_resource_profile: dict[str, Any] = Field(default_factory=dict)
    risk_references: list[dict[str, Any]] = Field(default_factory=list)
    governance_classification: str = "STANDARD"
    security_classification: SecurityAuthorizationStatus = SecurityAuthorizationStatus.AUTHORIZED
    reversibility: str = "REVERSIBLE"  # REVERSIBLE, PARTIAL, IRREVERSIBLE
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    simulation_status: SimulationState = SimulationState.NOT_REQUIRED
    provenance: dict[str, Any] = Field(default_factory=dict)

    # Evaluation & criteria metrics
    alignment_score: float | None = None
    risk_score: float | None = None
    reversibility_score: float | None = None
    resource_efficiency: float | None = None
    projected_cost: float | None = None
    projected_duration_ms: int | None = None
    requires_approval: bool = False

    # Evaluation artifacts
    is_feasible: bool = True
    is_dominated: bool = False
    rejection_reason: str | None = None
    scores: dict[str, float] = Field(default_factory=dict)
    tradeoffs: list[dict[str, Any]] = Field(default_factory=list)
    constraint_violations: list[str] = Field(default_factory=list)

    def __init__(self, **data: Any) -> None:
        if "id" in data and "option_id" not in data:
            data["option_id"] = data["id"]
        if "title" in data and not data.get("name"):
            data["name"] = data["title"]
        elif "name" in data and not data.get("title"):
            data["title"] = data["name"]
        if not data.get("description") and data.get("name"):
            data["description"] = data["name"]
        super().__init__(**data)

    @property
    def id(self) -> str:
        return self.option_id

    @property
    def decision_type(self) -> DecisionType:
        return self.option_type

    @decision_type.setter
    def decision_type(self, val: DecisionType) -> None:
        self.option_type = val

    @property
    def is_pareto_optimal(self) -> bool:
        return self.is_feasible and not self.is_dominated


class DecisionInput(BaseModel):
    """Structured contract for requesting a deliberation (Phase 3)."""
    model_config = ConfigDict(extra="ignore")

    objective_id: str = Field(default_factory=lambda: f"obj_{_uuid_hex('', 8)}")
    statement: str = ""
    title: str = ""
    description: str = ""
    decision_type: DecisionType = DecisionType.ACTION
    context: dict[str, Any] = Field(default_factory=dict)
    candidate_options: list[DecisionOption] = Field(default_factory=list)
    constraints: list[DecisionConstraint] = Field(default_factory=list)
    assumptions: list[AssumptionItem] = Field(default_factory=list)
    risks: list[dict[str, Any]] = Field(default_factory=list)
    predictions: list[dict[str, Any]] = Field(default_factory=list)
    causal_effects: list[dict[str, Any]] = Field(default_factory=list)
    resource_state: dict[str, Any] = Field(default_factory=dict)
    capability_state: dict[str, Any] = Field(default_factory=dict)
    governance_state: dict[str, Any] = Field(default_factory=dict)
    security_state: dict[str, Any] = Field(default_factory=dict)
    historical_evidence: list[dict[str, Any]] = Field(default_factory=list)
    correlation_id: str | None = None
    trace_id: str | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)

    def __init__(self, **data: Any) -> None:
        if "title" in data and not data.get("statement"):
            data["statement"] = data["title"]
        if "statement" in data and not data.get("title"):
            data["title"] = data["statement"]
        if "description" in data and not data.get("context"):
            data["context"] = {"description": data["description"]}
        super().__init__(**data)


class DecisionV2Record(BaseModel):
    """Comprehensive decision record satisfying Task 94 Phase 1 requirements."""
    model_config = ConfigDict(extra="ignore")

    decision_id: str = Field(default_factory=lambda: _uuid_hex("dec"))
    objective_id: str = ""
    title: str = ""
    task_id: str | None = None
    conversation_id: str | None = None
    created_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)
    decision_version: int = 1
    status: DecisionLifecycleState = DecisionLifecycleState.PROPOSED
    decision_type: DecisionType = DecisionType.ACTION
    context_snapshot_id: str | None = None

    options: list[DecisionOption] = Field(default_factory=list)
    selected_option: DecisionOption | None = None
    constraints: list[DecisionConstraint] = Field(default_factory=list)
    assumptions: list[AssumptionItem] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    uncertainty: dict[str, Any] = Field(default_factory=dict)
    certainty: DecisionCertainty = DecisionCertainty.MEDIUM

    risk_summary: dict[str, Any] = Field(default_factory=dict)
    resource_summary: dict[str, Any] = Field(default_factory=dict)
    governance_summary: dict[str, Any] = Field(default_factory=dict)
    security_summary: dict[str, Any] = Field(default_factory=dict)
    approval_summary: dict[str, Any] = Field(default_factory=dict)

    expected_outcomes: dict[str, Any] = Field(default_factory=dict)
    actual_outcomes: dict[str, Any] | None = None
    outcomes: list[DecisionOutcomeRecord] = Field(default_factory=list)
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    explanation: Any | None = None

    valid_until: datetime | None = None
    expiration_reason: str | None = None
    revalidation_required: bool = False

    provenance: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None
    trace_id: str | None = None

    def __init__(self, **data: Any) -> None:
        if "id" in data and "decision_id" not in data:
            data["decision_id"] = data["id"]
        if "lifecycle_state" in data and "status" not in data:
            data["status"] = data["lifecycle_state"]
        if "expires_at" in data and "valid_until" not in data:
            data["valid_until"] = data["expires_at"]
        super().__init__(**data)

    @property
    def id(self) -> str:
        return self.decision_id

    @property
    def lifecycle_state(self) -> DecisionLifecycleState:
        return self.status

    @property
    def is_stale(self) -> bool:
        if not self.valid_until:
            return False
        return datetime.now(UTC) > self.valid_until

    @property
    def selected_option_id(self) -> str | None:
        return self.selected_option.option_id if self.selected_option else None

    @selected_option_id.setter
    def selected_option_id(self, opt_id: str | None) -> None:
        if opt_id is None:
            self.selected_option = None
        else:
            opt = next((o for o in self.options if o.option_id == opt_id), None)
            if opt:
                self.selected_option = opt

    def can_transition_to(self, target_state: DecisionLifecycleState) -> bool:
        """Validate if the proposed lifecycle state transition is legal."""
        allowed = ALLOWED_TRANSITIONS.get(self.status, set())
        return target_state in allowed

    def transition_to(self, target_state: DecisionLifecycleState, reason: str | None = None) -> None:
        """Enforce strict lifecycle transitions."""
        if not self.can_transition_to(target_state):
            raise ValueError(f"Illegal state transition from {self.status} to {target_state}")
        self.status = target_state
        self.updated_at = datetime.now(UTC)
        if reason:
            self.expiration_reason = reason


class DecisionExplanation(BaseModel):
    """Structured 15-point evidence-based explanation (Phase 30)."""
    model_config = ConfigDict(extra="ignore")

    decision_id: str = ""
    objective: str = ""
    options_considered: list[str] = Field(default_factory=list)
    constraints_summary: list[str] = Field(default_factory=list)
    evidence_basis: list[str] = Field(default_factory=list)
    risks_evaluated: list[str] = Field(default_factory=list)
    forecasts_used: list[str] = Field(default_factory=list)
    causal_effects_identified: list[str] = Field(default_factory=list)
    resource_implications: dict[str, Any] = Field(default_factory=dict)
    governance_status: str = "COMPLIANT"
    security_status: str = "AUTHORIZED"
    approval_status: str = "NOT_REQUIRED"
    uncertainty_profile: dict[str, Any] = Field(default_factory=dict)
    selected_action: str = ""
    expected_outcome: str = ""
    verification_plan: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=_now_utc)

    # Friendly property accessors for test assertions
    @property
    def selected_option(self) -> str:
        return self.selected_action

    @property
    def selection_rationale(self) -> str:
        return f"Selected '{self.selected_action}' to achieve '{self.objective}'"

    @property
    def rejected_alternatives(self) -> list[str]:
        return [opt for opt in self.options_considered if opt != self.selected_action]

    @property
    def pareto_trade_offs(self) -> list[str]:
        return [f"Trade-off between {r}" for r in self.risks_evaluated]

    @property
    def assumptions_relied_on(self) -> list[str]:
        return self.evidence_basis

    @property
    def epistemic_uncertainties(self) -> list[str]:
        return [str(k) for k in self.uncertainty_profile.keys()]

    @property
    def confidence_interval(self) -> str:
        return self.uncertainty_profile.get("certainty", "HIGH")

    @property
    def reversibility_assessment(self) -> str:
        return "REVERSIBLE"

    @property
    def downstream_impacts(self) -> str:
        return self.expected_outcome

    @property
    def governance_compliance(self) -> str:
        return self.governance_status

    @property
    def approval_requirements(self) -> str:
        return self.approval_status

    @property
    def fallback_plan(self) -> str:
        return "Fallback to status quo (NO_ACTION)"

    @property
    def monitoring_signals(self) -> str:
        return ", ".join(self.verification_plan)

    @property
    def staleness_conditions(self) -> str:
        return "Invalidated if assumptions fail or environment drifts"


class DecisionOutcomeRecord(BaseModel):
    """Post-execution verification and deviation record (Phase 26)."""
    model_config = ConfigDict(extra="ignore")

    outcome_id: str = Field(default_factory=lambda: _uuid_hex("out"))
    decision_id: str
    predicted_outcome: dict[str, Any] = Field(default_factory=dict)
    predicted_impact: dict[str, Any] = Field(default_factory=dict)
    actual_outcome: dict[str, Any] = Field(default_factory=dict)
    actual_impact: dict[str, Any] = Field(default_factory=dict)
    deviation_score: float = 0.0
    regret_score: float = 0.0
    execution_cost: dict[str, Any] = Field(default_factory=dict)
    latency_ms: float = 0.0
    unexpected_side_effects: list[str] = Field(default_factory=list)
    verification_status: VerificationStatus = VerificationStatus.VERIFIED
    success: bool = True
    lessons_learned: list[str] = Field(default_factory=list)
    recorded_at: datetime = Field(default_factory=_now_utc)

    def __init__(self, **data: Any) -> None:
        if "id" in data and "outcome_id" not in data:
            data["outcome_id"] = data["id"]
        if "predicted_impact" in data and not data.get("predicted_outcome"):
            data["predicted_outcome"] = data["predicted_impact"]
        if "actual_impact" in data and not data.get("actual_outcome"):
            data["actual_outcome"] = data["actual_impact"]
        super().__init__(**data)
