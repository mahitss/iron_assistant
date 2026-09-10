"""Master Metacognition Service orchestrating the complete self-modeling pipeline (Task 51)."""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any, Dict, List, Optional

from app.metacognition.actions import ActionEngine
from app.metacognition.assumptions import AssumptionTracker
from app.metacognition.authority import AuthorityValidator
from app.metacognition.calibration import ConfidenceCalibrator
from app.metacognition.capabilities import CapabilityManager
from app.metacognition.confidence import ConfidenceEngine
from app.metacognition.errors import ErrorMemoryManager
from app.metacognition.evaluation import MetacognitiveEvaluator
from app.metacognition.explanations import ExplanationGenerator
from app.metacognition.failures import FailureClassifier
from app.metacognition.goals import GoalTracker
from app.metacognition.introspection import IntrospectionConsole
from app.metacognition.knowledge import KnowledgeStateTracker
from app.metacognition.limitations import LimitationDetector
from app.metacognition.observations import ObservationTracker
from app.metacognition.plans import PlanReadinessEvaluator
from app.metacognition.policy_state import PolicyStateManager
from app.metacognition.provenance import MetacognitiveProvenanceTracker
from app.metacognition.reflection import ReflectionEngine
from app.metacognition.resource_awareness import ResourceAwarenessTracker
from app.metacognition.safety import MetacognitiveSafetyGuard
from app.metacognition.self_model import SelfModelManager
from app.metacognition.state import InternalStateManager
from app.metacognition.tasks import TaskTracker
from app.metacognition.uncertainty import UncertaintyModel
from app.metacognition.verification import VerificationAuditGuard

logger = logging.getLogger(__name__)


class MetacognitionService:
    """Master orchestrator implementing:

    OBSERVE -> MODEL INTERNAL STATE -> CHECK KNOWLEDGE -> CHECK CAPABILITY ->
    CHECK AUTHORITY -> CHECK CONFIDENCE -> CHECK LIMITATIONS -> ACT OR ASK ->
    VERIFY -> UPDATE SELF-MODEL
    """

    def __init__(self) -> None:
        self.capabilities = CapabilityManager()
        self.limitations = LimitationDetector()
        self.knowledge = KnowledgeStateTracker()
        self.uncertainty = UncertaintyModel()
        self.confidence = ConfidenceEngine()
        self.calibration = ConfidenceCalibrator()
        self.assumptions = AssumptionTracker()
        self.goals = GoalTracker()
        self.tasks = TaskTracker()
        self.state = InternalStateManager()
        self.resources = ResourceAwarenessTracker()
        self.authority = AuthorityValidator()
        self.policy = PolicyStateManager()
        self.safety = MetacognitiveSafetyGuard()
        self.observations = ObservationTracker()
        self.failures = FailureClassifier()
        self.errors = ErrorMemoryManager()
        self.verification = VerificationAuditGuard()
        self.reflection = ReflectionEngine()
        self.evaluator = MetacognitiveEvaluator()
        self.provenance = MetacognitiveProvenanceTracker()

        self.plan_evaluator = PlanReadinessEvaluator(self.capabilities)
        self.introspection = IntrospectionConsole(
            self.capabilities,
            self.limitations,
            self.uncertainty,
            self.failures,
        )

        self.self_model = SelfModelManager(
            capability_manager=self.capabilities,
            limitation_detector=self.limitations,
            knowledge_tracker=self.knowledge,
            uncertainty_model=self.uncertainty,
            goal_tracker=self.goals,
            task_tracker=self.tasks,
            state_manager=self.state,
            resource_tracker=self.resources,
            policy_manager=self.policy,
            safety_guard=self.safety,
        )

    # =========================================================================
    # CORE INTERFACES
    # =========================================================================

    def get_self_model(self, user_id: str = "default_user"):
        return self.self_model.build_snapshot(user_id=user_id)

    def get_user_facing_projection(self, user_id: str = "default_user") -> Dict[str, Any]:
        snapshot = self.get_self_model(user_id=user_id)
        return ExplanationGenerator.create_user_facing_projection(snapshot)

    def check_action_readiness(
        self,
        action_name: str,
        required_capabilities: List[str],
        user_id: str = "default_user",
        required_permission: Optional[str] = None,
        policy_rule: Optional[str] = None,
        requires_approval: bool = False,
        is_approved: bool = False,
        preconditions: Optional[Dict[str, bool]] = None,
    ):
        avail_caps = [c.name for c in self.capabilities.list_capabilities() if c.state in ("AVAILABLE", "RESTRICTED")]
        is_auth = self.authority.is_authorized(user_id, required_permission) if required_permission else True
        is_policy = self.policy.check_policy(policy_rule) if policy_rule else True

        return ActionEngine.assess_readiness(
            action_name=action_name,
            required_capabilities=required_capabilities,
            available_capabilities=avail_caps,
            is_authorized=is_auth,
            is_policy_permitted=is_policy,
            requires_approval=requires_approval,
            is_approved=is_approved,
            preconditions=preconditions,
        )

    def introspect(self, question_type: str, subject_or_action: Optional[str] = None) -> Any:
        q = question_type.upper()
        if q == "WHAT_CAN_YOU_DO":
            return self.introspection.answer_what_can_you_do()
        elif q == "WHY_CANT_YOU":
            return self.introspection.answer_why_cant_you_do_this(subject_or_action or "operation")
        elif q == "HOW_SURE":
            return self.introspection.answer_how_sure_are_you(subject_or_action or "general")
        elif q == "DID_YOU_DO_IT":
            return self.introspection.answer_did_you_actually_do_it(subject_or_action or "action")
        elif q == "WHAT_WENT_WRONG":
            return self.introspection.answer_what_went_wrong(subject_or_action)
        else:
            raise ValueError(f"Unknown introspection question type: '{question_type}'")

    def reconcile(self, registered_tools: List[str]) -> Dict[str, Any]:
        return self.self_model.reconcile_self_model(registered_tools)
