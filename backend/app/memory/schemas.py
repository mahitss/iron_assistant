"""Pydantic schemas for memory operations and representations."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    """Categorization of long-term memories."""

    PREFERENCE = "preference"
    FACT = "fact"
    PROJECT = "project"
    INSTRUCTION = "instruction"
    CONTEXT = "context"

    @classmethod
    def from_str(cls, value: str) -> "MemoryType":
        try:
            return cls(value.strip().lower())
        except (ValueError, AttributeError):
            return cls.FACT


class MemoryCreate(BaseModel):
    """Schema for explicitly creating a new long-term memory."""

    content: str = Field(..., min_length=1, max_length=5000, description="Memory text content")
    memory_type: MemoryType = Field(default=MemoryType.FACT, description="Category of memory")
    importance: float = Field(default=0.5, ge=0.0, le=1.0, description="Priority weight (0.0 to 1.0)")
    source: str | None = Field(default="user_explicit", description="Origin of the memory")


class MemoryUpdate(BaseModel):
    """Schema for updating an existing long-term memory."""

    content: str | None = Field(default=None, min_length=1, max_length=5000)
    memory_type: MemoryType | None = None
    importance: float | None = Field(default=None, ge=0.0, le=1.0)


class MemoryResponse(BaseModel):
    """Clean representation of a stored memory (does not expose raw vectors)."""

    id: str
    content: str
    memory_type: str
    importance: float
    source: str | None = None
    created_at: datetime
    updated_at: datetime
    last_accessed_at: datetime | None = None

    model_config = {"from_attributes": True}


class MemorySearchResult(BaseModel):
    """Result of semantic memory search including relevance score."""

    memory: MemoryResponse
    similarity: float = Field(..., description="Cosine similarity score (0.0 to 1.0)")
    score: float = Field(..., description="Combined ranking score including importance and recency")


class ConversationContext(BaseModel):
    """Formatted representation of recent history and relevant memories."""

    session_id: str
    recent_messages: list[dict[str, Any]] = Field(default_factory=list)
    relevant_memories: list[str] = Field(default_factory=list)


class MemoryCandidate(BaseModel):
    """Candidate memory proposed by the memory extraction layer before policy validation."""

    content: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Extracted durable statement in clear declarative form",
        examples=["The user prefers dark mode in all development environments."],
    )
    memory_type: MemoryType = Field(
        default=MemoryType.FACT,
        description="Categorization of the candidate memory",
    )
    importance: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Proposed priority weight (0.0 to 1.0)",
    )
    reason: str | None = Field(
        default=None,
        max_length=200,
        description="Brief justification for why this memory is durable",
    )


class MemoryExtractionResult(BaseModel):
    """Container schema for candidate memories proposed by the model."""

    candidates: list[MemoryCandidate] = Field(
        default_factory=list,
        description="Collection of extracted memory candidates",
    )

