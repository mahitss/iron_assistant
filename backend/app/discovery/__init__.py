"""Kairo Autonomous Hypothesis, Experimentation & Scientific Discovery Engine (Task 72).

Enables autonomous scientific discovery loops:
UNKNOWN -> QUESTION -> HYPOTHESES -> EXPERIMENT DESIGN -> PREDICTION ->
AUTHORIZATION -> EXECUTION -> OBSERVATION -> RESULT ANALYSIS ->
HYPOTHESIS UPDATE -> VERIFICATION -> KNOWLEDGE UPDATE -> NEXT EXPERIMENT
"""

from app.discovery.analyzer import ResultAnalyzer
from app.discovery.design import ExperimentDesigner
from app.discovery.hypotheses import HypothesisEngine
from app.discovery.integrator import DiscoverySubsystemIntegrator
from app.discovery.prediction import PredictionRecorder
from app.discovery.queue import ExperimentQueueManager
from app.discovery.replication import BiasDetector, ReplicationEngine
from app.discovery.router import discovery_router, experiments_router
from app.discovery.schemas import (
    AnalysisOutcome,
    CleanupPlan,
    DiscoveryAuditEvent,
    DiscoveryHealthMetrics,
    DiscoveryHypothesis,
    DiscoveryRequest,
    DiscoverySession,
    DiscoveryState,
    EnvironmentType,
    EpistemicCategory,
    ExperimentDesign,
    ExperimentObservation,
    ExperimentResult,
    ExperimentStatus,
    ExperimentType,
    GeneralizationScope,
    PreExecutionPrediction,
    ResearchQuestion,
    RiskLevel,
    RollbackPlan,
)
from app.discovery.service import (
    DiscoveryEngineService,
    get_discovery_service,
)
from app.discovery.state_machine import (
    can_transition_discovery,
    can_transition_experiment,
    validate_discovery_transition,
    validate_experiment_transition,
)
from app.discovery.unknowns import UnknownDetector

__all__ = [
    "AnalysisOutcome",
    "BiasDetector",
    "CleanupPlan",
    "DiscoveryAuditEvent",
    "DiscoveryEngineService",
    "DiscoveryHealthMetrics",
    "DiscoveryHypothesis",
    "DiscoveryRequest",
    "DiscoverySession",
    "DiscoveryState",
    "DiscoverySubsystemIntegrator",
    "EnvironmentType",
    "EpistemicCategory",
    "ExperimentDesign",
    "ExperimentDesigner",
    "ExperimentObservation",
    "ExperimentQueueManager",
    "ExperimentResult",
    "ExperimentStatus",
    "ExperimentType",
    "GeneralizationScope",
    "HypothesisEngine",
    "PreExecutionPrediction",
    "PredictionRecorder",
    "ReplicationEngine",
    "ResearchQuestion",
    "ResultAnalyzer",
    "RiskLevel",
    "RollbackPlan",
    "UnknownDetector",
    "can_transition_discovery",
    "can_transition_experiment",
    "discovery_router",
    "experiments_router",
    "get_discovery_service",
    "validate_discovery_transition",
    "validate_experiment_transition",
]
