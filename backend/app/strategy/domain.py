"""Domain entities, enums, and lifecycle state machines for KAIRO Strategy Engine (Task 106).

Core Architectural Invariants:
1. LEARNED STRATEGY != POLICY AUTHORITY (Governance remains sole policy authority)
2. LEARNED STRATEGY != SECURITY AUTHORITY (SecurityCenter remains sole authorization authority)
3. LEARNED STRATEGY != GOAL (Missions/Intents define goals; strategies are methods)
4. LEARNED STRATEGY != DECISION (Decision Intelligence chooses actions; Strategy Engine provides candidates)
5. LEARNED STRATEGY != FACT (Strategies are empirical heuristics with uncertainty)
6. STRATEGY != ACTION (Strategy Engine NEVER executes actions directly)
7. EMERGENCY_STOP ABSOLUTE PRIMACY (EmergencyStop stops privileged strategy application)
"""

from __future__ import annotations

import enum
import hashlib
import json
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


def generate_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class StrategyCategory(str, enum.Enum):
    """Canonical categories of learned operational strategies."""

    PLANNING = "PLANNING"
    DECISION = "DECISION"
    RECOVERY = "RECOVERY"
    RESOURCE = "RESOURCE"
    RETRIEVAL = "RETRIEVAL"
    CONTEXT = "CONTEXT"
    MEMORY = "MEMORY"
    AGENT_COORDINATION = "AGENT_COORDINATION"
    SITUATION_RESPONSE = "SITUATION_RESPONSE"
    FORECAST_RESPONSE = "FORECAST_RESPONSE"
    RELIABILITY = "RELIABILITY"
    MISSION_EXECUTION = "MISSION_EXECUTION"
    OBSERVATION = "OBSERVATION"
    VERIFICATION = "VERIFICATION"
    ERROR_HANDLING = "ERROR_HANDLING"
    PERFORMANCE = "PERFORMANCE"
    SECURITY_DEFENSE = "SECURITY_DEFENSE"


class StrategyStatus(str, enum.Enum):
    """Lifecycle states of an operational strategy."""

    CANDIDATE = "CANDIDATE"              # Newly generated pattern, awaiting validation
    DRAFT = "DRAFT"                      # Incomplete or under composition
    EVIDENCE_PENDING = "EVIDENCE_PENDING"# Requires empirical verification
    VALIDATING = "VALIDATING"            # Currently executing benchmark or experiment
    VALIDATED = "VALIDATED"              # Formally validated through evaluation/experiment
    AVAILABLE = "AVAILABLE"              # Promoted and ready for Decision Intelligence selection
    DEPRECATED = "DEPRECATED"            # Outdated or superseded by a newer version
    SUSPENDED = "SUSPENDED"              # Temporarily halted due to safety or regression flags
    CONFLICTED = "CONFLICTED"            # Mutually exclusive or opposing another strategy
    SUPERSEDED = "SUPERSEDED"            # Replaced by newer strategy version
    REJECTED = "REJECTED"                # Failed evaluation or disproven hypothesis
    EXPIRED = "EXPIRED"                  # Exceeded validity window or drifted


class ApplicabilityStatus(str, enum.Enum):
    """Status returned by ApplicabilityEngine."""

    APPLICABLE = "APPLICABLE"            # Conditions met, no contraindications
    NOT_APPLICABLE = "NOT_APPLICABLE"    # Context does not match conditions
    UNCERTAIN = "UNCERTAIN"              # Stale world-state or missing context
    BLOCKED = "BLOCKED"                  # Contraindication or EmergencyStop active


class ConflictType(str, enum.Enum):
    """Taxonomy of inter-strategy conflicts."""

    DIRECT = "DIRECT"                    # Explicitly contradictory actions
    CONDITIONAL = "CONDITIONAL"          # Mutually exclusive conditions
    TEMPORAL = "TEMPORAL"                # Divergent timing requirements (e.g. wait vs act now)
    ENVIRONMENTAL = "ENVIRONMENTAL"      # Incompatible environmental assumptions
    RESOURCE = "RESOURCE"                # Cumulative resource demands exceed budget
    CAPABILITY = "CAPABILITY"            # Contending for exclusive capability access
    OBJECTIVE = "OBJECTIVE"              # Trade-off in underlying optimization goals


