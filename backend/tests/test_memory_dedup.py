"""Unit tests for semantic deduplication and updating of existing memories."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base
from app.memory.embeddings import DeterministicEmbeddingProvider
from app.memory.schemas import MemoryCandidate, MemoryType
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
    """Deterministic embedding provider ensuring reproducible vector similarity."""
    return DeterministicEmbeddingProvider(dimension=64)


@pytest.mark.asyncio
async def test_deduplication_exact_duplicate_updates_rather_than_inserts(
    async_db_session: AsyncSession, embedding_provider
):
    """Verify that submitting the exact same memory twice results in 1 stored record with updated metadata."""
    service = MemoryService(session=async_db_session, embedding_provider=embedding_provider)

    candidate1 = MemoryCandidate(
        content="The user prefers dark mode interfaces.",
        memory_type=MemoryType.PREFERENCE,
        importance=0.6,
    )
    res1 = await service.process_candidate(candidate1, dedup_threshold=0.90)
    assert res1 is not None
    original_id = res1.id

    # Verify 1 record in DB
    all_mems = await service.list_memories()
    assert len(all_mems) == 1

    # Second candidate with same content and higher importance
    candidate2 = MemoryCandidate(
        content="The user prefers dark mode interfaces.",
        memory_type=MemoryType.PREFERENCE,
        importance=0.95,
    )
    res2 = await service.process_candidate(candidate2, dedup_threshold=0.90)
    assert res2 is not None

    # Must be the SAME ID, not a duplicate row
    assert res2.id == original_id
    assert res2.importance == 0.95

    # Total stored records must still be 1
    after_dedup = await service.list_memories()
    assert len(after_dedup) == 1


@pytest.mark.asyncio
async def test_similar_memory_updates_content(async_db_session: AsyncSession, embedding_provider):
    """Verify that an update to existing context replaces the previous statement when similarity is high."""
    service = MemoryService(session=async_db_session, embedding_provider=embedding_provider)

    c1 = MemoryCandidate(
        content="The user primary editor is Neovim.",
        memory_type=MemoryType.PREFERENCE,
        importance=0.7,
    )
    m1 = await service.process_candidate(c1, dedup_threshold=0.80)
    assert m1 is not None

    # Candidate with slight wording change
    c2 = MemoryCandidate(
        content="The user primary editor is Neovim with Lua plugins.",
        memory_type=MemoryType.PREFERENCE,
        importance=0.85,
    )
    # Using lower threshold to demonstrate update logic
    m2 = await service.process_candidate(c2, dedup_threshold=0.50)
    assert m2 is not None
    assert m2.id == m1.id
    assert "Lua plugins" in m2.content

    mems = await service.list_memories()
    assert len(mems) == 1


@pytest.mark.asyncio
async def test_unrelated_memory_creates_new_record(async_db_session: AsyncSession, embedding_provider):
    """Verify that unrelated candidates each create independent memory records."""
    service = MemoryService(session=async_db_session, embedding_provider=embedding_provider)

    c1 = MemoryCandidate(
        content="The user prefers dark mode.",
        memory_type=MemoryType.PREFERENCE,
        importance=0.8,
    )
    c2 = MemoryCandidate(
        content="The user is building Kairo in Python.",
        memory_type=MemoryType.PROJECT,
        importance=0.9,
    )

    m1 = await service.process_candidate(c1, dedup_threshold=0.90)
    m2 = await service.process_candidate(c2, dedup_threshold=0.90)

    assert m1 is not None
    assert m2 is not None
    assert m1.id != m2.id

    all_mems = await service.list_memories()
    assert len(all_mems) == 2
