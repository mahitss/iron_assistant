"""Database repository for conversations, messages, and long-term vector memories."""

import math
import uuid
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.models import Conversation, Memory, Message, utc_now


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Calculate cosine similarity between two float vectors in Python."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm1 * norm2)))


class ConversationRepository:
    """Repository handling conversation session threads and message histories."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create(self, session_id: str | None = None) -> Conversation:
        """Retrieve an existing conversation by session_id or create a new one."""
        sid = (session_id or f"sess_{uuid.uuid4().hex[:12]}").strip()

        stmt = select(Conversation).where(Conversation.session_id == sid)
        result = await self.session.execute(stmt)
        conv = result.scalar_one_or_none()

        if conv is None:
            conv = Conversation(session_id=sid)
            self.session.add(conv)
            await self.session.flush()

        return conv

    async def get_by_session_id(self, session_id: str) -> Conversation | None:
        """Lookup conversation by its session identifier."""
        stmt = select(Conversation).where(Conversation.session_id == session_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        meta: dict[str, Any] | None = None,
    ) -> Message:
        """Append a message to the conversation history."""
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            meta=meta or {},
        )
        self.session.add(msg)
        await self.session.flush()
        return msg

    async def get_recent_messages(
        self,
        conversation_id: str,
        limit: int = 20,
    ) -> list[Message]:
        """Fetch up to `limit` most recent messages, returned in chronological order."""
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(desc(Message.created_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        recent_desc = result.scalars().all()
        # Return in ascending chronological order for LLM context
        return list(reversed(recent_desc))


class MemoryRepository:
    """Repository managing long-term memory records and vector similarity lookups."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        content: str,
        memory_type: str = "fact",
        embedding: list[float] | None = None,
        importance: float = 0.5,
        source: str | None = "user_explicit",
        user_id: str | None = "default_user",
    ) -> Memory:
        """Persist a new memory entry."""
        memory = Memory(
            content=content,
            memory_type=memory_type,
            embedding=embedding,
            importance=importance,
            source=source,
            user_id=user_id or "default_user",
        )
        self.session.add(memory)
        await self.session.flush()
        return memory

    async def get_by_id(self, memory_id: str, user_id: str | None = None) -> Memory | None:
        """Fetch memory entry by UUID primary key, optionally scoped by user."""
        stmt = select(Memory).where(Memory.id == memory_id)
        if user_id is not None:
            stmt = stmt.where(Memory.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(
        self,
        memory_type: str | None = None,
        limit: int = 100,
        user_id: str | None = None,
    ) -> list[Memory]:
        """List stored memories with optional type and user filter."""
        stmt = select(Memory).order_by(desc(Memory.created_at)).limit(limit)
        if memory_type:
            stmt = stmt.where(Memory.memory_type == memory_type)
        if user_id is not None:
            stmt = stmt.where(Memory.user_id == user_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search_similar(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        memory_type: str | None = None,
        user_id: str | None = None,
    ) -> list[tuple[Memory, float]]:
        """Search memories by vector similarity with pgvector or in-memory fallback, scoped by user."""
        bind = self.session.bind
        dialect_name = bind.dialect.name if bind is not None else ""

        # Check if running against PostgreSQL with native pgvector support
        if dialect_name == "postgresql":
            distance_col = Memory.embedding.cosine_distance(query_embedding).label("dist")
            stmt = select(Memory, distance_col)
            if memory_type:
                stmt = stmt.where(Memory.memory_type == memory_type)
            if user_id is not None:
                stmt = stmt.where(Memory.user_id == user_id)
            stmt = stmt.where(Memory.embedding.is_not(None)).order_by("dist").limit(top_k)

            result = await self.session.execute(stmt)
            matches = []
            for mem, dist in result.all():
                similarity = max(0.0, 1.0 - float(dist)) if dist is not None else 0.0
                matches.append((mem, similarity))
            return matches

        # Python-based fallback for SQLite / test environments
        stmt = select(Memory).where(Memory.embedding.is_not(None))
        if memory_type:
            stmt = stmt.where(Memory.memory_type == memory_type)
        if user_id is not None:
            stmt = stmt.where(Memory.user_id == user_id)

        result = await self.session.execute(stmt)
        all_mems = result.scalars().all()

        scored: list[tuple[Memory, float]] = []
        for mem in all_mems:
            if mem.embedding is not None:
                sim = cosine_similarity(query_embedding, list(mem.embedding))
                scored.append((mem, sim))

        # Sort descending by similarity
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    async def update(
        self,
        memory: Memory,
        content: str | None = None,
        embedding: list[float] | None = None,
        importance: float | None = None,
        memory_type: str | None = None,
    ) -> Memory:
        """Update fields of an existing memory."""
        if content is not None:
            memory.content = content
        if embedding is not None:
            memory.embedding = embedding
        if importance is not None:
            memory.importance = importance
        if memory_type is not None:
            memory.memory_type = memory_type

        memory.updated_at = utc_now()
        await self.session.flush()
        return memory

    async def delete(self, memory_id: str, user_id: str | None = None) -> bool:
        """Delete a memory entry by ID, scoped by user."""
        mem = await self.get_by_id(memory_id, user_id=user_id)
        if mem is None:
            return False
        await self.session.delete(mem)
        await self.session.flush()
        return True

    async def update_last_accessed(self, memory_ids: list[str]) -> None:
        """Update last_accessed_at timestamp for retrieved memories."""
        if not memory_ids:
            return
        now = utc_now()
        stmt = select(Memory).where(Memory.id.in_(memory_ids))
        result = await self.session.execute(stmt)
        for mem in result.scalars().all():
            mem.last_accessed_at = now
        await self.session.flush()
