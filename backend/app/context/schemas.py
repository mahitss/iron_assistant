"""Pydantic schemas and enums for Kairo Personal Context Engine."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ContextType(str, Enum):
    """Categories of contextual knowledge sources."""

    SESSION_CONTEXT = "SESSION_CONTEXT"
    PROJECT_CONTEXT = "PROJECT_CONTEXT"
    CONVERSATION_CONTEXT = "CONVERSATION_CONTEXT"
    MEMORY_CONTEXT = "MEMORY_CONTEXT"
    WORKFLOW_CONTEXT = "WORKFLOW_CONTEXT"
    DEVELOPER_CONTEXT = "DEVELOPER_CONTEXT"
    PROACTIVE_CONTEXT = "PROACTIVE_CONTEXT"


class MemoryScope(str, Enum):
    """Durable memory access boundaries."""

    SESSION = "SESSION"
    PROJECT = "PROJECT"
    GLOBAL_USER = "GLOBAL_USER"


class MemorySource(str, Enum):
    """Origin of a persisted memory record."""

    USER_EXPLICIT = "USER_EXPLICIT"
    USER_CONVERSATION = "USER_CONVERSATION"
    SYSTEM_DERIVED = "SYSTEM_DERIVED"


class ProjectStatus(str, Enum):
    """Lifecycle state of a user project."""

    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class ContextItem(BaseModel):
    """Single item of contextual knowledge with provenance and relevance metadata."""

    source_type: ContextType
    source_id: str
    title: str
    content: str
    relevance_score: float = 0.0
    confidence: float | None = None
    timestamp: datetime | None = None
    provenance: str | None = None
    reason: str | None = None

    model_config = ConfigDict(frozen=True)


class ProjectCreate(BaseModel):
    """Payload to create a new project."""

    name: str = Field(..., min_length=1, max_length=100, description="Project name")
    description: str | None = Field(default=None, max_length=1000, description="Optional description")
    status: ProjectStatus = Field(default=ProjectStatus.ACTIVE, description="Initial project status")


class ProjectUpdate(BaseModel):
    """Payload to update an existing project."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    status: ProjectStatus | None = None


class ProjectRepositoryLink(BaseModel):
    """Payload to link a repository to a project."""

    repository_path: str = Field(
        ..., min_length=1, max_length=500, description="Local or remote repository path"
    )
    is_primary: bool = Field(default=False, description="Whether this is the primary repository")


class ProjectWorkflowLink(BaseModel):
    """Payload to link a workflow to a project."""

    workflow_id: str = Field(..., min_length=1, description="Workflow identifier")


class ProjectResponse(BaseModel):
    """Detailed project representation with linked resources."""

    id: str
    user_id: str
    name: str
    description: str | None = None
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
    last_active_at: datetime
    repositories: list[str] = Field(default_factory=list)
    workflows: list[str] = Field(default_factory=list)
    conversations: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ContextSettings(BaseModel):
    """User context personalization preferences."""

    user_id: str
    context_enabled: bool = True
    memory_enabled: bool = True
    project_context_enabled: bool = True
    proactive_context_enabled: bool = True
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ContextSettingsUpdate(BaseModel):
    """Payload to modify context personalization preferences."""

    context_enabled: bool | None = None
    memory_enabled: bool | None = None
    project_context_enabled: bool | None = None
    proactive_context_enabled: bool | None = None


class ContextPacket(BaseModel):
    """Bounded, prioritized packet of contextual information injected into agent prompts."""

    session_id: str | None = None
    user_id: str | None = None
    active_project: ProjectResponse | None = None
    items: list[ContextItem] = Field(default_factory=list)
    session_context: list[ContextItem] = Field(default_factory=list)
    project_context: list[ContextItem] = Field(default_factory=list)
    conversation_context: list[ContextItem] = Field(default_factory=list)
    memory_context: list[ContextItem] = Field(default_factory=list)
    workflow_context: list[ContextItem] = Field(default_factory=list)
    developer_context: list[ContextItem] = Field(default_factory=list)
    proactive_context: list[ContextItem] = Field(default_factory=list)
    ambiguous_projects: list[str] = Field(default_factory=list)
    requires_disambiguation: bool = False
    clarification_prompt: str | None = None
    total_items: int = 0

    def to_prompt_context(self) -> str:
        """Format bounded context packet into a concise prompt block."""
        if not self.items and not self.active_project and not self.ambiguous_projects:
            return ""

        sections: list[str] = []

        if self.active_project:
            proj_line = (
                f"Active Project: {self.active_project.name} (Status: {self.active_project.status.value})"
            )
            if self.active_project.repositories:
                proj_line += f" | Repositories: {', '.join(self.active_project.repositories)}"
            sections.append(proj_line)

        # Group items by source type
        grouped: dict[str, list[str]] = {}
        for item in self.items:
            key = item.source_type.value.replace("_CONTEXT", "").title()
            if key not in grouped:
                grouped[key] = []
            reason_str = f" [{item.reason}]" if item.reason else ""
            if item.source_type == ContextType.MEMORY_CONTEXT:
                grouped[key].append(f"- {item.content}")
            else:
                grouped[key].append(f"• {item.title}: {item.content}{reason_str}")

        for cat, lines in grouped.items():
            if cat.lower() == "memory":
                sections.append("Relevant memories:\n" + "\n".join(lines))
            else:
                sections.append(f"[{cat} Context]\n" + "\n".join(lines))

        return "\n\n".join(sections)
