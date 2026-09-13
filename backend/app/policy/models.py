"""SQLAlchemy models for Kairo Governance and Policy Engine (Task 36)."""

from datetime import UTC, datetime
from typing import Any
import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


def generate_uuid() -> str:
    return str(uuid.uuid4())


class GovernancePolicyModel(Base):
    """Stores declarative governance and security policies."""

    __tablename__ = "governance_policies"

    policy_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    shadow_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    scope: Mapped[str] = mapped_column(String(32), nullable=False, default="GLOBAL")
    target_scope_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    conditions_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    safe_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    constraints_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    __table_args__ = (
        Index("ix_governance_policies_scope", "scope"),
        Index("ix_governance_policies_enabled", "enabled"),
        Index("ix_governance_policies_priority", "priority"),
    )


class PolicyEvaluationModel(Base):
    """Stores provenance records for policy decisions."""

    __tablename__ = "policy_evaluations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    policy_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    policy_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    project_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    environment: Mapped[str | None] = mapped_column(String(32), nullable=True)
    action: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    target: Mapped[str | None] = mapped_column(String(256), nullable=True)
    tool_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    skill_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    safe_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    constraints_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    required_approval: Mapped[str | None] = mapped_column(String(64), nullable=True)
    required_authentication: Mapped[str | None] = mapped_column(String(64), nullable=True)
    allowed_scope_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    matched_policies_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    is_simulated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_policy_evaluations_created_at", "created_at"),
    )


# Re-export Task 78 Autonomous Governance models
from app.policy.governance_models import (
    AuthorityEscalationIncidentModel,
    AuthorityGrantModel,
    ConstitutionRecordModel,
    ConstitutionalPrincipleModel,
    GovernanceDecisionRecordModel,
)

__all__ = [
    "GovernancePolicyModel",
    "PolicyEvaluationModel",
    "ConstitutionRecordModel",
    "ConstitutionalPrincipleModel",
    "AuthorityGrantModel",
    "GovernanceDecisionRecordModel",
    "AuthorityEscalationIncidentModel",
]
