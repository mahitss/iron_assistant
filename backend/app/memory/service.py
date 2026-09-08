"""High-level service orchestrating memory creation, sanitization, semantic retrieval, and ranking."""

import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.embeddings import EmbeddingProvider, get_configured_embedding_provider
from app.memory.repository import MemoryRepository
from app.memory.sanitizer import MemorySanitizer
from app.memory.schemas import (
    MemoryResponse,
    MemorySearchResult,
    MemoryType,
    MemoryUpdate,
)

logger = logging.getLogger("kairo.memory.service")


class MemoryService:
    """Service managing persistent long-term memories with semantic pgvector search."""

    def __init__(
        self,
        session: AsyncSession,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self.session = session
        self.repository = MemoryRepository(session)
        self.embedding_provider = embedding_provider or get_configured_embedding_provider()

    async def create_memory(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.FACT,
        importance: float = 0.5,
        source: str | None = "user_explicit",
    ) -> MemoryResponse:
        """Sanitize content, generate embedding vector, and save new long-term memory."""
        # 1. Sanitize content (rejects secrets/passwords/API keys)
        clean_content = MemorySanitizer.validate_and_sanitize(content, reject_on_secret=True)

        # 2. Generate embedding if provider is available
        embedding: list[float] | None = None
        if self.embedding_provider is not None:
            try:
                embedding = await self.embedding_provider.embed(clean_content)
            except Exception as exc:
                logger.warning("Failed to generate embedding for memory: %s", exc)

        # 3. Persist memory
        model_type_str = memory_type.value if isinstance(memory_type, MemoryType) else str(memory_type)
        memory = await self.repository.create(
            content=clean_content,
            memory_type=model_type_str,
            embedding=embedding,
            importance=importance,
            source=source,
        )
        return MemoryResponse.model_validate(memory)

    async def search_memories(
        self,
        query: str,
        top_k: int = 5,
        memory_type: MemoryType | None = None,
        min_score: float = 0.1,
    ) -> list[MemorySearchResult]:
        """Perform semantic search, rank by similarity + importance + recency, and return top matches."""
        if not self.embedding_provider:
            logger.debug("Embedding provider inactive; skipping semantic memory search.")
            return []

        try:
            query_embedding = await self.embedding_provider.embed(query)
        except Exception as exc:
            logger.warning("Failed to generate query embedding: %s", exc)
            return []

        type_str = memory_type.value if memory_type else None
        # Retrieve candidate matches via repository
        matches = await self.repository.search_similar(
            query_embedding=query_embedding,
            top_k=top_k * 2,  # Retrieve wider candidate window for composite re-ranking
            memory_type=type_str,
        )

        if not matches:
            return []

        now = datetime.now(UTC)
        ranked: list[MemorySearchResult] = []
        retrieved_ids: list[str] = []

        for mem, similarity in matches:
            # Deterministic, explainable ranking calculation:
            # Score = 70% semantic similarity + 20% importance + 10% recency
            updated_dt = mem.updated_at
            if updated_dt.tzinfo is None:
                updated_dt = updated_dt.replace(tzinfo=UTC)
            hours_old = max(0.0, (now - updated_dt).total_seconds() / 3600.0)
            recency_factor = max(0.0, 1.0 - (hours_old / 720.0))  # Decays over 30 days
            combined_score = (0.7 * similarity) + (0.2 * mem.importance) + (0.1 * recency_factor)

            if combined_score >= min_score:
                resp = MemoryResponse.model_validate(mem)
                ranked.append(
                    MemorySearchResult(
                        memory=resp,
                        similarity=round(similarity, 4),
                        score=round(combined_score, 4),
                    )
                )
                retrieved_ids.append(mem.id)

        # Sort descending by composite score and cap at top_k
        ranked.sort(key=lambda x: x.score, reverse=True)
        top_results = ranked[:top_k]

        # Update last_accessed_at timestamp asynchronously
        if retrieved_ids:
            try:
                await self.repository.update_last_accessed([r.memory.id for r in top_results])
            except Exception as exc:
                logger.warning("Failed to update last_accessed_at timestamps: %s", exc)

        return top_results

    async def get_memory(self, memory_id: str) -> MemoryResponse | None:
        """Fetch memory entry by UUID."""
        mem = await self.repository.get_by_id(memory_id)
        return MemoryResponse.model_validate(mem) if mem else None

    async def list_memories(
        self,
        memory_type: MemoryType | None = None,
        limit: int = 100,
    ) -> list[MemoryResponse]:
        """List stored memories."""
        type_str = memory_type.value if memory_type else None
        mems = await self.repository.list_all(memory_type=type_str, limit=limit)
        return [MemoryResponse.model_validate(m) for m in mems]

    async def update_memory(
        self,
        memory_id: str,
        update_data: MemoryUpdate,
    ) -> MemoryResponse | None:
        """Update an existing memory entry."""
        mem = await self.repository.get_by_id(memory_id)
        if mem is None:
            return None

        clean_content: str | None = None
        new_embedding: list[float] | None = None

        if update_data.content is not None:
            clean_content = MemorySanitizer.validate_and_sanitize(update_data.content)
            if self.embedding_provider:
                try:
                    new_embedding = await self.embedding_provider.embed(clean_content)
                except Exception as exc:
                    logger.warning("Failed to regenerate embedding on update: %s", exc)

        type_str = update_data.memory_type.value if update_data.memory_type else None
        updated = await self.repository.update(
            memory=mem,
            content=clean_content,
            embedding=new_embedding,
            importance=update_data.importance,
            memory_type=type_str,
        )
        return MemoryResponse.model_validate(updated)

    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory entry."""
        return await self.repository.delete(memory_id)

    @staticmethod
    def format_memories_for_context(memories: list[MemoryResponse]) -> str:
        """Format retrieved memories into a clean prompt section for LLM context."""
        if not memories:
            return ""
        lines = ["Relevant memories:"]
        for mem in memories:
            lines.append(f"- {mem.content}")
        return "\n".join(lines)