class ContraindicationSeverity(str, enum.Enum):
    """Severity of a contraindication."""

    ADVISORY = "ADVISORY"                # Warning flag, decision engine may override
    RESTRICTED = "RESTRICTED"            # Requires heightened confidence or secondary approval
    PROHIBITIVE = "PROHIBITIVE"          # Hard block; strategy cannot be applied


class EvidenceSourceType(str, enum.Enum):
    """Provenance sources of empirical evidence."""

    TASK_103_EXPERIENCE = "TASK_103_EXPERIENCE"
    TASK_104_EVALUATION = "TASK_104_EVALUATION"
    TASK_105_EXPERIMENT = "TASK_105_EXPERIMENT"
    DECISION_OUTCOME = "DECISION_OUTCOME"
    MISSION_OUTCOME = "MISSION_OUTCOME"
    RECOVERY_OUTCOME = "RECOVERY_OUTCOME"
    COUNTEREXAMPLE = "COUNTEREXAMPLE"


class ConditionOperator(str, enum.Enum):
    """Comparison operators for conditions and preconditions."""

    EQUALS = "EQUALS"
    NOT_EQUALS = "NOT_EQUALS"
    GREATER_THAN = "GREATER_THAN"
    LESS_THAN = "LESS_THAN"
    IN_SET = "IN_SET"
    CONTAINS = "CONTAINS"
    EXISTS = "EXISTS"


class ProposalStatus(str, enum.Enum):
    """Status of strategy evolution proposals."""

    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CONVERTED_TO_EXPERIMENT = "CONVERTED_TO_EXPERIMENT"


class ReviewDecision(str, enum.Enum):
    """Decisions made during strategy review."""

    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    DEFERRED_TO_EXPERIMENT = "DEFERRED_TO_EXPERIMENT"


# ------------------------------------------------------------------------------
# Domain Entities (17 Persistent Abstractions)
# ------------------------------------------------------------------------------

class StrategyCondition(BaseModel):
    """Specific condition under which a strategy applies."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: generate_id("scond"))
    strategy_id: str
    version_id: Optional[str] = None
    condition_type: str                  # TASK_TYPE, MISSION_TYPE, SITUATION, RESOURCE_STATE, etc.
    operator: ConditionOperator = ConditionOperator.EQUALS
    field_path: str
    target_value: Any
    is_mandatory: bool = True
    created_at: datetime = Field(default_factory=utc_now)


class StrategyPrecondition(BaseModel):
    """Prerequisite state required before a strategy can be considered viable."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: generate_id("spre"))
    strategy_id: str
    version_id: Optional[str] = None
    precondition_type: str               # CAPABILITY_READY, RESOURCE_AVAILABLE, CONTEXT_PRESENT, etc.
    requirement_description: str
    verification_key: str
    expected_state: Any = True
    is_hard_requirement: bool = True
    created_at: datetime = Field(default_factory=utc_now)


class StrategyContraindication(BaseModel):
    """Explicit condition dictating DO NOT USE WHEN..."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: generate_id("scontra"))
    strategy_id: str
    version_id: Optional[str] = None
    contraindication_type: str           # RESOURCE_PRESSURE_HIGH, CAPABILITY_DEGRADED, etc.
    severity: ContraindicationSeverity = ContraindicationSeverity.PROHIBITIVE
    trigger_condition: Dict[str, Any] = Field(default_factory=dict)
    rationale: str
    created_at: datetime = Field(default_factory=utc_now)


class StrategyOutcome(BaseModel):
    """Expected outcome and success criteria along a specific dimension."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: generate_id("sout"))
    strategy_id: str
    version_id: Optional[str] = None
    dimension: str                       # QUALITY, LATENCY, RELIABILITY, RESOURCE_COST, etc.
    expected_delta: float
    variance: float = 0.0
    success_criteria: str
    measurement_unit: str = "percentage"
    created_at: datetime = Field(default_factory=utc_now)


