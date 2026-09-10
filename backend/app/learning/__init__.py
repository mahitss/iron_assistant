"""Kairo Adaptive Learning, Strategy Optimization & Experience Engine (Task 43)."""

from app.learning.calibration import CalibratedConfidence, ConfidenceCalibrator
from app.learning.decay import EnvironmentalDecayManager
from app.learning.evaluator import StrategyEvaluationReport, StrategyEvaluator
from app.learning.experiences import Experience, ExperienceType
from app.learning.experimentation import Experiment, ExperimentStatus
from app.learning.failures import FailureManager, PreFlightWarning
from app.learning.feedback import FeedbackIngestor, FeedbackItem
from app.learning.optimizer import RankedStrategy, StrategyOptimizer
from app.learning.outcomes import Outcome
from app.learning.patterns import FailurePattern, PatternClusterer
from app.learning.personalization import PersonalizationManager, UserPreferenceProfile
from app.learning.promotion import PromotionRecord, StrategyPromoter
from app.learning.provenance import StrategyProvenanceRecord
from app.learning.reliability import ReliabilityMetrics, ReliabilityTracker
from app.learning.rollback import RollbackRecord, StrategyRollbacker
from app.learning.router import router as learning_router
from app.learning.safety import LearningSafetyGuard
from app.learning.service import LearningService
from app.learning.signals import (
    SOURCE_PRIORITY_WEIGHTS,
    LearningSignal,
    SignalSource,
    SignalType,
)
from app.learning.strategies import Strategy, StrategyStatus
from app.learning.strategy_store import StrategyStore

from app.learning.adaptation import BehaviorAdaptationEngine, ModelWeightModificationError
from app.learning.consolidation import ContradictoryConsolidationError, ExperienceConsolidator
from app.learning.corrections import CorrectionHandler
from app.learning.evaluation import ContinuousLearningEvaluator
from app.learning.experiences import ExperienceManager
from app.learning.generalization import GeneralizationGuard, OvergeneralizationError
from app.learning.governance import LearningGovernanceEngine
from app.learning.heuristics import HeuristicManager, HeuristicPolicyInferenceError
from app.learning.lessons import LessonExtractor
from app.learning.outcomes import LearningOutcome, OutcomeEvaluator
from app.learning.ranking import AdaptiveRankingEngine
from app.learning.replay import ExperienceReplayEngine, TemporalLeakageError
from app.learning.retention import LearningRetentionManager
from app.learning.retrieval import AdaptiveRetrievalEngine
from app.learning.safety import (
    DataPoisoningError,
    PolicyModificationAttemptError,
    SafetyBoundaryViolationError,
)
from app.learning.schemas import (
    AdaptationType,
    ContinuousLearningMetricsSchema,
    CorrectionRecordSchema,
    ExperienceSchema,
    ExperienceSource,
    ExperienceStatus,
    FeedbackRecordSchema,
    FeedbackType,
    GeneralizationScope,
    HeuristicSchema,
    LearningOutcomeSchema,
    LearningPolicySchema,
    LessonSchema,
    LessonStatus,
    LessonType,
    ReplayEvaluationSchema,
    WorkflowPatternSchema,
)
from app.learning.skills import SkillImprovementEngine
from app.learning.workflows import WorkflowManager, WorkflowPolicyViolationError

__all__ = [
    "Experience",
    "ExperienceType",
    "Outcome",
    "LearningSignal",
    "SignalType",
    "SignalSource",
    "SOURCE_PRIORITY_WEIGHTS",
    "Strategy",
    "StrategyStatus",
    "StrategyStore",
    "StrategyOptimizer",
    "RankedStrategy",
    "StrategyEvaluator",
    "StrategyEvaluationReport",
    "ReliabilityMetrics",
    "ReliabilityTracker",
    "FailurePattern",
    "PatternClusterer",
    "FailureManager",
    "PreFlightWarning",
    "FeedbackItem",
    "FeedbackIngestor",
    "Experiment",
    "ExperimentStatus",
    "StrategyPromoter",
    "PromotionRecord",
    "StrategyRollbacker",
    "RollbackRecord",
    "EnvironmentalDecayManager",
    "ConfidenceCalibrator",
    "CalibratedConfidence",
    "UserPreferenceProfile",
    "PersonalizationManager",
    "LearningSafetyGuard",
    "StrategyProvenanceRecord",
    "LearningService",
    "learning_router",
    "ExperienceManager",
    "LearningOutcome",
    "OutcomeEvaluator",
    "LessonExtractor",
    "GeneralizationGuard",
    "OvergeneralizationError",
    "ExperienceConsolidator",
    "ContradictoryConsolidationError",
    "ExperienceReplayEngine",
    "TemporalLeakageError",
    "ContinuousLearningEvaluator",
    "BehaviorAdaptationEngine",
    "ModelWeightModificationError",
    "SkillImprovementEngine",
    "WorkflowManager",
    "WorkflowPolicyViolationError",
    "HeuristicManager",
    "HeuristicPolicyInferenceError",
    "AdaptiveRetrievalEngine",
    "AdaptiveRankingEngine",
    "FeedbackProcessor",
    "CorrectionHandler",
    "LearningRetentionManager",
    "LearningGovernanceEngine",
    "SafetyBoundaryViolationError",
    "PolicyModificationAttemptError",
    "DataPoisoningError",
    "ExperienceStatus",
    "ExperienceSource",
    "LessonType",
    "LessonStatus",
    "GeneralizationScope",
    "FeedbackType",
    "AdaptationType",
    "ExperienceSchema",
    "LearningOutcomeSchema",
    "LessonSchema",
    "WorkflowPatternSchema",
    "HeuristicSchema",
    "ReplayEvaluationSchema",
    "LearningPolicySchema",
    "ContinuousLearningMetricsSchema",
    "FeedbackRecordSchema",
    "CorrectionRecordSchema",
]
