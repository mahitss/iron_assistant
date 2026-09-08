"""SQLAlchemy models for Projects, Project Resource Links, and Context Personalization."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utc_now() -> datetime:
    """Generate timezone-aware UTC current timestamp."""
    return datetime.now(UTC)


class Project(Base):
    """Represents a discrete user endeavor, workspace, or codebase with linked resources."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )

    # Relationships
    repositories: Mapped[list["ProjectRepository"]] = relationship(
        "ProjectRepository",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    workflows: Mapped[list["ProjectWorkflow"]] = relationship(
        "ProjectWorkflow",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    conversations: Mapped[list["ProjectConversation"]] = relationship(
        "ProjectConversation",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_projects_user_status", "user_id", "status"),
        Index("ix_projects_user_name", "user_id", "name"),
    )

    def __repr__(self) -> str:
        return f"<Project(id='{self.id}', name='{self.name}', status='{self.status}')>"


class ProjectRepository(Base):
    """Links a project to a local or remote code repository path."""

    __tablename__ = "project_repositories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    repository_path: Mapped[str] = mapped_column(String(512), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    project: Mapped["Project"] = relationship("Project", back_populates="repositories")

    __table_args__ = (Index("ix_project_repo_path", "project_id", "repository_path"),)


class ProjectWorkflow(Base):
    """Links an automated workflow to a project."""

    __tablename__ = "project_workflows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    workflow_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workflows.id", ondelete="CASCADE"), index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    project: Mapped["Project"] = relationship("Project", back_populates="workflows")


class ProjectConversation(Base):
    """Links a conversation session thread to a project."""

    __tablename__ = "project_conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    project: Mapped["Project"] = relationship("Project", back_populates="conversations")


class UserContextSettings(Base):
    """User-level personalization switches and context preferences."""

    __tablename__ = "user_context_settings"

    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    context_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    memory_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    project_context_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    proactive_context_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
