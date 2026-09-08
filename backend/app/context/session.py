"""Ephemeral session-level context manager tracking short-lived conversation continuity and task state."""

import json
import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("kairo.context.session")


class SessionContextManager:
    """Manages short-lived context (active topic, recent tool outcomes, pending tasks) per chat session."""

    def __init__(self, redis_client: Any | None = None, ttl_seconds: int = 3600) -> None:
        self.redis = redis_client
        self.ttl = ttl_seconds
        # In-memory local fallback store
        self._local_cache: dict[str, dict[str, Any]] = {}

    def _get_key(self, session_id: str) -> str:
        return f"kairo:context:session:{session_id}"

    async def get_session_context(self, session_id: str) -> dict[str, Any]:
        """Retrieve current session context dictionary."""
        if not session_id:
            return {}

        if self.redis is not None:
            try:
                raw = await self.redis.get(self._get_key(session_id))
                if raw:
                    return json.loads(raw)
            except Exception as exc:
                logger.debug("Redis session context lookup error: %s", exc)

        return self._local_cache.get(session_id, {})

    async def update_session_context(self, session_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Merge updates into current session context."""
        if not session_id:
            return {}

        current = await self.get_session_context(session_id)
        current.update(updates)
        current["last_activity_at"] = datetime.now(UTC).isoformat()

        if self.redis is not None:
            try:
                await self.redis.setex(
                    self._get_key(session_id),
                    self.ttl,
                    json.dumps(current),
                )
            except Exception as exc:
                logger.debug("Redis session context write error: %s", exc)

        self._local_cache[session_id] = current
        return current

    async def set_active_project(self, session_id: str, project_id: str) -> None:
        """Bind session to a specific active project."""
        await self.update_session_context(session_id, {"active_project_id": project_id})

    async def record_tool_outcome(
        self,
        session_id: str,
        tool_name: str,
        status: str,
        summary: str | None = None,
    ) -> None:
        """Record outcome of recent tool execution in session memory."""
        ctx = await self.get_session_context(session_id)
        outcomes = ctx.get("recent_tool_outcomes", [])
        outcomes.append(
            {
                "tool": tool_name,
                "status": status,
                "summary": summary or "",
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )
        # Keep only the last 5 tool outcomes to preserve context budget
        outcomes = outcomes[-5:]
        await self.update_session_context(session_id, {"recent_tool_outcomes": outcomes})

    async def clear_session_context(self, session_id: str) -> None:
        """Flush ephemeral session context."""
        if self.redis is not None:
            try:
                await self.redis.delete(self._get_key(session_id))
            except Exception as exc:
                logger.debug("Redis session context delete error: %s", exc)
        self._local_cache.pop(session_id, None)
