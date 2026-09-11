"""UniversalContextCache: Safe scoped caching with tenant isolation and invalidation (Task 69)."""

import hashlib
import logging
from datetime import UTC, datetime, timedelta

from app.context.universal_schemas import ContextPackage

logger = logging.getLogger("kairo.context.cache")


class UniversalContextCache:
    """Safe context package caching with strict tenant boundaries and source-based invalidation."""

    def __init__(self, default_ttl_seconds: int = 300) -> None:
        self.default_ttl = timedelta(seconds=default_ttl_seconds)
        # Store tuple: (ContextPackage, expiration_datetime, tenant_id, user_id, source_ids)
        self._cache: dict[str, tuple[ContextPackage, datetime, str, str, set[str]]] = {}

    def _generate_key(
        self,
        tenant_id: str,
        user_id: str,
        session_id: str | None,
        task_id: str | None,
        agent_id: str | None,
        environment: str,
        query: str,
        version: str = "v1",
    ) -> str:
        q_hash = hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()[:16]
        return f"{tenant_id}:{user_id}:{session_id or '_'}:{task_id or '_'}:{agent_id or '_'}:{environment}:{q_hash}:{version}"

    def get(
        self,
        tenant_id: str,
        user_id: str,
        session_id: str | None,
        task_id: str | None,
        agent_id: str | None,
        environment: str,
        query: str,
        version: str = "v1",
    ) -> ContextPackage | None:
        """Fetch cached ContextPackage enforcing tenant isolation and TTL."""
        key = self._generate_key(
            tenant_id, user_id, session_id, task_id, agent_id, environment, query, version
        )
        entry = self._cache.get(key)
        if not entry:
            return None

        pkg, expires_at, c_tenant, c_user, _ = entry
        # Strict scope verification
        if c_tenant != tenant_id or c_user != user_id:
            logger.warning("Blocked cross-tenant/user context cache access attempt on key '%s'", key)
            return None

        if datetime.now(UTC) > expires_at:
            del self._cache[key]
            return None

        return pkg

    def set(
        self,
        package: ContextPackage,
        session_id: str | None = None,
        task_id: str | None = None,
        agent_id: str | None = None,
        query: str = "",
        ttl_seconds: int | None = None,
    ) -> None:
        """Cache assembled ContextPackage with source ID indexing for fine-grained invalidation."""
        ttl = timedelta(seconds=ttl_seconds) if ttl_seconds else self.default_ttl
        now = datetime.now(UTC)
        expires_at = now + ttl

        key = self._generate_key(
            package.tenant_id,
            package.user_id,
            session_id,
            task_id,
            agent_id,
            package.environment,
            query or package.task or "",
        )

        source_ids = {it.source_id for it in package.items}
        self._cache[key] = (package, expires_at, package.tenant_id, package.user_id, source_ids)

    def invalidate_for_source(self, source_id: str) -> int:
        """Invalidate all cached packages that contain a specific modified or deleted source ID."""
        keys_to_remove = [k for k, (_, _, _, _, sources) in self._cache.items() if source_id in sources]
        for k in keys_to_remove:
            del self._cache[k]
        return len(keys_to_remove)

    def invalidate_for_tenant(self, tenant_id: str) -> int:
        """Invalidate all cached context for an entire tenant."""
        keys_to_remove = [k for k, (_, _, c_tenant, _, _) in self._cache.items() if c_tenant == tenant_id]
        for k in keys_to_remove:
            del self._cache[k]
        return len(keys_to_remove)

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
