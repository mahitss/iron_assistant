"""Cache invalidation and deletion propagation coordinator (Task 39, Spec 53, 167-168)."""

import logging
from typing import Any

from app.state.cache import ScopedStateCache, scoped_cache

logger = logging.getLogger("kairo.state.invalidation")


class CacheInvalidator:
    """Coordinates cache purging on state mutations and deletion propagation."""

    def __init__(self, cache: ScopedStateCache = scoped_cache) -> None:
        self.cache = cache

    def on_state_updated(
        self,
        domain: str,
        resource_id: str,
        user_id: str | None = None,
        project_id: str | None = None,
    ) -> None:
        """Invalidates cache when an authoritative record is modified."""
        # 1. Invalidate precise scoped key
        exact_key = self.cache.build_scoped_key(domain, resource_id, user_id, project_id)
        self.cache.invalidate(exact_key)

        # 2. Invalidate un-scoped or wildcard entries for this resource
        prefix = f"{domain}:{resource_id}"
        count = self.cache.invalidate_prefix(prefix)
        logger.debug("Invalidated %d cache entries for prefix '%s'", count, prefix)

    def on_resource_deleted(
        self,
        domain: str,
        resource_id: str,
        user_id: str | None = None,
        project_id: str | None = None,
    ) -> None:
        """Purges cached state on deletion to prevent resurrecting deleted objects."""
        self.on_state_updated(domain, resource_id, user_id, project_id)
        logger.info("Deletion propagation: cache purged for %s:%s", domain, resource_id)


# Global invalidator instance
cache_invalidator = CacheInvalidator()
