"""ContextEngine: Central facade coordinating context resolution, ranking, user preferences, and cache."""

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.context.models import UserContextSettings
from app.context.project import ProjectService
from app.context.resolver import ContextResolver
from app.context.schemas import (
    ContextItem,
    ContextPacket,
    ContextSettings,
    ContextSettingsUpdate,
    ContextType,
)
from app.context.session import SessionContextManager
from app.memory.service import MemoryService

logger = logging.getLogger("kairo.context.engine")


class ContextEngine:
    """Authoritative Context Engine for Kairo personal assistant."""

    def __init__(
        self,
        redis_client: Any | None = None,
        session_manager: SessionContextManager | None = None,
        resolver: ContextResolver | None = None,
    ) -> None:
        self.settings = get_settings()
        self.redis = redis_client
        self.session_manager = session_manager or SessionContextManager(redis_client=redis_client)
        self.resolver = resolver or ContextResolver(
            session_manager=self.session_manager,
            max_context_items=self.settings.KAIRO_MAX_CONTEXT_ITEMS,
            max_memory_items=self.settings.KAIRO_MAX_MEMORY_ITEMS,
            max_project_items=self.settings.KAIRO_MAX_PROJECT_CONTEXT_ITEMS,
        )

    async def get_user_settings(
        self, user_id: str, db_session: AsyncSession | None = None
    ) -> ContextSettings:
        """Fetch user context settings with fallback defaults."""
        if db_session is not None:
            try:
                stmt = select(UserContextSettings).where(UserContextSettings.user_id == user_id)
                res = await db_session.execute(stmt)
                record = res.scalar_one_or_none()
                if record:
                    return ContextSettings.model_validate(record)
            except Exception as exc:
                logger.debug("Failed loading user context settings from DB: %s", exc)

        return ContextSettings(
            user_id=user_id,
            context_enabled=self.settings.KAIRO_CONTEXT_ENABLED,
            memory_enabled=self.settings.KAIRO_MEMORY_ENABLED,
            project_context_enabled=self.settings.KAIRO_PROJECT_CONTEXT_ENABLED,
            proactive_context_enabled=self.settings.KAIRO_PROACTIVE_CONTEXT_ENABLED,
            updated_at=datetime.now(UTC),
        )

    async def update_user_settings(
        self,
        user_id: str,
        updates: ContextSettingsUpdate,
        db_session: AsyncSession | None = None,
    ) -> ContextSettings:
        """Update and persist user context personalization settings."""
        if db_session is None:
            current = await self.get_user_settings(user_id)
            dump = updates.model_dump(exclude_unset=True)
            return current.model_copy(update=dump)

        stmt = select(UserContextSettings).where(UserContextSettings.user_id == user_id)
        res = await db_session.execute(stmt)
        record = res.scalar_one_or_none()

        if not record:
            record = UserContextSettings(
                user_id=user_id,
                context_enabled=self.settings.KAIRO_CONTEXT_ENABLED,
                memory_enabled=self.settings.KAIRO_MEMORY_ENABLED,
                project_context_enabled=self.settings.KAIRO_PROJECT_CONTEXT_ENABLED,
                proactive_context_enabled=self.settings.KAIRO_PROACTIVE_CONTEXT_ENABLED,
                updated_at=datetime.now(UTC),
            )
            db_session.add(record)

        dump = updates.model_dump(exclude_unset=True)
        for key, val in dump.items():
            if hasattr(record, key) and val is not None:
                setattr(record, key, val)

        record.updated_at = datetime.now(UTC)
        await db_session.commit()
        await db_session.refresh(record)

        # Invalidate any cached settings
        if self.redis:
            try:
                await self.redis.delete(f"kairo:context:settings:{user_id}")
            except Exception:
                pass

        return ContextSettings.model_validate(record)

    async def resolve_context(
        self,
        user_id: str,
        message: str,
        session_id: str | None = None,
        db_session: AsyncSession | None = None,
        memory_service: MemoryService | None = None,
    ) -> ContextPacket:
        """Generate bounded ContextPacket for the given user turn."""
        # 1. Check user personalization toggles
        settings = await self.get_user_settings(user_id=user_id, db_session=db_session)
        if not settings.context_enabled:
            return ContextPacket(session_id=session_id, user_id=user_id)

        # 2. Resolve context using ContextResolver
        packet = await self.resolver.resolve(
            user_id=user_id,
            message=message,
            session_id=session_id,
            db_session=db_session,
            memory_service=memory_service if settings.memory_enabled else None,
        )

        # 3. Filter disabled category items
        if not settings.project_context_enabled:
            packet.project_context = []
            packet.developer_context = []
            packet.active_project = None
        if not settings.proactive_context_enabled:
            packet.proactive_context = []

        # Recompute items list based on active categories
        active_items: list[ContextItem] = []
        active_items.extend(packet.session_context)
        active_items.extend(packet.project_context)
        active_items.extend(packet.conversation_context)
        active_items.extend(packet.memory_context)
        active_items.extend(packet.workflow_context)
        active_items.extend(packet.developer_context)
        active_items.extend(packet.proactive_context)

        packet.items = active_items
        packet.total_items = len(active_items)
        return packet

    async def get_project_context(
        self,
        user_id: str,
        project_id: str,
        db_session: AsyncSession | None = None,
    ) -> ContextPacket:
        """Fetch all contextual elements linked specifically to a given project."""
        if db_session is None:
            return ContextPacket(user_id=user_id)

        proj_service = ProjectService(db_session)
        project = await proj_service.get_project(user_id=user_id, project_id=project_id)
        if not project:
            return ContextPacket(user_id=user_id)

        items: list[ContextItem] = [
            ContextItem(
                source_type=ContextType.PROJECT_CONTEXT,
                source_id=project.id,
                title=f"Project {project.name}",
                content=project.description or f"Project status is {project.status.value}",
                relevance_score=1.0,
                confidence=1.0,
                reason="Direct project inquiry.",
            )
        ]
        for repo in project.repositories:
            items.append(
                ContextItem(
                    source_type=ContextType.DEVELOPER_CONTEXT,
                    source_id=f"repo_{repo}",
                    title="Linked Repository",
                    content=repo,
                    relevance_score=0.9,
                    confidence=1.0,
                    reason=f"Repository attached to project '{project.name}'.",
                )
            )

        return ContextPacket(
            user_id=user_id,
            active_project=project,
            items=items,
            project_context=items,
            total_items=len(items),
        )

    async def search_context(
        self,
        user_id: str,
        query: str,
        db_session: AsyncSession | None = None,
        memory_service: MemoryService | None = None,
    ) -> list[ContextItem]:
        """Perform hybrid search over both structured project data and long-term memory."""
        packet = await self.resolve_context(
            user_id=user_id,
            message=query,
            db_session=db_session,
            memory_service=memory_service,
        )
        return packet.items