class StrategyFailureMode(BaseModel):
    """Documented failure mode or risk."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: generate_id("sfail"))
    strategy_id: str
    version_id: Optional[str] = None
    failure_class: str                   # TIMEOUT, RESOURCE_SPIKE, ACCURACY_DROP, DRIFT, etc.
    symptom: str
    known_cause: str
    frequency: float = 0.0
    mitigation_strategy_id: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)


class StrategyEvidence(BaseModel):
    """Empirical observation, evaluation result, or counterexample."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: generate_id("sevi"))
    strategy_id: str
    version_id: Optional[str] = None
    source_type: EvidenceSourceType
    source_id: str
    is_counterexample: bool = False
    claim: str
    observed_metrics: Dict[str, Any] = Field(default_factory=dict)
    environmental_context: Dict[str, Any] = Field(default_factory=dict)
    capability_version: str = "1.0.0"
    confidence_weight: float = 1.0
    verified: bool = True
    sealed_hash_sha256: str = ""
    created_at: datetime = Field(default_factory=utc_now)

    def seal(self) -> str:
        payload = f"{self.strategy_id}:{self.source_type}:{self.source_id}:{self.claim}:{json.dumps(self.observed_metrics, sort_keys=True)}"
        self.sealed_hash_sha256 = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return self.sealed_hash_sha256


class StrategyApplicability(BaseModel):
    """Computed applicability evaluation for a specific context."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: generate_id("sapp"))
    strategy_id: str
    version_id: Optional[str] = None
    evaluation_context: Dict[str, Any] = Field(default_factory=dict)
    applicability_status: ApplicabilityStatus = ApplicabilityStatus.UNCERTAIN
    applicability_score: float = 0.0
    blocking_reasons: List[str] = Field(default_factory=list)
    uncertainty_reasons: List[str] = Field(default_factory=list)
    evaluated_at: datetime = Field(default_factory=utc_now)


class StrategyEvaluation(BaseModel):
    """Formal benchmark or experimental validation record."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: generate_id("seval"))
    strategy_id: str
    version_id: Optional[str] = None
    evaluator: str                       # task_104_benchmark, task_105_sandbox, peer_review
    evaluation_type: str = "BENCHMARK"
    sample_size: int = 0
    metrics: Dict[str, Any] = Field(default_factory=dict)
    verdict: str = "INCONCLUSIVE"        # PASS, FAIL, INCONCLUSIVE, REGRESSED
    holdout_passed: bool = False
    generalization_score: float = 0.0
    evaluation_evidence_ref: str = ""
    created_at: datetime = Field(default_factory=utc_now)


class StrategyUsage(BaseModel):
    """Record of a strategy presented or selected in decision-making."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: generate_id("suse"))
    strategy_id: str
    version_id: Optional[str] = None
    decision_id: str
    mission_id: Optional[str] = None
    situation_id: Optional[str] = None
    selected: bool = False
    execution_context: Dict[str, Any] = Field(default_factory=dict)
    used_at: datetime = Field(default_factory=utc_now)


class StrategyFeedback(BaseModel):
    """Outcome feedback from operational execution."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: generate_id("sfeed"))
    strategy_id: str
    version_id: Optional[str] = None
    usage_id: Optional[str] = None
    decision_id: Optional[str] = None
    action_id: Optional[str] = None
    outcome_status: str = "SUCCESS"      # SUCCESS, FAILURE, PARTIAL, UNKNOWN
    actual_metrics: Dict[str, Any] = Field(default_factory=dict)
    expected_vs_actual_delta: Dict[str, Any] = Field(default_factory=dict)
    observed_failure_mode: Optional[str] = None
    resource_cost: float = 0.0
    user_intervention: bool = False
    recorded_at: datetime = Field(default_factory=utc_now)


class StrategyConflict(BaseModel):
    """Detected conflict between two strategies."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: generate_id("sconf"))
    strategy_a_id: str
    strategy_b_id: str
    conflict_type: ConflictType = ConflictType.DIRECT
    description: str
    detected_under_context: Dict[str, Any] = Field(default_factory=dict)
    resolution_hint: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)


class StrategySupersession(BaseModel):
    """Lineage supersession between an older and newer strategy."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: generate_id("ssup"))
    superseded_strategy_id: str
    superseding_strategy_id: str
    superseded_version_id: Optional[str] = None
    superseding_version_id: Optional[str] = None
    reason: str
    evidence_summary: str
    superseded_at: datetime = Field(default_factory=utc_now)


