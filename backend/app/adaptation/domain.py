"""Domain models, enums, lifecycle state machines, and invariants for Task 105:
KAIRO Autonomous Adaptation, Experiment Orchestration & Governed Evolution Engine.

Fundamental Invariant:
Kairo is allowed to become better. Kairo is NOT allowed to become uncontrolled.
Governed evolution != Uncontrolled self-modification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
import hashlib
import json
from typing import Any, Dict, List, Optional
import uuid


# ==============================================================================
# 1. ENUMS & CONSTANTS
# ==============================================================================

class ProgramStatus(str, Enum):
    """Lifecycle states for an AdaptationProgram."""
    DRAFT = "DRAFT"
    PROPOSED = "PROPOSED"
    REVIEWING = "REVIEWING"
    APPROVED = "APPROVED"
    EXPERIMENTING = "EXPERIMENTING"
    VALIDATING = "VALIDATING"
    SUCCESSFUL = "SUCCESSFUL"
    FAILED = "FAILED"
    INCONCLUSIVE = "INCONCLUSIVE"
    BLOCKED = "BLOCKED"
    SUPERSEDED = "SUPERSEDED"
    CANCELLED = "CANCELLED"


class VariantType(str, Enum):
    """Role and strategy of an experiment variant."""
    BASELINE = "BASELINE"          # Immutable control
    CANDIDATE = "CANDIDATE"        # Intervention candidate
    NO_ACTION = "NO_ACTION"        # Null-intervention control
    SHADOW = "SHADOW"              # Shadow execution
    REPLAY = "REPLAY"              # Historical trace replay
    SIMULATION = "SIMULATION"      # Sandbox simulation
    SYNTHETIC = "SYNTHETIC"        # Synthetic benchmark
    CANARY = "CANARY"              # Bounded production canary
    HOLDOUT = "HOLDOUT"            # Isolated holdout test
    FAULT_INJECTION = "FAULT_INJECTION"
    A_B = "A_B"


class VariantConfigType(str, Enum):
    """Target configuration domain affected by an experiment."""
    CAPABILITY_VERSION = "CAPABILITY_VERSION"
    CONFIGURATION = "CONFIGURATION"
    RETRIEVAL_STRATEGY = "RETRIEVAL_STRATEGY"
    CONTEXT_STRATEGY = "CONTEXT_STRATEGY"
    AGENT_TOPOLOGY = "AGENT_TOPOLOGY"
    MODEL_ROUTING = "MODEL_ROUTING"
    WORKFLOW_CONFIG = "WORKFLOW_CONFIG"
    RESOURCE_CONFIG = "RESOURCE_CONFIG"
    RETRY_POLICY = "RETRY_POLICY"
    EVALUATION_STRATEGY = "EVALUATION_STRATEGY"
    OBSERVABILITY_CONFIG = "OBSERVABILITY_CONFIG"


class SandboxEnvironment(str, Enum):
    """Safest applicable execution environment (ordered by strictness)."""
    STATIC_ANALYSIS = "STATIC_ANALYSIS"
    REPLAY = "REPLAY"
    SIMULATION = "SIMULATION"
    SHADOW = "SHADOW"
    ISOLATED_TEST = "ISOLATED_TEST"
    CANARY = "CANARY"
    CONTROLLED_PROD = "CONTROLLED_PROD"


class RunStatus(str, Enum):
    """Lifecycle states for an ExperimentRun."""
    CREATED = "CREATED"
    VALIDATING = "VALIDATING"
    BLOCKED = "BLOCKED"
    READY = "READY"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    INCONCLUSIVE = "INCONCLUSIVE"
    ROLLED_BACK = "ROLLED_BACK"
    UNKNOWN = "UNKNOWN"


class StopConditionType(str, Enum):
    """Hard and soft stop conditions for experiment execution."""
    # Hard stop conditions (always override experiment goals)
    SAFETY_VIOLATION = "SAFETY_VIOLATION"
    SECURITY_VIOLATION = "SECURITY_VIOLATION"
    EMERGENCY_STOP = "EMERGENCY_STOP"
    RESOURCE_EXHAUSTION = "RESOURCE_EXHAUSTION"
    EXCESSIVE_LATENCY = "EXCESSIVE_LATENCY"
    ERROR_RATE_THRESHOLD = "ERROR_RATE_THRESHOLD"
    REGRESSION_THRESHOLD = "REGRESSION_THRESHOLD"
    ROLLBACK_TRIGGER = "ROLLBACK_TRIGGER"
    BUDGET_EXHAUSTION = "BUDGET_EXHAUSTION"
    TIMEOUT = "TIMEOUT"
    # Soft stop conditions
    INSUFFICIENT_BENEFIT = "INSUFFICIENT_BENEFIT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    LOW_POWER = "LOW_POWER"
    UNEXPECTED_BEHAVIOR = "UNEXPECTED_BEHAVIOR"


class FailureTaxonomy(str, Enum):
    """Formal taxonomy for experiment and evolution failures."""
    DESIGN_ERROR = "DESIGN_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    IMPLEMENTATION_ERROR = "IMPLEMENTATION_ERROR"
    DATA_ERROR = "DATA_ERROR"
    ENVIRONMENT_ERROR = "ENVIRONMENT_ERROR"
    RESOURCE_ERROR = "RESOURCE_ERROR"
    SECURITY_FAILURE = "SECURITY_FAILURE"
    SAFETY_FAILURE = "SAFETY_FAILURE"
    GOVERNANCE_FAILURE = "GOVERNANCE_FAILURE"
    MEASUREMENT_FAILURE = "MEASUREMENT_FAILURE"
    EVALUATOR_FAILURE = "EVALUATOR_FAILURE"
    CAPABILITY_FAILURE = "CAPABILITY_FAILURE"
    UNKNOWN_FAILURE = "UNKNOWN_FAILURE"


class ComparisonVerdict(str, Enum):
    """Verdict of multi-objective comparison between baseline and candidate."""
    IMPROVED = "IMPROVED"
    REGRESSED = "REGRESSED"
    TRADEOFF = "TRADEOFF"
    INCONCLUSIVE = "INCONCLUSIVE"


class MetricDimension(str, Enum):
    """10 non-collapsible objective dimensions."""
    QUALITY = "quality"
    SAFETY = "safety"
    SECURITY = "security"
    RELIABILITY = "reliability"
    LATENCY = "latency"
    RESOURCE_COST = "resource_cost"
    MEMORY_USEFULNESS = "memory_usefulness"
    CONTEXT_QUALITY = "context_quality"
    USER_INTERVENTION = "user_intervention"
    MISSION_COMPLETION = "mission_completion"


class EvolutionProposalStatus(str, Enum):
    """Governance lifecycle for an EvolutionProposal."""
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DEPLOYED_CANARY = "DEPLOYED_CANARY"
    SUPERSEDED = "SUPERSEDED"
    CANCELLED = "CANCELLED"


class ReviewStatus(str, Enum):
    """Decision recorded by human reviewer or governance committee."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"


