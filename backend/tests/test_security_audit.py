"""Unit tests for AuditLogger append-only records, secret masking, and user query filtering."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base
from app.security.audit import AuditLogger


@pytest.fixture
async def async_db_session():
    """In-memory SQLite database session for unit tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_audit_event_logging_and_secret_redaction(async_db_session: AsyncSession):
    """Verify audit events are persisted and secrets are redacted from metadata."""
    event = await AuditLogger.log_event(
        db_session=async_db_session,
        user_id="user_alice",
        event_type="tool.executed",
        tool_name="web_fetch",
        risk_level="LOW",
        decision="ALLOWED",
        success=True,
        metadata={
            "url": "https://example.com",
            "api_key": "sk-secret1234567890abcdef",
        },
    )

    assert event.id is not None
    assert event.tool_name == "web_fetch"
    assert event.metadata_json["api_key"] == "[REDACTED]"
    assert event.metadata_json["url"] == "https://example.com"


@pytest.mark.asyncio
async def test_audit_query_tenant_isolation(async_db_session: AsyncSession):
    """Verify users only retrieve their own audit events."""
    await AuditLogger.log_event(
        db_session=async_db_session,
        user_id="user_alice",
        event_type="tool.executed",
        tool_name="calculator",
    )
    await AuditLogger.log_event(
        db_session=async_db_session,
        user_id="user_bob",
        event_type="tool.executed",
        tool_name="git_status",
    )

    alice_events, alice_total = await AuditLogger.query_events(
        db_session=async_db_session,
        user_id="user_alice",
    )
    assert alice_total == 1
    assert alice_events[0].tool_name == "calculator"

    bob_events, bob_total = await AuditLogger.query_events(
        db_session=async_db_session,
        user_id="user_bob",
    )
    assert bob_total == 1
    assert bob_events[0].tool_name == "git_status"
