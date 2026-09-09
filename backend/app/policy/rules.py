"""Baseline system governance policies for Kairo (Task 36).

Provides sensible, secure defaults:
- Low-risk read operations default to ALLOW.
- High-risk/critical operations fail closed or require approvals.
- Production mutations require approval.
- Secrets and financial actions are strictly guarded.
"""

from app.policy.schemas import (
    ConditionOperator,
    PolicyDecisionType,
    PolicyRule,
    PolicyRuleCondition,
    PolicyScope,
)

DEFAULT_SYSTEM_POLICIES: list[PolicyRule] = [
    # 1. Emergency Stop Policy (Highest Priority System Deny)
    PolicyRule(
        policy_id="sys-emergency-stop",
        name="System Emergency Stop Enforcement",
        description="Blocks all actions when system emergency stop is triggered.",
        version=1,
        enabled=True,
        is_system=True,
        priority=1000,
        scope=PolicyScope.GLOBAL,
        conditions=[
            PolicyRuleCondition(field="world_state.emergency_stop", operator=ConditionOperator.EQUALS, value=True)
        ],
        decision=PolicyDecisionType.DENY,
        reason_code="EMERGENCY_STOP_ACTIVE",
        safe_explanation="Action blocked: Emergency Stop is active across the system.",
    ),

    # 2. Production Deployment Human Approval Gate
    PolicyRule(
        policy_id="sys-prod-deploy-approval",
        name="Production Deployment Human Approval Gate",
        description="Mandates formal human approval for any deployment to production.",
        version=1,
        enabled=True,
        is_system=True,
        priority=900,
        scope=PolicyScope.ENVIRONMENT,
        target_scope_id="production",
        conditions=[
            PolicyRuleCondition(field="environment", operator=ConditionOperator.EQUALS, value="production"),
            PolicyRuleCondition(field="action", operator=ConditionOperator.CONTAINS, value="deploy"),
        ],
        decision=PolicyDecisionType.REQUIRE_APPROVAL,
        reason_code="PRODUCTION_REQUIRES_APPROVAL",
        safe_explanation="Production deployments require formal human approval.",
    ),

    # 3. Production Deletion Guard
    PolicyRule(
        policy_id="sys-prod-delete-guard",
        name="Production Resource Deletion Guard",
        description="Requires formal approval for resource deletions in production.",
        version=1,
        enabled=True,
        is_system=True,
        priority=900,
        scope=PolicyScope.ENVIRONMENT,
        target_scope_id="production",
        conditions=[
            PolicyRuleCondition(field="environment", operator=ConditionOperator.EQUALS, value="production"),
            PolicyRuleCondition(field="action", operator=ConditionOperator.CONTAINS, value="delete"),
        ],
        decision=PolicyDecisionType.REQUIRE_APPROVAL,
        reason_code="PRODUCTION_DELETE_REQUIRES_APPROVAL",
        safe_explanation="Deleting production resources requires formal human approval.",
    ),

    # 4. Financial Actions Guard
    PolicyRule(
        policy_id="sys-financial-action-guard",
        name="Financial Operation Security Guard",
        description="Mandates human approval and step-up auth for any financial transactions.",
        version=1,
        enabled=True,
        is_system=True,
        priority=950,
        scope=PolicyScope.GLOBAL,
        conditions=[
            PolicyRuleCondition(field="action", operator=ConditionOperator.IN, value=["pay", "billing", "transfer", "purchase"]),
        ],
        decision=PolicyDecisionType.REQUIRE_APPROVAL,
        reason_code="FINANCIAL_REQUIRES_APPROVAL",
        safe_explanation="Financial transactions require verified authorization and human approval.",
    ),

    # 5. Read-Only Default Allowance (Section 11)
    PolicyRule(
        policy_id="sys-read-only-allow",
        name="Safe Read-Only Operations Default Allowance",
        description="Permits safe read, inspect, and status queries across environments.",
        version=1,
        enabled=True,
        is_system=True,
        priority=50,
        scope=PolicyScope.GLOBAL,
        conditions=[
            PolicyRuleCondition(field="action", operator=ConditionOperator.IN, value=["read", "get", "list", "search", "inspect", "status", "view"]),
        ],
        decision=PolicyDecisionType.ALLOW,
        reason_code="READ_ONLY_PERMITTED",
        safe_explanation="Read-only operation permitted.",
    ),

    # 6. Development / Test Local Execution Allowance
    PolicyRule(
        policy_id="sys-dev-local-allow",
        name="Development Environment Standard Action Allowance",
        description="Permits standard development actions within dev and test environments.",
        version=1,
        enabled=True,
        is_system=True,
        priority=100,
        scope=PolicyScope.ENVIRONMENT,
        target_scope_id="development",
        conditions=[
            PolicyRuleCondition(field="environment", operator=ConditionOperator.IN, value=["development", "test"]),
        ],
        decision=PolicyDecisionType.ALLOW,
        reason_code="DEV_ENVIRONMENT_PERMITTED",
        safe_explanation="Standard execution permitted in development environment.",
    ),

    # 7. Staging Deployment Policy (Section 121)
    PolicyRule(
        policy_id="sys-staging-deploy-allow",
        name="Staging Deployment Policy",
        description="Permits deployments to staging with environment limits.",
        version=1,
        enabled=True,
        is_system=True,
        priority=200,
        scope=PolicyScope.ENVIRONMENT,
        target_scope_id="staging",
        conditions=[
            PolicyRuleCondition(field="environment", operator=ConditionOperator.EQUALS, value="staging"),
            PolicyRuleCondition(field="action", operator=ConditionOperator.CONTAINS, value="deploy"),
        ],
        decision=PolicyDecisionType.ALLOW,
        reason_code="STAGING_DEPLOY_PERMITTED",
        safe_explanation="Deployment to staging environment is permitted.",
    ),
]
