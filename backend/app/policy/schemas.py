"""Pydantic schemas and enums for Kairo Governance and Policy Engine (Task 36)."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
import uuid

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


def generate_eval_id() -> str:
    return f"pol_eval_{uuid.uuid4().hex[:16]}"


# ==========================================
# Enums
# ==========================================

class PolicyDecisionType(str, Enum):
    """Supported deterministic policy decisions."""
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_CONFIRMATION = "REQUIRE_CONFIRMATION"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    REQUIRE_STEP_UP_AUTH = "REQUIRE_STEP_UP_AUTH"
    ALLOW_WITH_LIMITS = "ALLOW_WITH_LIMITS"
    DEFER = "DEFER"


class RiskLevel(str, Enum):
    """Deterministic 5-tier risk taxonomy."""
    R0_READ_ONLY = "R0_READ_ONLY"
    R1_LOW = "R1_LOW"
    R2_MODERATE = "R2_MODERATE"
    R3_HIGH = "R3_HIGH"
    R4_CRITICAL = "R4_CRITICAL"

    @property
    def severity(self) -> int:
        severity_map = {
            RiskLevel.R0_READ_ONLY: 0,
            RiskLevel.R1_LOW: 1,
            RiskLevel.R2_MODERATE: 2,
            RiskLevel.R3_HIGH: 3,
            RiskLevel.R4_CRITICAL: 4,
        }
        return severity_map.get(self, 1)


class DataClassification(str, Enum):
    """Categorization for data sensitivity & governance."""
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    PRIVATE = "PRIVATE"
    SENSITIVE = "SENSITIVE"
    RESTRICTED = "RESTRICTED"

    @property
    def rank(self) -> int:
        rank_map = {
            DataClassification.PUBLIC: 0,
            DataClassification.INTERNAL: 1,
            DataClassification.PRIVATE: 2,
            DataClassification.SENSITIVE: 3,
            DataClassification.RESTRICTED: 4,
        }
        return rank_map.get(self, 0)


class PolicyScope(str, Enum):
    """Hierarchical scope categories where policies apply."""
    GLOBAL = "GLOBAL"
    USER = "USER"
    PROJECT = "PROJECT"
    ENVIRONMENT = "ENVIRONMENT"
    DEVICE = "DEVICE"
    SESSION = "SESSION"
    TASK = "TASK"
    TOOL = "TOOL"
    SKILL = "SKILL"
    DATA_TYPE = "DATA_TYPE"


class ConditionOperator(str, Enum):
    """Deterministic typed condition evaluation operators (non-Turing complete)."""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    BEFORE = "before"
    AFTER = "after"
    EXISTS = "exists"


# ==========================================
# Policy Rule & Condition Models
# ==========================================

class PolicyRuleCondition(BaseModel):
    """Deterministic condition statement."""
    field: str = Field(..., description="Dotted path in context, e.g. 'environment', 'risk.level', 'device.is_trusted'")
    operator: ConditionOperator = Field(..., description="Condition operator")
    value: Any = Field(default=None, description="Expected value or set to evaluate against")


class PolicyRule(BaseModel):
    """Declarative Governance Policy schema."""
    policy_id: str = Field(..., description="Unique policy identifier")
    name: str = Field(..., description="Human-readable policy name")
    description: str = Field(default="", description="Detailed policy purpose and operational guidance")
    version: int = Field(default=1, description="Integer version of this policy")
    enabled: bool = Field(default=True, description="Whether this policy is active")
    is_system: bool = Field(default=False, description="System immutable policy that cannot be deleted by non-root")
    shadow_mode: bool = Field(default=False, description="If true, evaluates and logs decisions without enforcing")
    priority: int = Field(default=100, description="Priority score; DENY takes precedence in conflicts")
    scope: PolicyScope = Field(default=PolicyScope.GLOBAL, description="Scope tier where policy applies")
    target_scope_id: str | None = Field(default=None, description="Target entity ID if scope is specific (e.g. project_id)")
    conditions: list[PolicyRuleCondition] = Field(default_factory=list, description="All conditions must match (AND)")
    decision: PolicyDecisionType = Field(..., description="Policy decision when conditions match")
    reason_code: str | None = Field(default=None, description="Machine-readable reason code")
    safe_explanation: str | None = Field(default=None, description="User-facing safe explanation")
    constraints: dict[str, Any] = Field(default_factory=dict, description="Operational limits, budgets, or boundaries")
    created_by: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


# ==========================================
# Policy Evaluation Context & Decision
# ==========================================

class PolicyContext(BaseModel):
    """Input payload strictly containing only verified facts needed for policy evaluation."""
    user: dict[str, Any] | None = Field(default=None, description="User info: id, role, tier, permissions")
    session: dict[str, Any] | None = Field(default=None, description="Session info: id, authenticated_at, age_minutes, mfa")
    device: dict[str, Any] | None = Field(default=None, description="Device info: id, is_trusted, device_class, capabilities, revoked")
    project: dict[str, Any] | None = Field(default=None, description="Project info: id, repositories, environments, active")
    environment: str = Field(default="development", description="Environment: development, test, staging, production")
    action: str | None = Field(default=None, description="Action verb: read, write, deploy, delete, send, execute_tool, etc.")
    target: dict[str, Any] | str | None = Field(default=None, description="Action target: resource, path, repo, account, etc.")
    intent: dict[str, Any] | None = Field(default=None, description="Structured intent context: id, type, objective, confidence")
    task: dict[str, Any] | None = Field(default=None, description="Autonomous task context: id, budget, steps_taken, duration_sec")
    tool: dict[str, Any] | str | None = Field(default=None, description="Tool details: name, required_scopes, declared_risk")
    skill: dict[str, Any] | str | None = Field(default=None, description="Skill details: name, capabilities, risk_class")
    data_scope: dict[str, Any] | None = Field(default=None, description="Data scope: classification, contains_secrets, bulk_export")
    risk: dict[str, Any] | RiskLevel | str | None = Field(default=None, description="Preliminary or computed risk info")
    world_state: dict[str, Any] | None = Field(default=None, description="World state: emergency_stop, change_freeze, incident_mode")
    provider_model: dict[str, Any] | None = Field(default=None, description="Target LLM provider & model if applicable")


class PolicyDecision(BaseModel):
    """Standardized deterministic output of a policy evaluation."""
    decision: PolicyDecisionType = Field(..., description="Final policy determination")
    policy_id: str | None = Field(default=None, description="Primary matching policy ID")
    policy_version: int | None = Field(default=None, description="Primary matching policy version")
    reason_code: str | None = Field(default=None, description="Canonical reason code, e.g. PRODUCTION_REQUIRES_APPROVAL")
    safe_explanation: str = Field(..., description="User-safe concise explanation")
    constraints: dict[str, Any] = Field(default_factory=dict, description="Operational boundaries & limits")
    required_approval: dict[str, Any] | str | None = Field(default=None, description="Required approval details if any")
    required_authentication: dict[str, Any] | str | None = Field(default=None, description="Required auth or step-up MFA")
    allowed_scope: dict[str, Any] = Field(default_factory=dict, description="Constrained scope allowed for execution")
    risk_level: RiskLevel = Field(default=RiskLevel.R1_LOW, description="Assessed risk level")
    expires_at: datetime | None = Field(default=None, description="Decision validity expiration")
    evaluation_id: str = Field(default_factory=generate_eval_id, description="Traceable evaluation UUID")
    matched_policies: list[str] = Field(default_factory=list, description="IDs of all policies that matched")
    shadow_decisions: list[dict[str, Any]] = Field(default_factory=list, description="Decisions from shadow-mode policies")
    simulated: bool = Field(default=False, description="True if evaluation was simulation only")
    timestamp: datetime = Field(default_factory=utc_now)


# ==========================================
# Requests & Responses
# ==========================================

class PolicyEvaluateRequest(BaseModel):
    """Request payload for policy evaluation."""
    context: PolicyContext
    simulate: bool = False


class PolicySimulationRequest(BaseModel):
    """Request to simulate policy evaluation against hypothetical rules."""
    context: PolicyContext
    candidate_policy: PolicyRule | None = None


class PolicySimulationResponse(BaseModel):
    """Response containing simulation decision and full evaluation trace."""
    decision: PolicyDecision
    evaluated_policies_count: int
    trace: list[dict[str, Any]] = Field(default_factory=list)


class PolicyCreateRequest(BaseModel):
    """Request to create a new governance policy."""
    policy_id: str
    name: str
    description: str = ""
    priority: int = 100
    scope: PolicyScope = PolicyScope.GLOBAL
    target_scope_id: str | None = None
    conditions: list[PolicyRuleCondition] = []
    decision: PolicyDecisionType
    reason_code: str | None = None
    safe_explanation: str | None = None
    constraints: dict[str, Any] = {}
    shadow_mode: bool = False


class PolicyUpdateRequest(BaseModel):
    """Request to update an existing governance policy (creates new version)."""
    name: str | None = None
    description: str | None = None
    priority: int | None = None
    conditions: list[PolicyRuleCondition] | None = None
    decision: PolicyDecisionType | None = None
    reason_code: str | None = None
    safe_explanation: str | None = None
    constraints: dict[str, Any] | None = None
    enabled: bool | None = None
    shadow_mode: bool | None = None


class PolicyRollbackRequest(BaseModel):
    """Request to roll back a policy to a previous version."""
    target_version: int
    reason: str


class PolicyStatusResponse(BaseModel):
    """Health & statistics of the policy engine."""
    total_policies: int
    active_policies: int
    shadow_policies: int
    system_policies: int
    emergency_stop_active: bool
    safe_mode_active: bool
    change_freeze_environments: list[str] = []
    incident_mode: bool = False
    cached_decisions_count: int
