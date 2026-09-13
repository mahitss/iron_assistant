"""Kairo Governance and Policy Decision Engine (Tasks 36 & 78).

Provides centralized policy evaluation, risk classification, constitutional reasoning,
authority management, multi-tier policy hierarchy, least-privilege analysis,
and emergency protections across Kairo subsystems.
"""

from app.policy.authority import AuthorityManagerEngine, default_authority_manager
from app.policy.constitution import ConstitutionalEngine
from app.policy.engine import PolicyEngine, policy_engine
from app.policy.escalation_detector import (
    AuthorityEscalationDetector,
    default_escalation_detector,
)
from app.policy.goal_alignment import GoalAlignmentEngine, default_goal_alignment_engine
from app.policy.governance_coordinator import (
    GovernanceIntelligenceCoordinator,
    default_governance_coordinator,
)
from app.policy.governance_router import router as governance_router
from app.policy.governance_schemas import (
    AuthorityEscalationReport,
    AuthorityGrant,
    AuthorityLevel,
    ConstitutionalPrinciple,
    ConstitutionModelSchema,
    GoalAlignmentReport,
    GovernanceDashboardSummary,
    GovernanceDecisionResult,
    GovernanceDecisionType,
    GovernanceReviewRequest,
    GovernanceState,
    LeastPrivilegeRecommendation,
    PolicyTier,
    PrincipleEvaluationResult,
    PrincipleName,
    PrincipleStrictness,
)
from app.policy.governance_state_machine import (
    GovernanceStateMachine,
    GovernanceTransitionError,
)
from app.policy.hierarchy import PolicyHierarchyEngine
from app.policy.registry import PolicyRegistry, policy_registry
from app.policy.router import admin_router as admin_policy_router, router as policy_router
from app.policy.schemas import (
    ConditionOperator,
    DataClassification,
    PolicyContext,
    PolicyDecision,
    PolicyDecisionType,
    PolicyRule,
    PolicyRuleCondition,
    PolicyScope,
    RiskLevel,
)

__all__ = [
    # Task 36
    "PolicyEngine",
    "policy_engine",
    "PolicyRegistry",
    "policy_registry",
    "policy_router",
    "admin_policy_router",
    "governance_router",
    "PolicyContext",
    "PolicyDecision",
    "PolicyDecisionType",
    "RiskLevel",
    "DataClassification",
    "PolicyScope",
    "PolicyRule",
    "PolicyRuleCondition",
    "ConditionOperator",
    # Task 78
    "ConstitutionalEngine",
    "AuthorityManagerEngine",
    "default_authority_manager",
    "PolicyHierarchyEngine",
    "GovernanceStateMachine",
    "GovernanceTransitionError",
    "GoalAlignmentEngine",
    "default_goal_alignment_engine",
    "AuthorityEscalationDetector",
    "default_escalation_detector",
    "GovernanceIntelligenceCoordinator",
    "default_governance_coordinator",
    "PrincipleName",
    "PrincipleStrictness",
    "PolicyTier",
    "AuthorityLevel",
    "GovernanceState",
    "GovernanceDecisionType",
    "ConstitutionalPrinciple",
    "ConstitutionModelSchema",
    "AuthorityGrant",
    "PrincipleEvaluationResult",
    "GoalAlignmentReport",
    "LeastPrivilegeRecommendation",
    "AuthorityEscalationReport",
    "GovernanceReviewRequest",
    "GovernanceDecisionResult",
    "GovernanceDashboardSummary",
]
