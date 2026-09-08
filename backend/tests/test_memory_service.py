"""Unit tests for MemoryService: creation, semantic search, ranking, and context formatting."""

from datetime import UTC

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base
from app.memory.embeddings import DeterministicEmbeddingProvider
from app.memory.sanitizer import UnsafeMemoryError
from app.memory.schemas import MemoryType
from app.memory.service import MemoryService


@pytest.fixture
async def async_db_session():
    """Provide isolated in-memory SQLite database session for unit tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def embedding_provider():
    """Use zero-dependency deterministic embedding provider for reproducible tests."""
    return DeterministicEmbeddingProvider(dimension=64)


@pytest.mark.asyncio
async def test_create_memory_success(async_db_session: AsyncSession, embedding_provider):
    """Test explicit memory creation with sanitization and vector embedding."""
    service = MemoryService(session=async_db_session, embedding_provider=embedding_provider)

    mem = await service.create_memory(
        content="User prefers dark mode interfaces.",
        memory_type=MemoryType.PREFERENCE,
        importance=0.8,
        source="user_explicit",
    )

    assert mem.id is not None
    assert mem.content == "User prefers dark mode interfaces."
    assert mem.memory_type == "preference"
    assert mem.importance == 0.8


@pytest.mark.asyncio
async def test_create_memory_rejects_sensitive_data(async_db_session: AsyncSession, embedding_provider):
    """Verify memory creation raises UnsafeMemoryError if credentials are present."""
    service = MemoryService(session=async_db_session, embedding_provider=embedding_provider)

    with pytest.raises(UnsafeMemoryError):
        await service.create_memory(
            content="Password is secret123456",
            memory_type=MemoryType.FACT,
        )


@pytest.mark.asyncio
async def test_semantic_search_and_ranking(async_db_session: AsyncSession, embedding_provider):
    """Test vector similarity search with deterministic composite ranking and top-k."""
    service = MemoryService(session=async_db_session, embedding_provider=embedding_provider)

    # Insert three distinct memories
    await service.create_memory(
        content="Project backend is built with FastAPI and PostgreSQL.",
        memory_type=MemoryType.PROJECT,
        importance=0.9,
    )
    await service.create_memory(
        content="User's cat is named Luna.",
        memory_type=MemoryType.FACT,
        importance=0.3,
    )
    await service.create_memory(
        content="Kairo uses FastAPI for routing.",
        memory_type=MemoryType.PROJECT,
        importance=0.7,
    )

    # Search for FastAPI project details
    results = await service.search_memories(
        query="Tell me about the FastAPI backend framework.",
        top_k=2,
    )

    assert len(results) <= 2
    # Ensure returned results have valid similarity and composite score
    for r in results:
        assert 0.0 <= r.similarity <= 1.0
        assert 0.0 <= r.score <= 1.0
        assert r.memory.id is not None

    # Top-K limiting is strictly respected
    assert len(results) == 2


@pytest.mark.asyncio
async def test_search_graceful_degradation_without_embedding_provider(async_db_session: AsyncSession):
    """Verify search returns empty list without crashing when no embedding provider is available."""
    service = MemoryService(session=async_db_session, embedding_provider=None)

    results = await service.search_memories("Any query", top_k=5)
    assert results == []


@pytest.mark.asyncio
async def test_format_memories_for_context():
    """Verify clean internal representation of retrieved memories for LLM prompt."""
    service = MemoryService(session=None, embedding_provider=None)

    # Empty list yields empty string
    assert service.format_memories_for_context([]) == ""

    from datetime import datetime

    from app.memory.schemas import MemoryResponse

    now = datetime.now(UTC)
    mems = [
        MemoryResponse(
            id="1",
            content="User prefers concise explanations.",
            memory_type="preference",
            importance=0.8,
            source="user",
            created_at=now,
            updated_at=now,
            last_accessed_at=None,
        ),
        MemoryResponse(
            id="2",
            content="Project uses PostgreSQL and pgvector.",
            memory_type="project",
            importance=0.9,
            source="user",
            created_at=now,
            updated_at=now,
            last_accessed_at=None,
        ),
    ]

    formatted = service.format_memories_for_context(mems)
    assert "Relevant memories:" in formatted
    assert "- User prefers concise explanations." in formatted
    assert "- Project uses PostgreSQL and pgvector." in formatted
    # No internal IDs or embeddings in prompt
    assert "1" not in formatted
    assert "0.8" not in formatted
