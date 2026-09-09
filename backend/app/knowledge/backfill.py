"""Idempotent backfill service synchronizing existing Memories, Projects, and Workflows into Knowledge Fabric."""

import logging

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.automation.models import Workflow
from app.context.models import Project
from app.knowledge.models import KnowledgeEdgeModel, KnowledgeNodeModel, KnowledgeSourceModel
from app.knowledge.schemas import KnowledgeRelationType, KnowledgeSourceType, KnowledgeType
from app.memory.embeddings import DeterministicEmbeddingProvider, EmbeddingProvider
from app.memory.models import Memory

logger = logging.getLogger("kairo.knowledge.backfill")


class KnowledgeBackfillService:
    """Safely and idempotently backfills existing database records into the Knowledge Fabric."""

    def __init__(self, embedding_provider: EmbeddingProvider | None = None) -> None:
        self.embedding_provider = embedding_provider or DeterministicEmbeddingProvider()

    async def backfill_all(self, session: AsyncSession, user_id: str) -> dict[str, int]:
        """Backfill all existing memories, projects, and workflows for user."""
        projects_count = await self.backfill_projects(session, user_id)
        memories_count = await self.backfill_memories(session, user_id)
        workflows_count = await self.backfill_workflows(session, user_id)

        await session.commit()
        return {
            "projects_indexed": projects_count,
            "memories_indexed": memories_count,
            "workflows_indexed": workflows_count,
            "total_indexed": projects_count + memories_count + workflows_count,
        }

    async def backfill_projects(self, session: AsyncSession, user_id: str) -> int:
        """Backfill projects into KnowledgeNodeModel of type PROJECT."""
        stmt = select(Project).where(Project.user_id == user_id)
        res = await session.execute(stmt)
        projects = list(res.scalars().all())

        indexed = 0
        for p in projects:
            # Check if node already exists for this source_id
            existing = await self._find_node_by_source(session, user_id, p.id)
            if existing:
                continue

            summary = p.description or f"User Project: {p.name}"
            emb = await self.embedding_provider.embed(f"{p.name} {summary}")

            node = KnowledgeNodeModel(
                user_id=user_id,
                type=KnowledgeType.PROJECT.value,
                source_id=p.id,
                project_id=p.id,
                title=p.name,
                summary=summary,
                embedding=emb,
                status="ACTIVE",
                confidence=1.0,
                created_at=p.created_at,
                node_metadata={"status": p.status},
            )
            session.add(node)

            source = KnowledgeSourceModel(
                user_id=user_id,
                source_type=KnowledgeSourceType.USER_EXPLICIT.value,
                source_id=p.id,
                title=p.name,
                project_id=p.id,
                confidence=1.0,
                created_at=p.created_at,
            )
            session.add(source)
            indexed += 1

        return indexed

    async def backfill_memories(self, session: AsyncSession, user_id: str) -> int:
        """Backfill memories into KnowledgeNodeModel of type MEMORY and link to projects."""
        stmt = select(Memory).where(Memory.user_id == user_id)
        res = await session.execute(stmt)
        memories = list(res.scalars().all())

        indexed = 0
        for m in memories:
            existing = await self._find_node_by_source(session, user_id, m.id)
            if existing:
                continue

            title = f"Memory: {m.content[:60]}..." if len(m.content) > 60 else f"Memory: {m.content}"
            emb = await self.embedding_provider.embed(m.content)

            node = KnowledgeNodeModel(
                user_id=user_id,
                type=KnowledgeType.MEMORY.value,
                source_id=m.id,
                project_id=m.project_id,
                title=title,
                summary=m.content,
                embedding=emb,
                status="ACTIVE",
                confidence=m.confidence,
                created_at=m.created_at,
                node_metadata={"memory_type": m.memory_type, "scope": m.scope},
            )
            session.add(node)
            await session.flush()

            source = KnowledgeSourceModel(
                user_id=user_id,
                source_type=KnowledgeSourceType.USER_EXPLICIT.value
                if m.source == "user_explicit"
                else KnowledgeSourceType.SYSTEM_DERIVED.value,
                source_id=m.id,
                title=title,
                project_id=m.project_id,
                confidence=m.confidence,
                created_at=m.created_at,
            )
            session.add(source)

            # If linked to a project, create BELONGS_TO relationship edge to the project node
            if m.project_id:
                proj_node = await self._find_node_by_source(session, user_id, m.project_id)
                if proj_node:
                    edge = KnowledgeEdgeModel(
                        user_id=user_id,
                        source_node_id=node.id,
                        target_node_id=proj_node.id,
                        relation_type=KnowledgeRelationType.BELONGS_TO.value,
                        confidence=1.0,
                        source="BACKFILL",
                    )
                    session.add(edge)

            indexed += 1

        return indexed

    async def backfill_workflows(self, session: AsyncSession, user_id: str) -> int:
        """Backfill automation workflows into KnowledgeNodeModel of type WORKFLOW."""
        stmt = select(Workflow).where(Workflow.user_id == user_id)
        res = await session.execute(stmt)
        workflows = list(res.scalars().all())

        indexed = 0
        for w in workflows:
            existing = await self._find_node_by_source(session, user_id, w.id)
            if existing:
                continue

            summary = w.description or f"Workflow automation: {w.name} ({w.trigger_type})"
            emb = await self.embedding_provider.embed(f"{w.name} {summary}")

            node = KnowledgeNodeModel(
                user_id=user_id,
                type=KnowledgeType.WORKFLOW.value,
                source_id=w.id,
                title=w.name,
                summary=summary,
                embedding=emb,
                status="ACTIVE",
                confidence=1.0,
                created_at=w.created_at,
                node_metadata={"trigger_type": w.trigger_type, "is_enabled": w.enabled},
            )
            session.add(node)

            source = KnowledgeSourceModel(
                user_id=user_id,
                source_type=KnowledgeSourceType.SYSTEM_DERIVED.value,
                source_id=w.id,
                title=w.name,
                confidence=1.0,
                created_at=w.created_at,
            )
            session.add(source)
            indexed += 1

        return indexed

    async def _find_node_by_source(
        self, session: AsyncSession, user_id: str, source_id: str
    ) -> KnowledgeNodeModel | None:
        stmt = select(KnowledgeNodeModel).where(
            and_(
                KnowledgeNodeModel.user_id == user_id,
                KnowledgeNodeModel.source_id == source_id,
            )
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()
