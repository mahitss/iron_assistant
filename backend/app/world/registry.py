"""Source-of-truth registry and authority hierarchy for Kairo World Model (Task 32, Spec 32, 33)."""

from enum import Enum
import logging
from typing import Dict, Optional, Tuple

from app.world.entities import EntityType

logger = logging.getLogger("kairo.world.registry")


class SourceAuthority(str, Enum):
    """Authority priority levels for resolving state updates (Spec 33)."""

    AUTHORITATIVE_SYSTEM = "AUTHORITATIVE_SYSTEM"  # Primary source of truth (e.g. GitHub API, SecurityCenter)
    VERIFIED_EVENT = "VERIFIED_EVENT"              # Signed/trusted Event Bus event from producer
    DERIVED_INFERENCE = "DERIVED_INFERENCE"        # Inferred from correlated events
    UNTRUSTED_EXTERNAL = "UNTRUSTED_EXTERNAL"      # External file text, user suggestion, or model hallucination


# Authority ranking numeric score (Higher strictly beats lower)
AUTHORITY_SCORE: dict[SourceAuthority, int] = {
    SourceAuthority.AUTHORITATIVE_SYSTEM: 100,
    SourceAuthority.VERIFIED_EVENT: 80,
    SourceAuthority.DERIVED_INFERENCE: 50,
    SourceAuthority.UNTRUSTED_EXTERNAL: 10,
}


class SourceOfTruthRegistry:
    """Authoritative catalog mapping entity domain fields to their true owner systems (Spec 32)."""

    # Mapping of (EntityType, field_name) -> authoritative source identifier
    AUTHORITATIVE_SOURCES: dict[Tuple[EntityType, str], str] = {
        (EntityType.DEVICE, "state"): "local_companion",
        (EntityType.DEVICE, "capabilities"): "security_center",
        (EntityType.REPOSITORY, "state"): "github",
        (EntityType.REPOSITORY, "head_revision"): "github",
        (EntityType.REPOSITORY, "ci_status"): "github",
        (EntityType.TASK, "state"): "task_engine",
        (EntityType.TASK, "step"): "task_engine",
        (EntityType.WORKFLOW, "state"): "automation",
        (EntityType.SERVICE, "state"): "observability",
        (EntityType.ENVIRONMENT, "state"): "infrastructure",
        (EntityType.MODEL, "state"): "model_router",
        (EntityType.PROVIDER, "state"): "model_router",
        (EntityType.PROJECT, "state"): "projects",
        (EntityType.KNOWLEDGE_NODE, "state"): "knowledge_fabric",
    }

    @classmethod
    def get_authoritative_source(cls, entity_type: EntityType | str, field_name: str = "state") -> str:
        """Return the authoritative source system for an entity field."""
        try:
            et = EntityType(entity_type) if isinstance(entity_type, str) else entity_type
            return cls.AUTHORITATIVE_SOURCES.get((et, field_name), "system")
        except ValueError:
            return "system"

    @classmethod
    def is_source_authoritative(
        cls,
        entity_type: EntityType | str,
        source: str,
        field_name: str = "state",
    ) -> bool:
        """Check whether a given source is the authoritative owner of the entity field."""
        expected = cls.get_authoritative_source(entity_type, field_name)
        return source.lower().strip() == expected.lower().strip()

    @classmethod
    def should_update(
        cls,
        current_authority: SourceAuthority,
        new_authority: SourceAuthority,
        is_same_source: bool = False,
    ) -> bool:
        """Determine whether an update has sufficient authority to overwrite existing state (Spec 33)."""
        # If same source, update is allowed if not stale/older version
        if is_same_source:
            return True

        current_score = AUTHORITY_SCORE.get(current_authority, 0)
        new_score = AUTHORITY_SCORE.get(new_authority, 0)

        # Authoritative sources strictly win; lower authority can NEVER overwrite higher authority
        return new_score >= current_score
