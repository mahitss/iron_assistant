"""SQLAlchemy declarative models for agent tasks and execution results."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def utc_now() -> datetime:
    """Generate timezone-aware UTC current timestamp."""
    return datetime.now(UTC)


class AgentTask(Base):
    """Represents an individual sub-agent task within an orchestrated plan."""

    __tablename__ = "agent_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    parent_task_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    agent_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="PENDING", index=True
    )  # PENDING, RUNNING, WAITING_APPROVAL, COMPLETED, FAILED, CANCELLED, TIMED_OUT
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    dependencies: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_agent_tasks_user_session", "user_id", "session_id"),
        Index("ix_agent_tasks_user_status", "user_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<AgentTaskResult(task_id='{self.task_id}', status='{self.status}')>"


class AgentContractModel(Base):
    """Authoritative contract governing agent objective, scope boundaries, budget, and verification."""

    __tablename__ = "agent_contracts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"ctr_{uuid.uuid4().hex[:12]}")
    collaboration_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    parent_goal: Mapped[str] = mapped_column(Text, nullable=False)
    assigned_objective: Mapped[str] = mapped_column(Text, nullable=False)
    agent_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    agent_role: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE", index=True)
    scope_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    inputs_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    expected_outputs_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    constraints_json: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    budget_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    success_criteria_json: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    verification_requirements_json: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    permissions_json: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    __table_args__ = (
        Index("ix_agent_contracts_collab_agent", "collaboration_id", "agent_id"),
        Index("ix_agent_contracts_user_status", "user_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<AgentContract(id='{self.id}', agent='{self.agent_id}', status='{self.status}')>"


class AgentCollaborationModel(Base):
    """Multi-agent collaboration session coordinating specialists under supervisor oversight."""

    __tablename__ = "agent_collaborations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"collab_{uuid.uuid4().hex[:12]}")
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    supervisor_id: Mapped[str] = mapped_column(String(64), nullable=False, default="supervisor_default")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PLANNING", index=True)
    plan_dag_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    participants_json: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    synthesis_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False, default="UNVERIFIED", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    __table_args__ = (
        Index("ix_agent_collaborations_user_proj", "user_id", "project_id"),
        Index("ix_agent_collaborations_user_status", "user_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<AgentCollaboration(id='{self.id}', status='{self.status}')>"


class AgentMessageModel(Base):
    """Authenticated, scoped message communicated between specialist agents and supervisor."""

    __tablename__ = "agent_messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"msg_{uuid.uuid4().hex[:12]}")
    collaboration_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    contract_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    sender_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    recipient_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    message_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    evidence_refs: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="NORMAL")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_agent_messages_collab_sender", "collaboration_id", "sender_id"),
        Index("ix_agent_messages_collab_recipient", "collaboration_id", "recipient_id"),
        Index("ix_agent_messages_created", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AgentMessage(id='{self.id}', type='{self.message_type}', sender='{self.sender_id}')>"


class AgentDisagreementModel(Base):
    """Tracks contradictions or disagreements between specialist agents for evidence-first resolution."""

    __tablename__ = "agent_disagreements"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"dis_{uuid.uuid4().hex[:12]}")
    collaboration_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(256), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default="MEDIUM", index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN", index=True)
    participants_json: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    claims_json: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    evidence_json: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    resolution_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    def __repr__(self) -> str:
        return f"<AgentDisagreement(id='{self.id}', subject='{self.subject[:30]}', status='{self.status}')>"


class AgentWorkspaceArtifactModel(Base):
    """Structured collaborative artifact published by an agent to the shared team workspace."""

    __tablename__ = "agent_workspace_artifacts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"art_{uuid.uuid4().hex[:12]}")
    collaboration_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    contract_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    creator_agent_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    artifact_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    scope_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    content_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_agent_artifacts_collab_creator", "collaboration_id", "creator_agent_id"),
        Index("ix_agent_artifacts_collab_type", "collaboration_id", "artifact_type"),
    )

    def __repr__(self) -> str:
        return f"<AgentWorkspaceArtifact(id='{self.id}', type='{self.artifact_type}', title='{self.title[:30]}')>"

