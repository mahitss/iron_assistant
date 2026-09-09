"""Autonomy Governance Policies, Fail-Closed Enforcement, and Domain Workflow Rules (Task 45)."""

from __future__ import annotations

from enum import Enum
import logging
from typing import Any, Dict, List, Optional

from app.autonomy.safety import ActionClassification, AutonomyLevel

logger = logging.getLogger("kairo.autonomy.policies")


class PolicyDeniedError(Exception):
    """Raised when an autonomous operation violates governance policy or fail-closed invariants (Spec 176-179)."""


class DomainWorkflowType(str, Enum):
    RESEARCH = "RESEARCH"
    CODING = "CODING"
    DEBUGGING = "DEBUGGING"
    DEPLOYMENT = "DEPLOYMENT"
    MAINTENANCE = "MAINTENANCE"
    BROWSER = "BROWSER"
    COMPUTER_CONTROL = "COMPUTER_CONTROL"
    COMMUNICATION = "COMMUNICATION"
    PUBLISHING = "PUBLISHING"
    DELETION = "DELETION"


class AutonomyPolicyEngine:
    """Enforces fail-closed governance, action classifications, and domain workflow constraints (Spec 37, 176-190)."""

    def __init__(self, policy_service_available: bool = True, security_service_available: bool = True) -> None:
        self.policy_service_available = policy_service_available
        self.security_service_available = security_service_available

    def evaluate_action_policy(
        self,
        action_class: ActionClassification,
        target_resource: str,
        params: Dict[str, Any],
        is_approval_present: bool = False,
    ) -> bool:
        """Enforce Spec 176-180: Fail-closed principle for security/policy, degraded fail-safe for low risk."""
        # 1. Fail-safe principle for low-risk read-only (Spec 180)
        if action_class in [ActionClassification.READ, ActionClassification.ANALYZE]:
            return True

        # 2. Consequential operations: Fail-closed if policy service is down (Spec 176)
        if not self.policy_service_available:
            logger.critical("FAIL-CLOSED: Policy engine unavailable; consequential action '%s' blocked.", action_class.value)
            raise PolicyDeniedError("Policy evaluation unavailable: Fail-closed principle denies consequential operation.")

        # 3. Fail-closed if security service is down (Spec 177)
        if not self.security_service_available:
            logger.critical("FAIL-CLOSED: Security center unavailable; action '%s' blocked.", action_class.value)
            raise PolicyDeniedError("Security checks unavailable: Fail-closed principle denies consequential operation.")

        # 4. Consequential actions require explicit approvals if privileged/deploy/delete (Spec 178)
        if action_class in [ActionClassification.PRIVILEGED, ActionClassification.DEPLOY, ActionClassification.DELETE]:
            if not is_approval_present:
                logger.warning("Action '%s' on '%s' blocked: Missing mandatory human approval.", action_class.value, target_resource)
                raise PolicyDeniedError(f"Action '{action_class.value}' requires explicit approval before execution.")

        return True

    def validate_domain_workflow(self, workflow_type: DomainWorkflowType, step_metadata: Dict[str, Any]) -> None:
        """Validate specialized requirements for autonomous domains (Spec 181-190)."""
        # 1. Autonomous Coding (Spec 182): inspect -> plan -> modify -> test -> review -> verify
        if workflow_type == DomainWorkflowType.CODING:
            if step_metadata.get("is_modification") and not step_metadata.get("has_prior_test_plan"):
                raise PolicyDeniedError("Autonomous coding requires pre-defined test and review plan before modifying code.")

        # 2. Autonomous Deployment (Spec 184): inspect -> plan -> approval -> deploy -> health-check -> verify
        elif workflow_type == DomainWorkflowType.DEPLOYMENT:
            if not step_metadata.get("has_rollback_strategy"):
                raise PolicyDeniedError("Autonomous deployment requires a verified rollback strategy.")
            if not step_metadata.get("has_health_check"):
                raise PolicyDeniedError("Autonomous deployment requires automated post-deploy health check verification.")

        # 3. Autonomous Communication / Publishing (Spec 188, 189): recipient validation, content validation, approval
        elif workflow_type in [DomainWorkflowType.COMMUNICATION, DomainWorkflowType.PUBLISHING]:
            if not step_metadata.get("recipient_validated"):
                raise PolicyDeniedError("Autonomous communication requires explicit recipient validation.")
            if not step_metadata.get("content_safety_validated"):
                raise PolicyDeniedError("Autonomous publishing requires automated content safety validation.")

        # 4. Autonomous Deletion (Spec 190): exact target, scope, policy, approval, verification
        elif workflow_type == DomainWorkflowType.DELETION:
            target = step_metadata.get("target_resource", "")
            if not target or target in ["/", "*", "C:\\", "C:/", "~"]:
                raise PolicyDeniedError(f"Prohibited wide deletion target: '{target}'.")
            if not step_metadata.get("is_approved"):
                raise PolicyDeniedError("Deletion of persistent resources requires explicit human approval.")