class ValidationStatus(str, Enum):
    """Status of pre-rollout multi-suite evolution validation."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    INCONCLUSIVE = "INCONCLUSIVE"


class AssignmentStrategy(str, Enum):
    """Deterministic assignment strategy for experiment population."""
    DETERMINISTIC_MODULO = "DETERMINISTIC_MODULO"
    HASH_RING = "HASH_RING"
    STRATIFIED = "STRATIFIED"


# ==============================================================================
# 2. CORE DOMAIN ENTITIES
# ==============================================================================

@dataclass
class AdaptationProgram:
    """Bounded improvement initiative addressing a verified evaluation finding or regression."""
    id: str = field(default_factory=lambda: f"prog_{uuid.uuid4().hex[:12]}")
    title: str = ""
    objective: str = ""
    problem_statement: str = ""
    originating_finding_id: Optional[str] = None
    affected_capability: str = ""
    affected_mission_id: Optional[str] = None
    affected_situation_id: Optional[str] = None
    affected_decision_id: Optional[str] = None
    baseline_id: str = ""
    hypothesis_id: Optional[str] = None
    constraints: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    expected_benefit: str = ""
    expected_cost: str = ""
    success_criteria: dict[str, Any] = field(default_factory=dict)
    failure_criteria: dict[str, Any] = field(default_factory=dict)
    safety_criteria: list[str] = field(default_factory=list)
    resource_budget: dict[str, Any] = field(default_factory=lambda: {
        "max_cost_usd": 10.0,
        "max_tokens": 100000,
        "cpu_quota": 2,
        "memory_mb": 2048,
    })
    time_budget_seconds: float = 3600.0
    governance_requirements: list[str] = field(default_factory=lambda: ["GovernanceEngine", "SecurityCenter"])
    rollback_strategy: str = "Revert to frozen baseline capability parameters"
    validation_strategy: str = "Multi-suite offline replay + simulation gate"
    owner_source: str = "autonomous_adaptation_engine"
    provenance: dict[str, Any] = field(default_factory=dict)
    version: str = "1.0.0"
    status: ProgramStatus = ProgramStatus.DRAFT
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def transition_to(self, new_status: ProgramStatus, reason: str = "") -> None:
        """Validate and apply state transition."""
        valid_transitions: dict[ProgramStatus, set[ProgramStatus]] = {
            ProgramStatus.DRAFT: {ProgramStatus.PROPOSED, ProgramStatus.APPROVED, ProgramStatus.CANCELLED},
            ProgramStatus.PROPOSED: {ProgramStatus.REVIEWING, ProgramStatus.APPROVED, ProgramStatus.CANCELLED, ProgramStatus.BLOCKED},
            ProgramStatus.REVIEWING: {ProgramStatus.APPROVED, ProgramStatus.BLOCKED, ProgramStatus.CANCELLED},
            ProgramStatus.APPROVED: {ProgramStatus.EXPERIMENTING, ProgramStatus.CANCELLED, ProgramStatus.BLOCKED},
            ProgramStatus.EXPERIMENTING: {ProgramStatus.VALIDATING, ProgramStatus.FAILED, ProgramStatus.INCONCLUSIVE, ProgramStatus.BLOCKED, ProgramStatus.CANCELLED},
            ProgramStatus.VALIDATING: {ProgramStatus.SUCCESSFUL, ProgramStatus.FAILED, ProgramStatus.INCONCLUSIVE, ProgramStatus.BLOCKED},
            ProgramStatus.SUCCESSFUL: {ProgramStatus.SUPERSEDED},
            ProgramStatus.FAILED: {ProgramStatus.SUPERSEDED, ProgramStatus.DRAFT},
            ProgramStatus.INCONCLUSIVE: {ProgramStatus.SUPERSEDED, ProgramStatus.DRAFT},
            ProgramStatus.BLOCKED: {ProgramStatus.CANCELLED, ProgramStatus.DRAFT, ProgramStatus.REVIEWING, ProgramStatus.EXPERIMENTING},
            ProgramStatus.SUPERSEDED: set(),
            ProgramStatus.CANCELLED: set(),
        }
        allowed = valid_transitions.get(self.status, set())
        if new_status not in allowed:
            raise ValueError(f"Illegal program transition: {self.status.value} -> {new_status.value} (reason: {reason})")
        self.status = new_status
        self.updated_at = datetime.now(UTC)


@dataclass
class AdaptationHypothesis:
    """Explicit, measurable, falsifiable hypothesis: IF ... THEN ... BECAUSE ..."""
    id: str = field(default_factory=lambda: f"hyp_{uuid.uuid4().hex[:12]}")
    condition_change: str = ""       # IF condition/change
    expected_outcome: str = ""       # THEN expected outcome
    evidence_reasoning: str = ""     # BECAUSE evidence/reasoning
    confidence: float = 0.5          # 0.0 to 1.0
    evidence_references: list[str] = field(default_factory=list)
    counter_hypotheses: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    falsification_criteria: list[str] = field(default_factory=list)
    measurable_outcomes: dict[str, float] = field(default_factory=dict) # e.g. {"latency_ms": -50.0, "accuracy": 0.05}
    originating_finding_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def validate_measurability(self) -> tuple[bool, str]:
        """Strictly reject vague, non-falsifiable hypotheses."""
        if not self.condition_change.strip() or len(self.condition_change) < 8:
            return False, "Hypothesis must define an explicit IF condition."
        if not self.expected_outcome.strip() or len(self.expected_outcome) < 8:
            return False, "Hypothesis must define an explicit THEN expected outcome."
        if not self.evidence_reasoning.strip() or len(self.evidence_reasoning) < 8:
            return False, "Hypothesis must define an explicit BECAUSE rationale."
        # Reject vague phrases first
        vague_phrases = ["make smarter", "make kairo smarter", "improve things", "be better", "do best", "general improvement"]
        full_text = f"{self.condition_change} {self.expected_outcome}".lower()
        if any(v in full_text for v in vague_phrases):
            return False, "Vague non-measurable hypothesis rejected. Quantified metrics required."
        if not self.measurable_outcomes and not self.falsification_criteria:
            return False, "Hypothesis must define measurable outcome thresholds or falsification criteria."
        return True, "Hypothesis is measurable and falsifiable."


@dataclass
class ExperimentVariant:
    """Candidate behavior or configuration tied to an immutable governed artifact."""
    id: str = field(default_factory=lambda: f"var_{uuid.uuid4().hex[:12]}")
    plan_id: str = ""
    name: str = ""
    variant_type: VariantType = VariantType.CANDIDATE
    config_type: VariantConfigType = VariantConfigType.CONFIGURATION
    target_artifact_id: str = ""     # Capability version ID or registered config ID (immutable)
    configuration_delta: dict[str, Any] = field(default_factory=dict)
    fingerprint: str = ""
    is_control: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def compute_fingerprint(self) -> str:
        """Generate SHA-256 fingerprint of the variant configuration."""
        payload = json.dumps({
            "variant_type": self.variant_type.value,
            "config_type": self.config_type.value,
            "target_artifact_id": self.target_artifact_id,
            "configuration_delta": self.configuration_delta,
        }, sort_keys=True)
        self.fingerprint = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]
        return self.fingerprint


@dataclass
class ExperimentPlan:
    """Structured, bounded experiment plan."""
    id: str = field(default_factory=lambda: f"plan_{uuid.uuid4().hex[:12]}")
    program_id: str = ""
    objective: str = ""
    hypothesis_id: str = ""
    variants: list[ExperimentVariant] = field(default_factory=list)
    dataset_id: str = "default_eval_dataset"
    evaluation_suite_id: str = "comprehensive_suite"
    target_metrics: list[str] = field(default_factory=lambda: ["quality", "safety", "latency", "reliability"])
    safety_gates: list[str] = field(default_factory=lambda: ["SAFETY_GATE", "SECURITY_GATE", "EMERGENCY_STOP_GATE"])
    stop_conditions: list[str] = field(default_factory=lambda: [
        "SAFETY_VIOLATION",
        "SECURITY_VIOLATION",
        "EMERGENCY_STOP",
        "ERROR_RATE_THRESHOLD",
    ])
    resource_budget: dict[str, Any] = field(default_factory=lambda: {
        "max_cost_usd": 5.0,
        "max_tokens": 50000,
        "concurrency": 2,
    })
    time_limit_seconds: float = 1800.0
    min_sample_size: int = 20
    max_sample_size: int = 200
    rollback_condition: str = "Error rate > 5% or regression detected in safety/security"
    evidence_requirements: list[str] = field(default_factory=lambda: [
        "traces", "metrics", "world_state_deltas", "causal_attribution"
    ])
    sandbox_environment: SandboxEnvironment = SandboxEnvironment.SIMULATION
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ExperimentAssignment:
    """Deterministic, reproducible assignment of scenarios/populations to variants."""
    id: str = field(default_factory=lambda: f"asgn_{uuid.uuid4().hex[:12]}")
    plan_id: str = ""
    assignment_seed: int = 42
    strategy: AssignmentStrategy = AssignmentStrategy.DETERMINISTIC_MODULO
    population: str = "benchmark_cases"
    scenario_id: str = ""
    variant_id: str = ""
    assigned_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ExperimentRun:
    """Execution lifecycle of a single experiment plan."""
    id: str = field(default_factory=lambda: f"exprun_{uuid.uuid4().hex[:12]}")
    plan_id: str = ""
    program_id: str = ""
    stage_number: int = 1            # Stage 1: Replay, 2: Sim, 3: Shadow, 4: Canary, 5: Prod
    environment: SandboxEnvironment = SandboxEnvironment.SIMULATION
    status: RunStatus = RunStatus.CREATED
    current_sample_count: int = 0
    target_sample_count: int = 20
    stop_reason: Optional[str] = None
    passed_safety_gates: bool = True
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def transition_to(self, new_status: RunStatus, reason: str = "") -> None:
        """Validate and apply state transition."""
        valid_transitions: dict[RunStatus, set[RunStatus]] = {
            RunStatus.CREATED: {RunStatus.VALIDATING, RunStatus.BLOCKED},
            RunStatus.VALIDATING: {RunStatus.READY, RunStatus.BLOCKED},
            RunStatus.BLOCKED: {RunStatus.CREATED, RunStatus.STOPPED},
            RunStatus.READY: {RunStatus.STARTING, RunStatus.BLOCKED},
            RunStatus.STARTING: {RunStatus.RUNNING, RunStatus.BLOCKED, RunStatus.FAILED},
            RunStatus.RUNNING: {RunStatus.PAUSED, RunStatus.STOPPING, RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.INCONCLUSIVE},
            RunStatus.PAUSED: {RunStatus.RUNNING, RunStatus.STOPPING, RunStatus.BLOCKED},
            RunStatus.STOPPING: {RunStatus.STOPPED, RunStatus.ROLLED_BACK},
            RunStatus.STOPPED: set(),
            RunStatus.COMPLETED: set(),
            RunStatus.PARTIAL: {RunStatus.COMPLETED, RunStatus.STOPPED},
            RunStatus.FAILED: {RunStatus.ROLLED_BACK},
            RunStatus.INCONCLUSIVE: set(),
            RunStatus.ROLLED_BACK: set(),
            RunStatus.UNKNOWN: set(),
        }
        allowed = valid_transitions.get(self.status, set())
        if new_status not in allowed:
            raise ValueError(f"Illegal experiment run transition: {self.status.value} -> {new_status.value} (reason: {reason})")
        self.status = new_status
        if reason:
            self.stop_reason = reason
        if new_status == RunStatus.RUNNING and not self.started_at:
            self.started_at = datetime.now(UTC)
        elif new_status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.INCONCLUSIVE, RunStatus.STOPPED, RunStatus.ROLLED_BACK}:
            self.completed_at = datetime.now(UTC)


@dataclass
class ExperimentObservation:
    """Individual execution observation recorded during an experiment run."""
    id: str = field(default_factory=lambda: f"obs_{uuid.uuid4().hex[:12]}")
    run_id: str = ""
    variant_id: str = ""
    scenario_id: str = ""
    step_index: int = 0
    input_summary: str = ""
    execution_output: str = ""
    latency_ms: float = 0.0
    tokens_used: int = 0
    cost_usd: float = 0.0
    has_error: bool = False
    error_message: Optional[str] = None
    world_state_drift_detected: bool = False
    decision_record_id: Optional[str] = None
    action_transaction_id: Optional[str] = None
    observed_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ExperimentMetric:
    """Measured metric value aggregated per variant during an experiment."""
    id: str = field(default_factory=lambda: f"met_{uuid.uuid4().hex[:12]}")
    run_id: str = ""
    variant_id: str = ""
    dimension: MetricDimension = MetricDimension.QUALITY
    metric_name: str = ""
    metric_value: float = 0.0
    sample_count: int = 0
    variance: float = 0.0
    standard_deviation: float = 0.0
    confidence_interval_low: float = 0.0
    confidence_interval_high: float = 0.0
    recorded_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ExperimentComparison:
    """Structured tri-condition comparison: NO_CHANGE vs BASELINE vs CANDIDATE."""
    id: str = field(default_factory=lambda: f"cmp_{uuid.uuid4().hex[:12]}")
    run_id: str = ""
    baseline_variant_id: str = ""
    candidate_variant_id: str = ""
    no_action_variant_id: Optional[str] = None
    verdict: ComparisonVerdict = ComparisonVerdict.INCONCLUSIVE
    dimension_scores: dict[str, dict[str, float]] = field(default_factory=dict)
    # e.g. {"quality": {"baseline": 0.82, "candidate": 0.91, "delta": 0.09, "p_value": 0.01}}
    absolute_differences: dict[str, float] = field(default_factory=dict)
    relative_differences: dict[str, float] = field(default_factory=dict)
    causal_attribution_verified: bool = False
    causal_explanation: str = ""
    world_state_verified: bool = True
    world_state_drift_summary: str = ""
    sample_size: int = 0
    is_statistically_significant: bool = False
    rationale: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ExperimentDecision:
    """Formal decision resulting from an experiment comparison."""
    id: str = field(default_factory=lambda: f"dec_{uuid.uuid4().hex[:12]}")
    run_id: str = ""
    comparison_id: str = ""
    action_recommended: str = "PROPOSE_EVOLUTION" # PROPOSE_EVOLUTION, STOP, REFINE, ROLLBACK, INCONCLUSIVE
    rationale: str = ""
    evidence_package_id: str = ""
    decided_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ExperimentGate:
    """Fail-closed safety or security gate check within an experiment."""
    id: str = field(default_factory=lambda: f"gate_{uuid.uuid4().hex[:12]}")
    run_id: str = ""
    gate_name: str = ""
    passed: bool = False
    is_critical_security: bool = False
    threshold: Optional[float] = None
    measured_value: Optional[float] = None
    reason: str = ""
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ExperimentArtifact:
    """Stored immutable artifact associated with an experiment run."""
    id: str = field(default_factory=lambda: f"art_{uuid.uuid4().hex[:12]}")
    run_id: str = ""
    artifact_type: str = "trace"     # trace, snapshot, replay_log, metric_dump
    storage_path: str = ""
    content_hash: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ExperimentEvidence:
    """Immutable evidence bundle binding hypothesis, conditions, runs, observations, and metrics."""
    id: str = field(default_factory=lambda: f"evi_{uuid.uuid4().hex[:12]}")
    run_id: str = ""
    program_id: str = ""
    hypothesis_text: str = ""
    baseline_summary: dict[str, Any] = field(default_factory=dict)
    candidate_summary: dict[str, Any] = field(default_factory=dict)
    comparison_summary: dict[str, Any] = field(default_factory=dict)
    observations_count: int = 0
    safety_gates_passed: bool = True
    world_state_reconciled: bool = True
    resource_consumed: dict[str, Any] = field(default_factory=dict)
    immutable_hash: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def seal_evidence(self) -> str:
        """Compute cryptographic hash ensuring evidence cannot be mutated."""
        payload = json.dumps({
            "run_id": self.run_id,
            "program_id": self.program_id,
            "hypothesis_text": self.hypothesis_text,
            "baseline": self.baseline_summary,
            "candidate": self.candidate_summary,
            "comparison": self.comparison_summary,
            "safety_gates_passed": self.safety_gates_passed,
        }, sort_keys=True)
        self.immutable_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return self.immutable_hash


@dataclass
class EvolutionProposal:
    """Formal proposal to promote a candidate change to capability lifecycle. Proposal != Deployment."""
    id: str = field(default_factory=lambda: f"prop_{uuid.uuid4().hex[:12]}")
    program_id: str = ""
    evidence_id: str = ""
    title: str = ""
    affected_capability: str = ""
    current_version: str = "1.0.0"
    target_version: str = "1.1.0"
    baseline_id: str = ""
    candidate_variant_id: str = ""
    evidence_summary: str = ""
    metrics_summary: dict[str, Any] = field(default_factory=dict)
    regression_results: dict[str, Any] = field(default_factory=dict)
    safety_results: dict[str, Any] = field(default_factory=dict)
    security_results: dict[str, Any] = field(default_factory=dict)
    reliability_results: dict[str, Any] = field(default_factory=dict)
    resource_impact: dict[str, Any] = field(default_factory=dict)
    known_limitations: list[str] = field(default_factory=list)
    rollback_plan: str = ""
    deployment_scope: str = "CANARY_10_PERCENT"
    required_governance: list[str] = field(default_factory=lambda: ["GovernanceEngine", "SecurityCenter"])
    required_approval: bool = True
    confidence: float = 0.85
    generation: int = 1              # Evolution generation (0=baseline, 1=candidate, etc.)
    parent_proposal_id: Optional[str] = None
    status: EvolutionProposalStatus = EvolutionProposalStatus.DRAFT
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class EvolutionReview:
    """Human or governance committee review record for an EvolutionProposal."""
    id: str = field(default_factory=lambda: f"rev_{uuid.uuid4().hex[:12]}")
    proposal_id: str = ""
    reviewer: str = ""
    status: ReviewStatus = ReviewStatus.PENDING
    rationale: str = ""
    approval_reference_id: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class EvolutionChangeSet:
    """Immutable, governed changeset. Arbitrary code injection is strictly forbidden."""
    id: str = field(default_factory=lambda: f"cs_{uuid.uuid4().hex[:12]}")
    proposal_id: str = ""
    capability_id: str = ""
    current_version: str = "1.0.0"
    candidate_version: str = "1.1.0"
    configuration_delta: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    compatibility_report: dict[str, Any] = field(default_factory=dict)
    migration_requirements: list[str] = field(default_factory=list)
    rollback_instructions: dict[str, Any] = field(default_factory=dict)
    content_hash: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def compute_content_hash(self) -> str:
        """Hash the immutable changeset to ensure integrity."""
        payload = json.dumps({
            "proposal_id": self.proposal_id,
            "capability_id": self.capability_id,
            "current_version": self.current_version,
            "candidate_version": self.candidate_version,
            "delta": self.configuration_delta,
            "dependencies": self.dependencies,
        }, sort_keys=True)
        self.content_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return self.content_hash


@dataclass
class EvolutionValidation:
    """Multi-suite validation record executed prior to capability promotion."""
    id: str = field(default_factory=lambda: f"val_{uuid.uuid4().hex[:12]}")
    changeset_id: str = ""
    proposal_id: str = ""
    suite_results: dict[str, str] = field(default_factory=dict) # e.g. {"regression_corpus": "PASS", "safety_suite": "PASS"}
    holdout_passed: bool = True
    overall_status: ValidationStatus = ValidationStatus.PENDING
    failure_details: list[str] = field(default_factory=list)
    validated_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class AdaptationEvent:
    """Audit log entry for full chronological and causal provenance."""
    id: str = field(default_factory=lambda: f"aev_{uuid.uuid4().hex[:12]}")
    event_type: str = ""             # e.g. adaptation.created, experiment.started, evolution.proposed
    program_id: Optional[str] = None
    experiment_id: Optional[str] = None
    proposal_id: Optional[str] = None
    correlation_id: str = ""
    actor: str = "kairo.adaptation"
    payload: dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