class StrategyProposal(BaseModel):
    """Proposal to promote or adapt a strategy."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: generate_id("sprop"))
    proposal_title: str
    strategy_id: Optional[str] = None
    target_version: int = 1
    proposed_by: str = "experience_miner"
    rationale: str
    mined_patterns_summary: Dict[str, Any] = Field(default_factory=dict)
    status: ProposalStatus = ProposalStatus.DRAFT
    experiment_plan_id: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)


class StrategyReview(BaseModel):
    """Governance or operator review of a strategy proposal."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: generate_id("srev"))
    proposal_id: str
    reviewer: str = "kairo_governance"
    decision: ReviewDecision = ReviewDecision.APPROVED
    comments: str = ""
    governance_approval_id: Optional[str] = None
    reviewed_at: datetime = Field(default_factory=utc_now)


class StrategyEvent(BaseModel):
    """Audit log telemetry event."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: generate_id("sevt"))
    event_type: str                      # strategy.validated, strategy.drift_detected, etc.
    strategy_id: str
    version_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    dispatched_at: datetime = Field(default_factory=utc_now)


class StrategyVersion(BaseModel):
    """Immutable version of a strategy."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: generate_id("sver"))
    strategy_id: str
    version_number: int = 1
    parent_version_id: Optional[str] = None
    change_reason: str = "Initial version"
    change_description: str = ""
    parameters: Dict[str, Any] = Field(default_factory=dict)
    rules: List[Dict[str, Any]] = Field(default_factory=list)
    lifecycle_status: StrategyStatus = StrategyStatus.CANDIDATE
    confidence: float = 0.5
    uncertainty: float = 0.5
    evidence_count: int = 0
    counterexample_count: int = 0
    checksum_sha256: str = ""
    created_at: datetime = Field(default_factory=utc_now)

    def calculate_checksum(self) -> str:
        body = f"{self.strategy_id}:{self.version_number}:{self.parent_version_id}:{json.dumps(self.parameters, sort_keys=True)}:{json.dumps(self.rules, sort_keys=True)}"
        self.checksum_sha256 = hashlib.sha256(body.encode("utf-8")).hexdigest()
        return self.checksum_sha256


class Strategy(BaseModel):
    """Top-level persistent Strategy entity."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: generate_id("strat"))
    stable_id: str = Field(default_factory=lambda: f"strat_stable_{uuid.uuid4().hex[:8]}")
    name: str
    category: StrategyCategory = StrategyCategory.PLANNING
    objective: str = ""
    recommended_approach: str = ""
    current_version_id: Optional[str] = None
    lifecycle_status: StrategyStatus = StrategyStatus.CANDIDATE
    domain_scope: str = "SYSTEM"
    tested_domain: str = ""
    supported_domain: str = ""
    unknown_domain: str = ""
    confidence: float = 0.5              # [0.0, 1.0] multi-factor confidence
    uncertainty: float = 0.5             # [0.0, 1.0] epistemic uncertainty
    success_rate: float = 0.0            # Empirical success rate
    failure_rate: float = 0.0            # Empirical failure rate
    usage_count: int = 0
    last_validated_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None
    validity_window_seconds: int = 604800 # 7 days default
    is_stale: bool = False
    is_safety_critical: bool = False
    provenance_type: str = "EXPERIENCE_MINING"
    provenance_id: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    # In-memory relational attachments for easy retrieval and serialization
    versions: List[StrategyVersion] = Field(default_factory=list)
    conditions: List[StrategyCondition] = Field(default_factory=list)
    preconditions: List[StrategyPrecondition] = Field(default_factory=list)
    contraindications: List[StrategyContraindication] = Field(default_factory=list)
    outcomes: List[StrategyOutcome] = Field(default_factory=list)
    failure_modes: List[StrategyFailureMode] = Field(default_factory=list)
    evidences: List[StrategyEvidence] = Field(default_factory=list)
    counterexamples: List[StrategyEvidence] = Field(default_factory=list)
