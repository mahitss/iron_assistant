"""Typed entity relationship models and registry for Kairo World Model (Task 32, Spec 22-24)."""

from datetime import UTC, datetime
from enum import Enum
import hashlib
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class RelationshipType(str, Enum):
    """Explicit, authorized relationship types connecting entities (Spec 23)."""

    OWNS = "OWNS"                   # User owns Project, Project owns Task
    CONTAINS = "CONTAINS"           # Project contains Repository, Repository contains Branch
    BELONGS_TO = "BELONGS_TO"       # Branch belongs to Repository, Task belongs to Project
    DEPENDS_ON = "DEPENDS_ON"       # Service depends on Database, Task depends on Step
    RUNS = "RUNS"                   # Device runs Companion, Task runs Agent
    USES = "USES"                   # Agent uses Skill, Skill uses Tool, Project uses Service
    CONNECTED_TO = "CONNECTED_TO"   # Device connected to Kairo
    DEPLOYED_TO = "DEPLOYED_TO"     # Service deployed to Environment
    TRIGGERS = "TRIGGERS"           # Event triggers Workflow, Automation triggers Task
    PRODUCES = "PRODUCES"           # Task produces Document / Artifact
    OBSERVED_ON = "OBSERVED_ON"     # Service observed on Environment / Host
    SUPERSEDES = "SUPERSEDES"       # New Plan supersedes old Plan, new snapshot supersedes old


def generate_relationship_id(source_entity_id: str, target_entity_id: str, rel_type: RelationshipType | str) -> str:
    """Generate a deterministic ID for a relationship edge."""
    type_str = rel_type.value if isinstance(rel_type, RelationshipType) else str(rel_type).upper()
    seed = f"{source_entity_id}:{type_str}:{target_entity_id}".encode("utf-8")
    digest = hashlib.sha256(seed).hexdigest()[:16]
    return f"rel_{digest}"


class WorldRelationshipSchema(BaseModel):
    """Canonical edge model connecting two entities in the World Model graph (Spec 22)."""

    id: str = Field(description="Unique relationship edge identifier")
    source_entity_id: str = Field(description="Originating entity ID")
    target_entity_id: str = Field(description="Target entity ID")
    relationship_type: RelationshipType = Field(description="Strictly typed relationship name")
    owner_id: str = Field(description="Owner tenant identifier")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata annotations")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Edge creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class WorldRelationshipCreateRequest(BaseModel):
    """Payload to create or record a relationship edge."""

    source_entity_id: str
    target_entity_id: str
    relationship_type: RelationshipType
    metadata: dict[str, Any] = Field(default_factory=dict)
