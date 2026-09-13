"""Pydantic v2 domain schemas and contracts for Kairo Autonomous Governance,
Constitutional Reasoning, Policy Intelligence & Authority Management Engine (Task 78).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class PrincipleName(str, Enum):
    """11 canonical constitutional principles."""
    SAFETY = "SAFETY"
    LEGALITY = "LEGALITY"
    USER_AUTHORITY = "USER_AUTHORITY"
    TRANSPARENCY = "TRANSPARENCY"
    AUDITABILITY = "AUDITABILITY"
    REVERSIBILITY = "REVERSIBILITY"
    PROPORTIONALITY = "PROPORTIONALITY"
    PRIVACY = "PRIVACY"
    SECURITY = "SECURITY"
    LEAST_PRIVILEGE = "LEAST_PRIVILEGE"
    HUMAN_OVERSIGHT = "HUMAN_OVERSIGHT"


class PrincipleStrictness(str, Enum):
    """Enforcement rigidity for constitutional principles."""
    MANDATORY = "MANDATORY"  # Violation immediately denies action
    STRICT = "STRICT"        # Violation requires human review
    ADVISORY = "ADVISORY"    # Violation warns but does not halt execution


class PolicyTier(str, Enum):
    """6-tier explicit policy hierarchy (rank 0 = highest, 5 = lowest)."""
    SYSTEM = "SYSTEM"        # Immutable root guardrails
    SECURITY = "SECURITY"    # SecOps / boundary rules
    TENANT = "TENANT"        # Organization-level policies
    PROJECT = "PROJECT"      # Project / workspace policies
    WORKFLOW = "WORKFLOW"    # Automation / mission policies
    TASK = "TASK"            # Individual task / step policies

    @property
    def rank(self) -> int:
        hierarchy_map = {
            PolicyTier.SYSTEM: 0,
            PolicyTier.SECURITY: 1,
            PolicyTier.TENANT: 2,
            PolicyTier.PROJECT: 3,
            PolicyTier.WORKFLOW: 4,
            PolicyTier.TASK: 5,
        }
        return hierarchy_map.get(self, 5)


class AuthorityLevel(str, Enum):
    """6 discrete authority levels (Authority != Capability)."""
    NONE = "NONE"            # Completely unprivileged / untrusted
    LIMITED = "LIMITED"      # Read-only or sandboxed execution only
    PROJECT = "PROJECT"      # Permitted within specified project boundaries
    TENANT = "TENANT"        # Permitted across organization tenant
    SYSTEM = "SYSTEM"        # Cross-tenant operational management
    ADMIN = "ADMIN"          # Absolute administrative authority

    @property
    def rank(self) -> int:
        rank_map = {
            AuthorityLevel.NONE: 0,
            AuthorityLevel.LIMITED: 1,
            AuthorityLevel.PROJECT: 2,
            AuthorityLevel.TENANT: 3,
            AuthorityLevel.SYSTEM: 4,
            AuthorityLevel.ADMIN: 5,
        }
        return rank_map.get(self, 0)


class GovernanceState(str, Enum):
    """8 lifecycle states of a governance decision."""
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    REQUIRES_APPROVAL = "REQUIRES_APPROVAL"
    REQUIRES_HUMAN = "REQUIRES_HUMAN"
    EXECUTABLE = "EXECUTABLE"
    EXPIRED = "EXPIRED"
    ABORTED = "ABORTED"


class GovernanceDecisionType(str, Enum):
    """Outcome determination of a governance evaluation."""
    ALLOWED = "ALLOWED"
    DENIED = "DENIED"
    REQUIRES_APPROVAL = "REQUIRES_APPROVAL"
    REQUIRES_HUMAN = "REQUIRES_HUMAN"
    CONFLICTING_POLICY = "CONFLICTING_POLICY"
    UNKNOWN = "UNKNOWN"


# ==============================================================================
# Domain Models
# ==============================================================================

class ConstitutionalPrinciple(BaseModel):
    """Machine-readable configurable principle."""
    model_config = ConfigDict(extra="ignore")

    principle_id: str = Field(default_factory=lambda: f"prn_{uuid.uuid4().hex[:8]}")
    name: PrincipleName
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    strictness: PrincipleStrictness = PrincipleStrictness.MANDATORY
    description: str = ""
    enabled: bool = True
    rules: list[dict[str, Any]] = Field(default_factory=list)


class ConstitutionModelSchema(BaseModel):
    """Configurable system constitution."""
    model_config = ConfigDict(extra="ignore")

    constitution_id: str = Field(default_factory=lambda: f"const_{uuid.uuid4().hex[:8]}")
    name: str = "Kairo Core Autonomous Constitution"
    version: str = "1.0.0"
    principles: list[ConstitutionalPrinciple] = Field(default_factory=list)
    is_active: bool = True
    created_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)


class AuthorityGrant(BaseModel):
    """Explicit grant of authority for an agent, user, or workflow."""
    model_config = ConfigDict(extra="ignore")

    grant_id: str = Field(default_factory=lambda: f"auth_{uuid.uuid4().hex[:8]}")
    subject_id: str
    subject_type: str = "AGENT"  # USER, AGENT, WORKFLOW
    authority_level: AuthorityLevel = AuthorityLevel.LIMITED
    allowed_scopes: list[str] = Field(default_factory=list)
    allowed_actions: list[str] = Field(default_factory=list)
    denied_actions: list[str] = Field(default_factory=list)
    max_risk_level: str = "R2_MODERATE"
    expires_at: datetime | None = None
    granted_by: str = "system"
    is_active: bool = True
    created_at: datetime = Field(default_factory=_now_utc)


class PrincipleEvaluationResult(BaseModel):
    """Evaluation output for a single constitutional principle."""
    model_config = ConfigDict(extra="ignore")

    principle: PrincipleName
    score: float = Field(default=1.0, ge=0.0, le=1.0)
    compliant: bool = True
    findings: str = ""
    citation: str = ""


class GoalAlignmentReport(BaseModel):
    """Assessment of whether an action advances user, project, and safety goals."""
    model_config = ConfigDict(extra="ignore")

    user_goals_aligned: bool = True
    project_goals_aligned: bool = True
    constitutional_aligned: bool = True
    safety_aligned: bool = True
    conflicts_detected: list[str] = Field(default_factory=list)


class LeastPrivilegeRecommendation(BaseModel):
    """Least-privilege analysis identifying minimal required authority."""
    model_config = ConfigDict(extra="ignore")

    minimum_permissions_needed: list[str] = Field(default_factory=list)
    excess_permissions_requested: list[str] = Field(default_factory=list)
    recommended_authority_level: AuthorityLevel = AuthorityLevel.LIMITED
    reduction_possible: bool = False


class AuthorityEscalationReport(BaseModel):
    """Assessment of privilege bypass, control weakening, or escalation attempts."""
    model_config = ConfigDict(extra="ignore")

    is_escalation_attempt: bool = False
    bypass_technique: str | None = None
    severity: str = "LOW"
    rationale: str = ""
    flagged_actions: list[str] = Field(default_factory=list)


class GovernanceReviewRequest(BaseModel):
    """Input contract requesting pre-execution governance review."""
    model_config = ConfigDict(extra="ignore")

    review_id: str = Field(default_factory=lambda: f"gov_req_{uuid.uuid4().hex[:8]}")
    goal: str
    action: str
    resource: str = ""
    target_entity: str = ""
    risk_level: str = "R1_LOW"
    caller_id: str = "default_agent"
    caller_authority: AuthorityLevel = AuthorityLevel.LIMITED
    required_permissions: list[str] = Field(default_factory=list)  # READ, WRITE, EXECUTE, DESTRUCTIVE
    is_irreversible: bool = False
    is_destructive: bool = False
    uncertainty_score: float = Field(default=0.0, ge=0.0, le=1.0)
    tenant_id: str = "default_tenant"
    project_id: str | None = None
    context_metadata: dict[str, Any] = Field(default_factory=dict)


class GovernanceDecisionResult(BaseModel):
    """Authoritative output of the governance reasoning engine."""
    model_config = ConfigDict(extra="ignore")

    review_id: str
    decision: GovernanceDecisionType
    state: GovernanceState
    authority_level_granted: AuthorityLevel
    authority_check_passed: bool
    policy_tier_applied: PolicyTier | None = None
    policy_id_applied: str | None = None
    constitutional_score: float = Field(default=1.0, ge=0.0, le=1.0)
    principle_evaluations: list[PrincipleEvaluationResult] = Field(default_factory=list)
    goal_alignment: GoalAlignmentReport = Field(default_factory=GoalAlignmentReport)
    least_privilege: LeastPrivilegeRecommendation = Field(default_factory=LeastPrivilegeRecommendation)
    escalation_report: AuthorityEscalationReport = Field(default_factory=AuthorityEscalationReport)
    requires_human: bool = False
    human_handoff_packet: dict[str, Any] | None = None
    evidence: list[str] = Field(default_factory=list)
    explanation: str = ""
    evaluated_at: datetime = Field(default_factory=_now_utc)


class GovernanceDashboardSummary(BaseModel):
    """Consolidated metrics and health indicators for the Governance Command Center."""
    model_config = ConfigDict(extra="ignore")

    active_policies_by_tier: dict[str, int] = Field(default_factory=dict)
    active_authority_grants_count: int = 0
    pending_human_reviews_count: int = 0
    recent_escalations_count: int = 0
    constitutional_compliance_index: float = 1.0
    timestamp: datetime = Field(default_factory=_now_utc)
