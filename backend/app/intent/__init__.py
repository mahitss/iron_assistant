"""Kairo Unified Command, Intent, Reference Resolution, Goal Extraction, and Safe Motivation Engine (Tasks 35 & 48)."""

from app.intent.ambiguity import Ambiguity, AmbiguityAnalyzer
from app.intent.assumptions import Assumption, AssumptionTracker
from app.intent.clarification import ClarificationManager, ClarificationRequest
from app.intent.classifier import CommandClassifier
from app.intent.commands import CommandService
from app.intent.confidence import ConfidenceEstimator
from app.intent.constraints import (
    ConstraintCategory,
    ConstraintEngine,
    ConstraintPriority,
    DiscoveredConstraint,
)
from app.intent.context import (
    ContextSnapshot,
    IntentContextManager,
    TemporalContextResolver,
)
from app.intent.dialogue import DialogueSession, DialogueStateManager
from app.intent.entities import EntityExtractor
from app.intent.evaluation import IntentErrorCategory, IntentEvaluator
from app.intent.goals import Goal, GoalManager
from app.intent.intent_graph import IntentGraph
from app.intent.models import (
    AmbiguityRecordModel,
    AssumptionModel,
    ClarificationModel,
    CommandModel,
    GoalModel,
    IntentGraphModel,
    IntentModel,
    MotivationModel,
    ObjectiveModel,
)
from app.intent.motivation import (
    MotivationCategory,
    MotivationEngine,
    MotivationSignal,
    TradeoffAnalysis,
)
from app.intent.normalizer import CommandNormalizer
from app.intent.objectives import Objective, ObjectiveExtractor, ObjectiveType
from app.intent.parser import IntentParser
from app.intent.planner_bridge import CommandRouter
from app.intent.policies import IntentPolicyEngine
from app.intent.preferences import (
    PreferenceConfidence,
    PreferenceResolver,
    PreferenceScope,
    UserPreference,
)
from app.intent.priorities import IntentPrioritizer, IntentPriorityNode
from app.intent.provenance import IntentProvenanceTracker, ProvenanceSource
from app.intent.references import ReferenceResolver
from app.intent.resolution import SafeResolver
from app.intent.router import commands_router, intent_router
from app.intent.safety import IntentSafetyGuard, IntentSecurityViolation
from app.intent.schemas import (
    AmbiguityLevel,
    AmbiguityReport,
    AssumptionType,
    ClarificationOption,
    CommandAttachment,
    CommandCreateRequest,
    CommandResolveRequest,
    CommandResponse,
    CommandSchema,
    GoalStatus,
    IntentConstraints,
    IntentDetailedResponse,
    IntentEntity,
    IntentErrorState,
    IntentRiskLevel,
    IntentSchema,
    IntentStatus,
    IntentTarget,
    IntentType,
    ResolutionMethod,
    UrgencyLevel,
)
from app.intent.scope import IntentScope, ScopeExtractor
from app.intent.service import IntentService, get_intent_service
from app.intent.urgency import UrgencyExtractor
from app.intent.validator import IntentValidator

__all__ = [
    "Ambiguity",
    "AmbiguityAnalyzer",
    "AmbiguityLevel",
    "AmbiguityRecordModel",
    "AmbiguityReport",
    "Assumption",
    "AssumptionModel",
    "AssumptionTracker",
    "AssumptionType",
    "ClarificationManager",
    "ClarificationModel",
    "ClarificationOption",
    "ClarificationRequest",
    "CommandAttachment",
    "CommandClassifier",
    "CommandCreateRequest",
    "CommandModel",
    "CommandNormalizer",
    "CommandResolveRequest",
    "CommandResponse",
    "CommandRouter",
    "CommandSchema",
    "CommandService",
    "ConfidenceEstimator",
    "ConstraintCategory",
    "ConstraintEngine",
    "ConstraintPriority",
    "ContextSnapshot",
    "DialogueSession",
    "DialogueStateManager",
    "DiscoveredConstraint",
    "EntityExtractor",
    "Goal",
    "GoalManager",
    "GoalModel",
    "GoalStatus",
    "IntentConstraints",
    "IntentContextManager",
    "IntentDetailedResponse",
    "IntentEntity",
    "IntentErrorCategory",
    "IntentErrorState",
    "IntentEvaluator",
    "IntentGraph",
    "IntentGraphModel",
    "IntentModel",
    "IntentParser",
    "IntentPolicyEngine",
    "IntentPrioritizer",
    "IntentPriorityNode",
    "IntentProvenanceTracker",
    "IntentRiskLevel",
    "IntentSafetyGuard",
    "IntentSchema",
    "IntentScope",
    "IntentSecurityViolation",
    "IntentService",
    "IntentStatus",
    "IntentTarget",
    "IntentType",
    "IntentValidator",
    "MotivationCategory",
    "MotivationEngine",
    "MotivationModel",
    "MotivationSignal",
    "Objective",
    "ObjectiveExtractor",
    "ObjectiveModel",
    "ObjectiveType",
    "PreferenceConfidence",
    "PreferenceResolver",
    "PreferenceScope",
    "ProvenanceSource",
    "ReferenceResolver",
    "ResolutionMethod",
    "SafeResolver",
    "ScopeExtractor",
    "TemporalContextResolver",
    "TradeoffAnalysis",
    "UrgencyExtractor",
    "UrgencyLevel",
    "UserPreference",
    "commands_router",
    "get_intent_service",
    "intent_router",
]
