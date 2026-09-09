"""Kairo Cognitive Planning, Reasoning, Long-Horizon Execution, Plan Verification, and Adaptive Decision Engine (Task 41).

Core Architectural Invariant:
LLM: PROPOSES
Planner: STRUCTURES
Policy: AUTHORIZES
Task Engine: EXECUTES
Verifier: CHECKS
World Model: REPRESENTS CURRENT STATE
Memory: REMEMBERS RELEVANT HISTORY
"""

from app.cognition.alternatives import AlternativeEvaluator, PlanAlternative
from app.cognition.assumptions import (
    AssumptionCriticality,
    AssumptionValidationStatus,
    AssumptionValidator,
    PlanAssumption,
)
from app.cognition.confidence import ConfidenceLevel, EvidenceAssessment
from app.cognition.constraints import (
    Constraint,
    ConstraintEngine,
    ConstraintEvaluationResult,
    ConstraintType,
)
from app.cognition.decomposer import PlanDecomposer
from app.cognition.dependencies import (
    DependencyCycleError,
    DependencyGraph,
    ResourceConflictError,
)
from app.cognition.evaluator import PlanEvaluator, PlanValidationReport
from app.cognition.explain import PlanExplainer, PlanPreview, StepExplanation
from app.cognition.goals import Goal, GoalPriority, GoalScope, GoalStatus, GoalType
from app.cognition.planner import CognitivePlanner
from app.cognition.plans import Plan, PlanDiff, PlanRiskLevel, PlanStatus, ScopeLock
from app.cognition.reasoning import (
    DecisionFactors,
    Hypothesis,
    ReasoningEngine,
    ReasoningMode,
)
from app.cognition.replanner import PlanReplanner, ReplanReason, ReplanRequest
from app.cognition.router import router as cognition_router
from app.cognition.scheduler import PlanScheduler, QueueItem, QueueItemStatus
from app.cognition.state import CognitiveStateBridge, PlanFreshnessState
from app.cognition.steps import PlanStep, StepRiskLevel, StepStatus, VerificationSpec
from app.cognition.strategies import PlanTemplate, StrategyRegistry
from app.cognition.verifier import (
    CognitiveVerifier,
    InvariantViolationError,
    StepVerificationResult,
)

__all__ = [
    "AlternativeEvaluator",
    "AssumptionCriticality",
    "AssumptionValidationStatus",
    "AssumptionValidator",
    "CognitivePlanner",
    "CognitiveStateBridge",
    "CognitiveVerifier",
    "ConfidenceLevel",
    "Constraint",
    "ConstraintEngine",
    "ConstraintEvaluationResult",
    "ConstraintType",
    "DecisionFactors",
    "DependencyCycleError",
    "DependencyGraph",
    "EvidenceAssessment",
    "Goal",
    "GoalPriority",
    "GoalScope",
    "GoalStatus",
    "GoalType",
    "Hypothesis",
    "InvariantViolationError",
    "Plan",
    "PlanAlternative",
    "PlanAssumption",
    "PlanDecomposer",
    "PlanDiff",
    "PlanEvaluator",
    "PlanExplainer",
    "PlanFreshnessState",
    "PlanPreview",
    "PlanReplanner",
    "PlanRiskLevel",
    "PlanScheduler",
    "PlanStatus",
    "PlanStep",
    "PlanTemplate",
    "PlanValidationReport",
    "QueueItem",
    "QueueItemStatus",
    "ReasoningEngine",
    "ReasoningMode",
    "ReplanReason",
    "ReplanRequest",
    "ResourceConflictError",
    "ScopeLock",
    "StepExplanation",
    "StepRiskLevel",
    "StepStatus",
    "StepVerificationResult",
    "StrategyRegistry",
    "VerificationSpec",
    "cognition_router",
]
