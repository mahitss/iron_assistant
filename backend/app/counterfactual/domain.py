"""Domain models, value objects, and lifecycle definitions for Task 113:
Autonomous Counterfactual, Intervention Analysis, What-If Simulation & Causal Experiment Planning Engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
import uuid


class CounterfactualLifecycleStage(str, Enum):
    """Lifecycle stages for counterfactual analyses."""
    REQUESTED = "REQUESTED"
    SCOPING = "SCOPING"
    BASELINE_BUILDING = "BASELINE_BUILDING"
    SCENARIO_BUILDING = "SCENARIO_BUILDING"
    VALIDATING = "VALIDATING"
    SIMULATING = "SIMULATING"
    EVALUATING = "EVALUATING"
    COMPARING = "COMPARING"
    PROVISIONAL = "PROVISIONAL"
    EVIDENCE_PENDING = "EVIDENCE_PENDING"
    READY_FOR_DECISION = "READY_FOR_DECISION"
    BLOCKED = "BLOCKED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    AUTHORIZED = "AUTHORIZED"
    EXECUTING = "EXECUTING"
    OBSERVING = "OBSERVING"
    VERIFYING = "VERIFYING"
    VERIFIED = "VERIFIED"
    CONTRADICTED = "CONTRADICTED"
    FAILED = "FAILED"
    STALE = "STALE"
    SUPERSEDED = "SUPERSEDED"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"


class CounterfactualType(str, Enum):
    """Types of counterfactual inquiries."""
    ABSTENTION = "ABSTENTION"          # "What if X had not happened?"
    SUBSTITUTION = "SUBSTITUTION"      # "What if X were replaced by Y?"
    TIMING = "TIMING"                  # "What if X happened earlier/later?"
    DOSAGE = "DOSAGE"                  # "What if X were stronger/weaker?"
    RESOURCE = "RESOURCE"              # "What if resource allocation changed?"
    CAPABILITY = "CAPABILITY"          # "What if capability Y were unavailable?"
    DEPENDENCY = "DEPENDENCY"          # "What if dependency Z failed?"
    POLICY = "POLICY"                  # "What if policy condition changed?"
    ENVIRONMENT = "ENVIRONMENT"        # "What if external condition changed?"
    COMBINATIONAL = "COMBINATIONAL"    # "What if X and Y changed together?"


class BaselineType(str, Enum):
    """Types of baseline reference states."""
    HISTORICAL = "HISTORICAL"
    CURRENT = "CURRENT"
    RECONSTRUCTED = "RECONSTRUCTED"
    SIMULATED = "SIMULATED"
    EXPECTED = "EXPECTED"
    NO_ACTION = "NO_ACTION"
    ALTERNATIVE_ACTION = "ALTERNATIVE_ACTION"


class InterventionScope(str, Enum):
    """Scope of intervention applicability."""
    LOCAL = "LOCAL"
    ENTITY = "ENTITY"
    SERVICE = "SERVICE"
    WORKFLOW = "WORKFLOW"
    MISSION = "MISSION"
    SYSTEM = "SYSTEM"
    ENVIRONMENT = "ENVIRONMENT"
    SIMULATION_ONLY = "SIMULATION_ONLY"


class AssumptionStatus(str, Enum):
    """Causal assumption validity state."""
    SUPPORTED = "SUPPORTED"
    PLAUSIBLE = "PLAUSIBLE"
    WEAK = "WEAK"
    UNKNOWN = "UNKNOWN"
    CONTRADICTED = "CONTRADICTED"


class RobustnessClassification(str, Enum):
    """Robustness classification across parameter/environment variations."""
    ROBUST = "ROBUST"
    SENSITIVE = "SENSITIVE"
    FRAGILE = "FRAGILE"
    UNKNOWN = "UNKNOWN"


class VerificationOutcome(str, Enum):
    """Outcome of comparing counterfactual prediction against reality."""
    VERIFIED = "VERIFIED"
    CONTRADICTED = "CONTRADICTED"
    DEVIATED = "DEVIATED"
    UNRESOLVED = "UNRESOLVED"


class CounterfactualFailureReason(str, Enum):
    """Taxonomy of counterfactual analysis failures."""
    BASELINE_INVALID = "BASELINE_INVALID"
    INTERVENTION_INVALID = "INTERVENTION_INVALID"
    CAUSAL_MODEL_INSUFFICIENT = "CAUSAL_MODEL_INSUFFICIENT"
    SIMULATION_FAILURE = "SIMULATION_FAILURE"
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    MODEL_STALE = "MODEL_STALE"
    WORLD_STATE_STALE = "WORLD_STATE_STALE"
    CONTEXT_STALE = "CONTEXT_STALE"
    SECURITY_BLOCKED = "SECURITY_BLOCKED"
    GOVERNANCE_BLOCKED = "GOVERNANCE_BLOCKED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    EMERGENCY_STOP = "EMERGENCY_STOP"
    VERIFICATION_UNAVAILABLE = "VERIFICATION_UNAVAILABLE"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"
    CONTRADICTORY_EVIDENCE = "CONTRADICTORY_EVIDENCE"
    TIMEOUT = "TIMEOUT"
    UNKNOWN = "UNKNOWN"


@dataclass
class CounterfactualBaseline:
    """Explicit factual baseline against which counterfactuals are evaluated."""
    baseline_id: str = field(default_factory=lambda: f"base_{uuid.uuid4().hex[:12]}")
    baseline_type: BaselineType = BaselineType.CURRENT
    target_entity: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    state_snapshot: dict[str, Any] = field(default_factory=dict)
    source_versions: dict[str, str] = field(default_factory=dict)
    known_gaps: list[str] = field(default_factory=list)
    uncertainty_summary: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)
    is_historical_reconstruction: bool = False


@dataclass
class InterventionAssumption:
    """Assumptions required for an intervention model to hold."""
    assumption_id: str = field(default_factory=lambda: f"asm_{uuid.uuid4().hex[:8]}")
    description: str = ""
    status: AssumptionStatus = AssumptionStatus.PLAUSIBLE
    supporting_evidence: list[str] = field(default_factory=list)
    contradicting_evidence: list[str] = field(default_factory=list)
    sensitivity_weight: float = 0.5


@dataclass
class InterventionConstraint:
    """Invariants and constraints that an intervention must satisfy."""
    constraint_id: str = field(default_factory=lambda: f"cst_{uuid.uuid4().hex[:8]}")
    description: str = ""
    is_hard_invariant: bool = True
    satisfied: bool = True
    violation_reason: str = ""


@dataclass
class InterventionMechanism:
    """Causal mechanism explaining how intervention affects outcome."""
    mechanism_id: str = field(default_factory=lambda: f"mec_{uuid.uuid4().hex[:8]}")
    treatment_variable: str = ""
    mediating_nodes: list[str] = field(default_factory=list)
    target_variable: str = ""
    pathway_description: str = ""
    confidence: float = 0.5


@dataclass
class Intervention:
    """Specification of a hypothetical intervention."""
    intervention_id: str = field(default_factory=lambda: f"intv_{uuid.uuid4().hex[:12]}")
    name: str = ""
    target: str = ""
    scope: InterventionScope = InterventionScope.SERVICE
    changes: dict[str, Any] = field(default_factory=dict)
    intervention_type: CounterfactualType = CounterfactualType.RESOURCE
    assumptions: list[InterventionAssumption] = field(default_factory=list)
    constraints: list[InterventionConstraint] = field(default_factory=list)
    mechanisms: list[InterventionMechanism] = field(default_factory=list)
    is_reversible: bool = True
    reversibility_plan: str = ""
    estimated_resource_cost: dict[str, float] = field(default_factory=dict)
    risk_level: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    requires_approval: bool = False
    is_blocked: bool = False
    block_reason: str = ""
    environment_label: str = "SIMULATION_ONLY"
    is_hypothetical: bool = True


@dataclass
class InterventionPrediction:
    """Predicted outcome trajectory under an intervention."""
    prediction_id: str = field(default_factory=lambda: f"prd_{uuid.uuid4().hex[:12]}")
    intervention_id: str = ""
    predicted_state: dict[str, Any] = field(default_factory=dict)
    state_transitions: list[dict[str, Any]] = field(default_factory=list)
    metric_trajectories: dict[str, list[float]] = field(default_factory=dict)
    uncertainty_intervals: dict[str, tuple[float, float]] = field(default_factory=dict)
    expected_timing_seconds: float = 0.0
    confidence: float = 0.5
    causal_support_level: str = "MODERATE"
    is_hypothetical: bool = True
    environment_label: str = "SIMULATION_ONLY"


@dataclass
class InterventionOutcome:
    """Multi-dimensional outcome assessment across system dimensions."""
    mission_success_delta: float = 0.0      # [-1.0, 1.0]
    goal_progress_delta: float = 0.0        # [-1.0, 1.0]
    system_health_delta: float = 0.0        # [-1.0, 1.0]
    reliability_delta: float = 0.0          # [-1.0, 1.0]
    risk_score: float = 0.2                 # [0.0, 1.0]
    resource_usage: dict[str, float] = field(default_factory=dict)
    latency_delta_ms: float = 0.0
    cost_estimate_units: float = 0.0
    safety_score: float = 0.95              # [0.0, 1.0]
    reversibility_score: float = 1.0        # [0.0, 1.0]
    capability_impact: str = "NEUTRAL"      # IMPROVED, NEUTRAL, DEGRADED
    user_impact: str = "NEUTRAL"
    external_impact: str = "NEUTRAL"


@dataclass
class CounterfactualScenario:
    """Concrete scenario pairing a baseline and candidate interventions."""
    scenario_id: str = field(default_factory=lambda: f"scen_{uuid.uuid4().hex[:12]}")
    scenario_name: str = ""
    baseline_id: str = ""
    interventions: list[Intervention] = field(default_factory=list)
    scenario_type: CounterfactualType = CounterfactualType.RESOURCE
    simulation_budget_seconds: float = 5.0
    random_seed: int | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    prediction: InterventionPrediction | None = None
    outcome: InterventionOutcome | None = None
    is_no_action: bool = False
    is_hypothetical: bool = True


@dataclass
class InterventionComparisonItem:
    """Individual item in a structured side-by-side comparison."""
    scenario_id: str
    scenario_name: str
    is_no_action: bool
    predicted_summary: str
    key_assumptions: list[str]
    risk_level: str
    resource_cost_summary: str
    reversibility: str
    uncertainty_level: str
    confidence: float


@dataclass
class InterventionComparison:
    """Structured comparison across NO_ACTION and candidate interventions."""
    comparison_id: str = field(default_factory=lambda: f"cmp_{uuid.uuid4().hex[:12]}")
    baseline_scenario_id: str = ""
    candidate_scenario_ids: list[str] = field(default_factory=list)
    items: list[InterventionComparisonItem] = field(default_factory=list)
    dimensions_evaluated: list[str] = field(default_factory=list)
    tradeoff_summary: str = ""
    recommended_option_for_decision: str | None = None
    no_action_viable: bool = True
    insufficient_evidence_warning: bool = False


@dataclass
class SensitivityResult:
    """Result of sensitivity analysis over assumptions and parameters."""
    influential_parameters: list[dict[str, Any]] = field(default_factory=list)
    critical_assumptions: list[str] = field(default_factory=list)
    elasticity_map: dict[str, float] = field(default_factory=dict)
    summary: str = ""


@dataclass
class RobustnessAssessment:
    """Robustness classification across variations."""
    classification: RobustnessClassification = RobustnessClassification.ROBUST
    stability_score: float = 0.8  # [0.0, 1.0]
    evaluated_variations_count: int = 0
    failure_scenarios_count: int = 0
    vulnerabilities: list[str] = field(default_factory=list)


@dataclass
class InformationGainProposal:
    """Candidate observation or experiment designed to reduce hypothesis entropy."""
    proposal_id: str = field(default_factory=lambda: f"ig_{uuid.uuid4().hex[:8]}")
    target_hypotheses: list[str] = field(default_factory=list)
    discriminating_observation: str = ""
    candidate_experiment_type: str = "OBSERVATIONAL"  # OBSERVATIONAL, SHADOW, CANARY, A_B, REPLAY
    expected_information_gain: float = 0.7  # [0.0, 1.0]
    cost_estimate: float = 0.1
    latency_seconds: float = 5.0
    safety_risk: str = "LOW"
    observability_metric: str = ""


@dataclass
class InterventionExperimentPlan:
    """Causal experiment plan integrating with Task 105 ExperimentEngine."""
    plan_id: str = field(default_factory=lambda: f"exp_plan_{uuid.uuid4().hex[:12]}")
    hypothesis_id: str = ""
    treatment: dict[str, Any] = field(default_factory=dict)
    control: dict[str, Any] = field(default_factory=dict)
    metric: str = ""
    stop_conditions: list[str] = field(default_factory=list)
    rollback_strategy: str = ""
    requires_human_approval: bool = True
    is_governance_compliant: bool = True
    is_authorized: bool = False


@dataclass
class InterventionVerification:
    """Prediction-vs-reality verification record after actual real-world execution."""
    verification_id: str = field(default_factory=lambda: f"cf_ver_{uuid.uuid4().hex[:12]}")
    counterfactual_id: str = ""
    executed_intervention_id: str = ""
    predicted_state: dict[str, Any] = field(default_factory=dict)
    observed_state: dict[str, Any] = field(default_factory=dict)
    outcome: VerificationOutcome = VerificationOutcome.UNRESOLVED
    state_deviation_score: float = 0.0
    metric_deviations: dict[str, float] = field(default_factory=dict)
    explanation_of_deviation: str = ""
    calibration_feedback_emitted: bool = False
    verified_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class CounterfactualSnapshot:
    """Immutable point-in-time snapshot of counterfactual analysis."""
    snapshot_id: str = field(default_factory=lambda: f"cf_snap_{uuid.uuid4().hex[:12]}")
    analysis_id: str = ""
    version: int = 1
    baseline_snapshot: dict[str, Any] = field(default_factory=dict)
    scenarios_snapshot: list[dict[str, Any]] = field(default_factory=list)
    comparison_snapshot: dict[str, Any] = field(default_factory=dict)
    assumptions_snapshot: list[dict[str, Any]] = field(default_factory=list)
    causal_model_version: str = "v1.0"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    content_hash: str = ""


@dataclass
class CounterfactualRequest:
    """Typed request for counterfactual inquiry."""
    target_entity: str
    target_variable: str | None = None
    question: str = "What would happen if we intervene?"
    counterfactual_type: CounterfactualType = CounterfactualType.RESOURCE
    baseline_type: BaselineType = BaselineType.CURRENT
    baseline_time: datetime | None = None
    candidate_changes: list[dict[str, Any]] = field(default_factory=list)
    include_no_action: bool = True
    causal_depth_limit: int = 4
    simulation_budget_seconds: float = 10.0
    require_reversibility: bool = True
    requested_by: str = "user"


@dataclass
class CounterfactualAnalysis:
    """Authoritative counterfactual analysis aggregation record."""
    analysis_id: str = field(default_factory=lambda: f"cfa_{uuid.uuid4().hex[:12]}")
    version: int = 1
    target_entity: str = ""
    question: str = ""
    lifecycle_stage: CounterfactualLifecycleStage = CounterfactualLifecycleStage.REQUESTED
    counterfactual_type: CounterfactualType = CounterfactualType.RESOURCE
    baseline: CounterfactualBaseline = field(default_factory=CounterfactualBaseline)
    scenarios: list[CounterfactualScenario] = field(default_factory=list)
    comparison: InterventionComparison | None = None
    sensitivity: SensitivityResult | None = None
    robustness: RobustnessAssessment | None = None
    information_gain_proposals: list[InformationGainProposal] = field(default_factory=list)
    experiment_plan: InterventionExperimentPlan | None = None
    verification: InterventionVerification | None = None
    causal_model_version: str = "v1.0"
    is_stale: bool = False
    stale_reason: str = ""
    error_message: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    environment_label: str = "SIMULATION_ONLY"
    is_hypothetical: bool = True
