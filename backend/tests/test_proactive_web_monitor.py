"""Tests for WebMonitor CRUD, SSRF safety validation, and change detection."""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base
from app.proactive.models import ProactiveInsight
from app.proactive.schemas import WebMonitorCreate, WebMonitorUpdate
from app.proactive.service import ProactiveService
from app.tools.web.safety import SSRFViolationError


@pytest.fixture
async def db_session():
    """Create in-memory SQLite database session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_web_monitor_ssrf_protection(db_session: AsyncSession):
    """Monitors targeting internal/private IPs or metadata endpoints must be blocked."""
    # Cloud metadata endpoint
    with pytest.raises(SSRFViolationError):
        await ProactiveService.create_web_monitor(
            db_session,
            "user_ssrf",
            WebMonitorCreate(name="IMDS", url="http://169.254.169.254/latest/meta-data"),
        )

    # Localhost
    with pytest.raises(SSRFViolationError):
        await ProactiveService.create_web_monitor(
            db_session,
            "user_ssrf",
            WebMonitorCreate(name="Localhost", url="http://127.0.0.1:8000/internal"),
        )


@pytest.mark.asyncio
async def test_web_monitor_crud(db_session: AsyncSession):
    """Test full CRUD lifecycle of web monitors with user scoping."""
    user_id = "user_crud"

    # Create
    monitor = await ProactiveService.create_web_monitor(
        db_session,
        user_id,
        WebMonitorCreate(name="FastAPI Docs", url="https://fastapi.tiangolo.com"),
    )
    assert monitor.id is not None
    assert monitor.name == "FastAPI Docs"

    # List
    items = await ProactiveService.list_web_monitors(db_session, user_id)
    assert len(items) == 1
    assert items[0].id == monitor.id

    # Update
    updated = await ProactiveService.update_web_monitor(
        db_session,
        user_id,
        monitor.id,
        WebMonitorUpdate(name="FastAPI Official"),
    )
    assert updated is not None
    assert updated.name == "FastAPI Official"

    # Delete
    deleted = await ProactiveService.delete_web_monitor(db_session, user_id, monitor.id)
    assert deleted is True

    # Verify deleted
    empty = await ProactiveService.list_web_monitors(db_session, user_id)
    assert len(empty) == 0


@pytest.mark.asyncio
async def test_web_monitor_change_detection(db_session: AsyncSession):
    """Verify content fingerprinting detects HTML changes and triggers proactive insights."""
    user_id = "user_monitor"
    with patch("app.tools.web.safety.URLSafetyValidator._resolve_host", return_value=["93.184.216.34"]):
        monitor = await ProactiveService.create_web_monitor(
            db_session,
            user_id,
            WebMonitorCreate(name="Status Page", url="https://status.example.com"),
        )

        # Mock response 1
        mock_resp1 = AsyncMock()
        mock_resp1.text = "<html><body><h1>Status</h1><p>All systems normal.</p></body></html>"
        mock_resp1.raise_for_status = lambda: None

        with patch("httpx.AsyncClient.get", return_value=mock_resp1):
            res1 = await ProactiveService.check_web_monitor(db_session, monitor)
            assert res1.changed is False
            assert monitor.content_fingerprint is not None

        # Mock response 2: Unchanged content -> No change detected
        with patch("httpx.AsyncClient.get", return_value=mock_resp1):
            res2 = await ProactiveService.check_web_monitor(db_session, monitor)
            assert res2.changed is False

        # Mock response 3: Changed content -> Change detected & proactive event dispatched!
        mock_resp2 = AsyncMock()
        mock_resp2.text = "<html><body><h1>Status</h1><p>Outage reported in us-east-1.</p></body></html>"
        mock_resp2.raise_for_status = lambda: None

        with patch("httpx.AsyncClient.get", return_value=mock_resp2):
            res3 = await ProactiveService.check_web_monitor(db_session, monitor)
            assert res3.changed is True
            assert res3.new_fingerprint != res1.new_fingerprint

        # Verify that a proactive insight was created in the database
        insights = (
            await db_session.execute(
                ProactiveInsight.__table__.select().where(ProactiveInsight.user_id == user_id)
            )
        ).all()
        assert len(insights) >= 1
