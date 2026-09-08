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
        return f"<AgentTask(id='{self.id}', agent='{self.agent_type}', status='{self.status}')>"


class AgentTaskResult(Base):
    """Stores structured outputs, classified evidence, and citations for a completed agent task."""

    __tablename__ = "agent_task_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_json: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    structured_output_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    citations_json: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    tool_calls_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    def __repr__(self) -> str:
        return f"<AgentTaskResult(task_id='{self.task_id}', status='{self.status}')>"
