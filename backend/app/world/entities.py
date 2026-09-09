"""Entity contracts, schemas, and types for Kairo World Model (Task 32, Spec 2-21)."""

from datetime import UTC, datetime
from enum import Enum
import hashlib
from typing import Any, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class EntityType(str, Enum):
    """Authorized domain entity types modeled in the Kairo World Model (Spec 3)."""

    USER = "USER"
    PROJECT = "PROJECT"
    REPOSITORY = "REPOSITORY"
    BRANCH = "BRANCH"
    WORKFLOW = "WORKFLOW"
    TASK = "TASK"
    AGENT = "AGENT"
    SKILL = "SKILL"
    TOOL = "TOOL"
    DEVICE = "DEVICE"
    SERVICE = "SERVICE"
    ENVIRONMENT = "ENVIRONMENT"
    DOCUMENT = "DOCUMENT"
    KNOWLEDGE_NODE = "KNOWLEDGE_NODE"
    AUTOMATION = "AUTOMATION"
    NOTIFICATION = "NOTIFICATION"
    MODEL = "MODEL"
    PROVIDER = "PROVIDER"


class ObservationType(str, Enum):
    """Epistemic classification of an observation (Spec 27, 45)."""

    OBSERVED = "OBSERVED"   # Directly witnessed from authoritative source API or verified event
    INFERRED = "INFERRED"   # Derived logically from associated signals
    EXPECTED = "EXPECTED"   # Anticipated state before observation confirmation
    UNKNOWN = "UNKNOWN"     # Unobserved or unverified state (default for unverified entities)


class ConfidenceLevel(str, Enum):
    """Confidence level of an observation (Spec 28)."""

    HIGH = "HIGH"      # Authoritative source API or verified cryptographic payload
    MEDIUM = "MEDIUM"  # Derived inference from related domain signals
    LOW = "LOW"        # Heuristic or speculative estimation


def generate_entity_id(entity_type: EntityType | str, owner_id: str, source: str, source_id: str) -> str:
    """Generate a deterministic, collision-safe internal ID for an entity (Spec 4)."""
    type_str = entity_type.value if isinstance(entity_type, EntityType) else str(entity_type).upper()
    seed = f"{owner_id}:{type_str}:{source}:{source_id}".encode("utf-8")
    digest = hashlib.sha256(seed).hexdigest()[:16]
    return f"ent_{type_str.lower()}_{digest}"


class WorldEntitySchema(BaseModel):
    """Canonical representation of an authorized entity in the World Model (Spec 2)."""

    id: str = Field(description="Stable internal entity identifier")
    type: EntityType = Field(description="Domain entity classification")
    name: str = Field(description="Human-readable entity name")
    owner_id: str = Field(description="Owner user identifier (tenant boundary)")
    project_id: Optional[str] = Field(default=None, description="Optional associated project ID")
    source: str = Field(description="Authoritative source system")
    source_id: str = Field(description="External identifier in source system")
    state: str = Field(description="Structured state code")
    state_version: Optional[int] = Field(default=None, description="Monotonic version for stale detection")
    observation_type: ObservationType = Field(default=ObservationType.OBSERVED, description="Epistemic status")
    confidence: ConfidenceLevel = Field(default=ConfidenceLevel.HIGH, description="Confidence grade")
    observed_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Observation timestamp")
    expires_at: Optional[datetime] = Field(default=None, description="Freshness expiration timestamp")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Sanitized entity attributes")
    is_stale: bool = Field(default=False, description="Whether entity has exceeded its freshness policy")

    model_config = ConfigDict(from_attributes=True)


class WorldEntityCreateRequest(BaseModel):
    """Payload for declaring or observing an entity."""

    type: EntityType
    name: str
    project_id: Optional[str] = None
    source: str
    source_id: str
    state: str
    state_version: Optional[int] = None
    observation_type: ObservationType = ObservationType.OBSERVED
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH
    metadata: dict[str, Any] = Field(default_factory=dict)
    ttl_seconds: Optional[int] = None
