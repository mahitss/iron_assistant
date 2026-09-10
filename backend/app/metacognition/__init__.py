"""Kairo Self-Modeling, Metacognition & Self-Correction Engine (Task 51)."""

from app.metacognition.actions import ActionEngine, ActionGuardError
from app.metacognition.assumptions import AssumptionTracker
from app.metacognition.authority import AuthorityValidator, UnauthorizedAuthorityClaimError
from app.metacognition.calibration import ConfidenceCalibrator
from app.metacognition.capabilities import CapabilityHallucinationError, CapabilityManager
from app.metacognition.confidence import ConfidenceEngine
from app.metacognition.errors import ErrorMemoryManager
from app.metacognition.evaluation import MetacognitiveEvaluator
from app.metacognition.explanations import ExplanationGenerator
from app.metacognition.failures import FailureClassifier
from app.metacognition.goals import GoalDriftError, GoalTracker
from app.metacognition.introspection import IntrospectionConsole
from app.metacognition.knowledge import KnowledgeStateTracker
from app.metacognition.limitations import LimitationDetector
from app.metacognition.observations import FalseObservationError, ObservationTracker
from app.metacognition.plans import PlanReadinessEvaluator
from app.metacognition.policy_state import PolicyStateManager, PolicyTamperingError
from app.metacognition.provenance import MetacognitiveProvenanceTracker
from app.metacognition.reflection import ReflectionEngine
from app.metacognition.resource_awareness import ResourceAwarenessTracker, ResourceBudgetExceededError
from app.metacognition.router import get_metacognition_service, router as metacognition_router
from app.metacognition.safety import (
    ConsciousnessClaimError,
    MetacognitiveSafetyGuard,
    SelfPreservationViolationError,
)
from app.metacognition.self_model import SelfModelManager
from app.metacognition.service import MetacognitionService
from app.metacognition.state import InternalStateManager
from app.metacognition.tasks import TaskTracker, UnknownTaskOriginError
from app.metacognition.uncertainty import UncertaintyModel
from app.metacognition.verification import FalseVerificationClaimError, VerificationAuditGuard

__all__ = [
    "metacognition_router",
    "get_metacognition_service",
    "MetacognitionService",
    "SelfModelManager",
    "CapabilityManager",
    "CapabilityHallucinationError",
    "LimitationDetector",
    "KnowledgeStateTracker",
    "UncertaintyModel",
    "ConfidenceEngine",
    "ConfidenceCalibrator",
    "AssumptionTracker",
    "GoalTracker",
    "GoalDriftError",
    "TaskTracker",
    "UnknownTaskOriginError",
    "ActionEngine",
    "ActionGuardError",
    "PlanReadinessEvaluator",
    "ObservationTracker",
    "FalseObservationError",
    "FailureClassifier",
    "ErrorMemoryManager",
    "VerificationAuditGuard",
    "FalseVerificationClaimError",
    "ReflectionEngine",
    "MetacognitiveEvaluator",
    "ResourceAwarenessTracker",
    "ResourceBudgetExceededError",
    "AuthorityValidator",
    "UnauthorizedAuthorityClaimError",
    "PolicyStateManager",
    "PolicyTamperingError",
    "MetacognitiveSafetyGuard",
    "ConsciousnessClaimError",
    "SelfPreservationViolationError",
    "IntrospectionConsole",
    "ExplanationGenerator",
    "MetacognitiveProvenanceTracker",
    "InternalStateManager",
]
