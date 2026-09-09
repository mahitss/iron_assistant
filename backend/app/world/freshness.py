"""Freshness policies, TTL matrix, and staleness evaluation for Kairo World Model (Task 32, Spec 29-31, 62)."""

from datetime import UTC, datetime, timedelta
import logging
from typing import Dict, Optional, Tuple

from app.world.entities import EntityType

logger = logging.getLogger("kairo.world.freshness")


class FreshnessPolicy:
    """Configures and evaluates freshness thresholds per entity type (Spec 31)."""

    # Default TTL in seconds per entity type
    DEFAULT_TTL_SECONDS: dict[EntityType, int] = {
        EntityType.DEVICE: 60,             # 1 minute (high churn heartbeat)
        EntityType.SERVICE: 120,           # 2 minutes (health checks)
        EntityType.TASK: 300,              # 5 minutes (execution operational status)
        EntityType.WORKFLOW: 300,          # 5 minutes
        EntityType.REPOSITORY: 600,        # 10 minutes (git sync)
        EntityType.BRANCH: 600,            # 10 minutes
        EntityType.MODEL: 600,             # 10 minutes
        EntityType.PROVIDER: 600,          # 10 minutes
        EntityType.PROJECT: 3600,          # 1 hour (metadata)
        EntityType.ENVIRONMENT: 3600,      # 1 hour
        EntityType.DOCUMENT: 86400,        # 24 hours
        EntityType.KNOWLEDGE_NODE: 86400,  # 24 hours
    }

    FALLBACK_TTL_SECONDS: int = 600

    @classmethod
    def get_default_ttl(cls, entity_type: EntityType | str) -> int:
        """Retrieve default freshness duration for entity type."""
        try:
            et = EntityType(entity_type) if isinstance(entity_type, str) else entity_type
            return cls.DEFAULT_TTL_SECONDS.get(et, cls.FALLBACK_TTL_SECONDS)
        except ValueError:
            return cls.FALLBACK_TTL_SECONDS

    @classmethod
    def compute_expiration(
        cls,
        entity_type: EntityType | str,
        observed_at: datetime | None = None,
        custom_ttl_seconds: int | None = None,
    ) -> datetime:
        """Compute expiration timestamp based on observation time and TTL."""
        base_time = observed_at or datetime.now(UTC)
        ttl = custom_ttl_seconds if custom_ttl_seconds is not None else cls.get_default_ttl(entity_type)
        return base_time + timedelta(seconds=ttl)

    @classmethod
    def is_stale(
        cls,
        observed_at: datetime,
        expires_at: datetime | None = None,
        entity_type: EntityType | str | None = None,
        now: datetime | None = None,
    ) -> bool:
        """Determine if an entity observation is stale (Spec 30)."""
        current_time = now or datetime.now(UTC)

        # 1. If explicit expiration set, check against it
        if expires_at is not None:
            return current_time > expires_at

        # 2. Otherwise compute default TTL if entity_type provided
        if entity_type is not None:
            ttl = cls.get_default_ttl(entity_type)
            return current_time > (observed_at + timedelta(seconds=ttl))

        # 3. Fallback default
        return current_time > (observed_at + timedelta(seconds=cls.FALLBACK_TTL_SECONDS))

    @classmethod
    def calculate_age_seconds(cls, observed_at: datetime, now: datetime | None = None) -> float:
        """Return elapsed seconds since the entity was observed."""
        current_time = now or datetime.now(UTC)
        diff = (current_time - observed_at).total_seconds()
        return max(0.0, diff)
