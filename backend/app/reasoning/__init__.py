"""Kairo Autonomous Reasoning & Deliberation Engine (Task 71).

Provides structured problem decomposition, competing hypotheses, empirical evidence
evaluation, falsification-oriented tests, assumption invalidation cascades, and safe
deliberation without exposing private chain-of-thought.
"""

from app.reasoning.assumptions import AssumptionTracker
from app.reasoning.budget import BudgetCoordinator
from app.reasoning.decomposer import ProblemDecomposer
from app.reasoning.deliberation import DeliberationEngine
from app.reasoning.evidence import EvidenceEvaluator
from app.reasoning.falsification import FalsificationEngine
from app.reasoning.graph import ReasoningGraphBuilder
from app.reasoning.hypotheses import HypothesisGenerator
from app.reasoning.integrator import ReasoningSubsystemIntegrator
from app.reasoning.router import router as reasoning_router
from app.reasoning.schemas import (
    AssumptionStatus,
    ConclusionStatus,
    EscalationType,
    GraphEdgeType,
    HypothesisStatus,
    ReasoningAlternative,
    ReasoningAssumption,
    ReasoningBudget,
    ReasoningConclusion,
    ReasoningConfidence,
    ReasoningDepth,
    ReasoningEvidence,
    ReasoningExplanation,
    ReasoningGraph,
    ReasoningHealthMetrics,
    ReasoningHypothesis,
    ReasoningRequest,
    ReasoningSession,
    ReasoningState,
    ReasoningTraceEvent,
    SubProblem,
    UncertaintyType,
)
from app.reasoning.service import ReasoningEngineService
from app.reasoning.state_machine import ReasoningStateMachine

__all__ = [
    "AssumptionStatus",
    "AssumptionTracker",
    "BudgetCoordinator",
    "ConclusionStatus",
    "DeliberationEngine",
    "EscalationType",
    "EvidenceEvaluator",
    "FalsificationEngine",
    "GraphEdgeType",
    "HypothesisGenerator",
    "HypothesisStatus",
    "ProblemDecomposer",
    "ReasoningAlternative",
    "ReasoningAssumption",
    "ReasoningBudget",
    "ReasoningConclusion",
    "ReasoningConfidence",
    "ReasoningDepth",
    "ReasoningEngineService",
    "ReasoningEvidence",
    "ReasoningExplanation",
    "ReasoningGraph",
    "ReasoningGraphBuilder",
    "ReasoningHealthMetrics",
    "ReasoningHypothesis",
    "ReasoningRequest",
    "ReasoningSession",
    "ReasoningState",
    "ReasoningStateMachine",
    "ReasoningSubsystemIntegrator",
    "ReasoningTraceEvent",
    "SubProblem",
    "UncertaintyType",
    "reasoning_router",
]
