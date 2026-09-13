"""SQLAlchemy ORM models for Kairo Autonomous Governance, Constitutional Reasoning,
and Authority Management (Task 78).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class ConstitutionRecordModel(Base):
    """Machine-readable system constitutions and versions."""

    __tablename__ = "constitutions"

    constitution_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(32), default="1.0.0", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, onupdate=_now_utc, nullable=False)

    principles: Mapped[list[ConstitutionalPrincipleModel]] = relationship(
        "ConstitutionalPrincipleModel", back_populates="constitution", cascade="all, delete-orphan"
    )


class ConstitutionalPrincipleModel(Base):
    """Configurable principles governing autonomous deliberation and execution."""

    __tablename__ = "constitutional_principles"

    principle_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    constitution_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("constitutions.constitution_id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    strictness: Mapped[str] = mapped_column(String(32), default="MANDATORY", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    rules_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)

    constitution: Mapped[ConstitutionRecordModel] = relationship("ConstitutionRecordModel", back_populates="principles")


class AuthorityGrantModel(Base):
    """Discrete grants of authority separating authorization from raw capability."""

    __tablename__ = "authority_grants"

    grant_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    subject_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    subject_type: Mapped[str] = mapped_column(String(32), default="AGENT", nullable=False)
    authority_level: Mapped[str] = mapped_column(String(32), default="LIMITED", index=True, nullable=False)
    allowed_scopes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    allowed_actions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    denied_actions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    max_risk_level: Mapped[str] = mapped_column(String(32), default="R2_MODERATE", nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    granted_by: Mapped[str] = mapped_column(String(64), default="system", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)


class GovernanceDecisionRecordModel(Base):
    """Provenance audit ledger for governance reviews and constitutional citations."""

    __tablename__ = "governance_decisions"

    decision_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    review_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), server_default="default_tenant", index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    caller_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    decision: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    state: Mapped[str] = mapped_column(String(32), default="EXECUTABLE", index=True, nullable=False)
    authority_check_passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    policy_tier_applied: Mapped[str | None] = mapped_column(String(32), nullable=True)
    constitutional_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    requires_human: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    evidence_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)


class AuthorityEscalationIncidentModel(Base):
    """Audit log of detected privilege escalation, control weakening, or bypass attempts."""

    __tablename__ = "authority_escalation_incidents"

    incident_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    caller_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    bypass_technique: Mapped[str | None] = mapped_column(String(128), nullable=True)
    severity: Mapped[str] = mapped_column(String(32), default="LOW", nullable=False)
    rationale: Mapped[str] = mapped_column(Text, default="", nullable=False)
    flagged_actions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
