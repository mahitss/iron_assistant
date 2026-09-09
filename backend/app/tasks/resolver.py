"""Task context resolution and external state freshness verification (Spec 52, 53, 54, 55)."""

import logging
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.context.resolver import ContextResolver
from app.knowledge.service import KnowledgeFabricService

logger = logging.getLogger("kairo.tasks.resolver")


class TaskContextResolver:
    """Retrieves and refreshes bounded context, knowledge, memory, and external state for tasks."""

    def __init__(
        self,
        context_resolver: ContextResolver | None = None,
        knowledge_service: KnowledgeFabricService | None = None,
    ) -> None:
        self.context_resolver = context_resolver or ContextResolver()
        self.knowledge_service = knowledge_service

    async def resolve_initial_context(
        self,
        user_id: str,
        project_id: str | None,
        objective: str,
        session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Resolve bounded context for initial task planning (Spec 52)."""
        context_packet: dict[str, Any] = {
            "objective": objective,
            "project_id": project_id,
            "knowledge_items": [],
            "memories": [],
            "project_summary": "",
        }

        try:
            if self.context_resolver:
                resolved = await self.context_resolver.resolve(
                    user_id=user_id,
                    message=objective,
                    db_session=session,
                )
                if resolved:
                    context_packet["memories"] = getattr(resolved, "relevant_memories", [])[:3]
                    context_packet["project_summary"] = getattr(resolved, "project_context", "")
        except Exception as e:
            logger.warning("Error resolving initial context for task: %s", e)

        # Knowledge search
        try:
            if self.knowledge_service and project_id:
                items = await self.knowledge_service.search_knowledge(
                    query=objective,
                    project_id=project_id,
                    session=session,
                    limit=3,
                )
                context_packet["knowledge_items"] = [
                    {"id": item.id, "title": item.title, "summary": item.summary}
                    for item in items
                ]
        except Exception as e:
            logger.warning("Error querying knowledge fabric for task: %s", e)

        # World Model context integration (Task 32, Spec 46, 75)
        try:
            from app.world.model import get_world_model
            wm = get_world_model()
            world_packet = await wm.build_context_packet(user_id=user_id, project_id=project_id)
            context_packet["world_context"] = world_packet.model_dump()
        except Exception as e:
            logger.debug("World model context lookup skipped: %s", e)

        return context_packet

    async def verify_external_state_freshness(
        self,
        target_resource: dict[str, Any],
        recorded_state: dict[str, Any] | None,
    ) -> bool:
        """Verify that external resource state has not changed unexpectedly (Spec 54, 55).

        Returns:
            True if state is fresh and plan remains valid; False if stale (triggers replan).
        """
        if not recorded_state:
            return True

        # Example: check git branch or HEAD commit hash
        current_commit = target_resource.get("commit_sha")
        recorded_commit = recorded_state.get("commit_sha")
        if current_commit and recorded_commit and current_commit != recorded_commit:
            logger.warning("External git commit changed from %s to %s", recorded_commit, current_commit)
            return False

        return True
