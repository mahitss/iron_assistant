"""Federated knowledge retriever bridging Memory, Projects, World Model, Event Bus, and Web."""

import hashlib
import logging
from typing import Any

from app.knowledge.schemas import (
    ChunkContentType,
    ChunkMetadata,
    DocumentChunk,
    FreshnessState,
    RAGSourceType,
    TrustTier,
)

logger = logging.getLogger("kairo.knowledge.cross_boundary")


class FederatedKnowledgeBridge:
    """Queries sibling subsystems across Kairo and standardizes their responses into knowledge chunks."""

    def __init__(
        self,
        memory_service: Any | None = None,
        project_service: Any | None = None,
        world_model: Any | None = None,
        event_bus: Any | None = None,
    ) -> None:
        self.memory_service = memory_service
        self.project_service = project_service
        self.world_model = world_model
        self.event_bus = event_bus

    async def fetch_memory_chunks(self, query: str, user_id: str, limit: int = 5) -> list[DocumentChunk]:
        """Fetch relevant episodic and semantic memories."""
        chunks: list[DocumentChunk] = []
        if not self.memory_service:
            return chunks

        try:
            # MemoryService might have search, recall, or search_memories
            memories = []
            if hasattr(self.memory_service, "search_memories"):
                res = await self.memory_service.search_memories(query=query, user_id=user_id, limit=limit)
                memories = res if isinstance(res, list) else []
            elif hasattr(self.memory_service, "recall"):
                res = await self.memory_service.recall(query=query, user_id=user_id, limit=limit)
                memories = res if isinstance(res, list) else []

            for idx, mem in enumerate(memories):
                content = mem.get("content") or mem.get("text") or str(mem)
                m_id = str(mem.get("id", f"mem_{idx}"))
                content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

                meta = ChunkMetadata(
                    chunk_id=f"mem_chunk_{m_id}",
                    document_id=f"memory_{m_id}",
                    section="Episodic Memory",
                    headings=["User Memory", mem.get("type", "episodic")],
                    content_type=ChunkContentType.PROSE,
                    user_id=user_id,
                    source_type=RAGSourceType.MEMORY,
                    trust_tier=TrustTier.SYSTEM_VERIFIED,
                    freshness=FreshnessState.FRESH,
                )
                chunks.append(DocumentChunk(id=f"mem_chunk_{m_id}", content=content, metadata=meta, content_hash=content_hash))
        except Exception as exc:
            logger.warning("Federated query to MemoryService failed: %s", exc)

        return chunks

    async def fetch_project_chunks(self, query: str, project_id: str, limit: int = 5) -> list[DocumentChunk]:
        """Fetch project documentation, task descriptions, and sprint goals."""
        chunks: list[DocumentChunk] = []
        if not self.project_service or not project_id:
            return chunks

        try:
            items = []
            if hasattr(self.project_service, "search_project_context"):
                items = await self.project_service.search_project_context(project_id=project_id, query=query, limit=limit)

            for idx, item in enumerate(items):
                content = item.get("content") or str(item)
                item_id = str(item.get("id", f"proj_{idx}"))
                content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

                meta = ChunkMetadata(
                    chunk_id=f"proj_chunk_{item_id}",
                    document_id=f"proj_doc_{item_id}",
                    section=item.get("title", "Project Artifact"),
                    headings=["Project Context", item.get("category", "General")],
                    content_type=ChunkContentType.PROSE,
                    project_id=project_id,
                    source_type=RAGSourceType.PROJECT_ARTIFACT,
                    trust_tier=TrustTier.PROJECT_DOC,
                    freshness=FreshnessState.FRESH,
                )
                chunks.append(DocumentChunk(id=f"proj_chunk_{item_id}", content=content, metadata=meta, content_hash=content_hash))
        except Exception as exc:
            logger.warning("Federated query to ProjectService failed: %s", exc)

        return chunks

    async def fetch_world_model_chunks(self, query: str) -> list[DocumentChunk]:
        """Fetch current world model state, connected device status, and environment variables."""
        chunks: list[DocumentChunk] = []
        if not self.world_model:
            return chunks

        try:
            state = {}
            if hasattr(self.world_model, "get_environment_state"):
                state = await self.world_model.get_environment_state()
            elif hasattr(self.world_model, "get_state"):
                state = await self.world_model.get_state()

            if state:
                content = f"Active Environment Entities and State:\n{state}"
                content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
                meta = ChunkMetadata(
                    chunk_id="wm_env_state_0",
                    document_id="world_model_state",
                    section="World State Snapshot",
                    headings=["World Model", "Environment Snapshot"],
                    content_type=ChunkContentType.DATA_TABLE,
                    source_type=RAGSourceType.WORLD_MODEL,
                    trust_tier=TrustTier.SYSTEM_VERIFIED,
                    freshness=FreshnessState.FRESH,
                )
                chunks.append(DocumentChunk(id="wm_env_state_0", content=content, metadata=meta, content_hash=content_hash))
        except Exception as exc:
            logger.warning("Federated query to WorldModel failed: %s", exc)

        return chunks
