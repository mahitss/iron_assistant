"""Tests for DocumentIngestionService, validation, semantic chunking, and security."""

import pytest
from app.db.session import Base
from app.knowledge.ingestion.documents import DocumentIngestionService
from app.knowledge.schemas import IndexJobStatus
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.fixture
async def async_db_session():
    """Create in-memory SQLite engine and AsyncSession fixture."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_document_ingestion_and_chunking(async_db_session: AsyncSession):
    """Verify markdown document validation, text extraction, semantic chunking, and edge linking."""
    service = DocumentIngestionService()
    user_id = "user_doc_test"

    markdown_doc = (
        "# System Architecture\n\n"
        "Kairo uses a multi-agent orchestration architecture coordinated by a Supervisor.\n\n"
        "## Core Memory\n\n"
        "Memory persistence is managed via PostgreSQL with pgvector extension.\n\n"
        "## Security Model\n\n"
        "SecurityCenter is authoritative for all tool and capability permissions.\n"
    ).encode("utf-8")

    res = await service.ingest_document(
        session=async_db_session,
        user_id=user_id,
        filename="architecture.md",
        file_bytes=markdown_doc,
        project_id="proj_kairo",
    )

    assert res.status == IndexJobStatus.COMPLETE
    assert res.document_id is not None
    assert res.chunks_created >= 1
    assert "architecture.md" in res.message


@pytest.mark.asyncio
async def test_document_security_validations(async_db_session: AsyncSession):
    """Verify size limits, extension allowlists, and path traversal defenses."""
    service = DocumentIngestionService()
    user_id = "user_sec_test"

    # 1. Reject forbidden extension
    with pytest.raises(ValueError, match="is not permitted"):
        await service.ingest_document(
            session=async_db_session,
            user_id=user_id,
            filename="malicious_script.sh",
            file_bytes=b"rm -rf /",
        )

    # 2. Reject path traversal in filename
    with pytest.raises(ValueError, match="Malicious filename or path traversal"):
        await service.ingest_document(
            session=async_db_session,
            user_id=user_id,
            filename="../../etc/passwd",
            file_bytes=b"root:x:0:0:root:/root:/bin/bash",
        )

    # 3. Reject oversized document (> 10MB)
    oversized = b"x" * (10485760 + 10)
    with pytest.raises(ValueError, match="exceeds maximum permitted limit"):
        await service.ingest_document(
            session=async_db_session,
            user_id=user_id,
            filename="huge_file.txt",
            file_bytes=oversized,
        )

    # 4. Reject empty file
    with pytest.raises(ValueError, match="Uploaded file is empty"):
        await service.ingest_document(
            session=async_db_session,
            user_id=user_id,
            filename="empty.txt",
            file_bytes=b"",
        )
