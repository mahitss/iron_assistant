"""Kairo Executive Decision Engine package (Task 57).

Answers: 'What should Kairo recommend we do?' by synthesizing verified state,
goals, multi-objective trade-offs, constraints, evidence, simulations, and uncertainty.
"""

from app.decision.engine import DecisionEngine, decision_engine
from app.decision.router import router as decision_router
from app.decision.safety import DecisionExecutionBoundaryError
from app.decision.schemas import (
    CandidateOption,
    Constraint,
    ConstraintType,
    DataTrustLevel,
    DecisionCommitment,
    DecisionGate,
    DecisionOutcome,
    DecisionRanking,
    DecisionRecord,
    DecisionRequest,
    DecisionRevision,
    DecisionStatus,
    EvidenceItem,
    EvidenceSet,
    EvidenceStrength,
    GateEvaluationStatus,
    Objective,
    OptionEvaluation,
    OptionType,
    Preference,
    Recommendation,
    ReversibilityLevel,
    RiskAssessment,
    RiskCategory,
    Tradeoff,
    UncertaintyAssessment,
)
from app.decision.service import DecisionService, decision_service

__all__ = [
    "CandidateOption",
    "Constraint",
    "ConstraintType",
    "DataTrustLevel",
    "DecisionCommitment",
    "DecisionEngine",
    "DecisionExecutionBoundaryError",
    "DecisionGate",
    "DecisionOutcome",
    "DecisionRanking",
    "DecisionRecord",
    "DecisionRequest",
    "DecisionRevision",
    "DecisionService",
    "DecisionStatus",
    "EvidenceItem",
    "EvidenceSet",
    "EvidenceStrength",
    "GateEvaluationStatus",
    "Objective",
    "OptionEvaluation",
    "OptionType",
    "Preference",
    "Recommendation",
    "ReversibilityLevel",
    "RiskAssessment",
    "RiskCategory",
    "Tradeoff",
    "UncertaintyAssessment",
    "decision_engine",
    "decision_router",
    "decision_service",
]
