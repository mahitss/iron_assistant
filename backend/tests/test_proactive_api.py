"""Integration tests for Proactive Intelligence, Notifications, and Web Monitors REST APIs."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base, get_db_session
from app.main import app
from app.proactive.models import ProactiveInsight
from app.proactive.service import ProactiveService
from app.proactive.state import InsightPriority, SourceType


@pytest.fixture
def sqlite_proactive_app():
    """Setup app with in-memory SQLite database session override."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async def init_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(init_tables())

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db_session] = override_get_db
    yield session_factory
    app.dependency_overrides.pop(get_db_session, None)
    asyncio.run(engine.dispose())


def test_proactive_settings_api(sqlite_proactive_app):
    """Test retrieving and updating proactive preferences."""
    client = TestClient(app)
    headers = {"X-User-ID": "user_api_settings"}

    # 1. GET default settings
    res = client.get("/api/v1/proactive/settings", headers=headers)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["proactive_enabled"] is True
    assert data["minimum_priority"] == "LOW"

    # 2. PATCH settings
    patch_res = client.patch(
        "/api/v1/proactive/settings",
        json={
            "minimum_priority": "HIGH",
            "quiet_hours_enabled": True,
            "quiet_hours_start": "23:00",
            "quiet_hours_end": "07:00",
        },
        headers=headers,
    )
    assert patch_res.status_code == status.HTTP_200_OK
    updated = patch_res.json()
    assert updated["minimum_priority"] == "HIGH"
    assert updated["quiet_hours_enabled"] is True
    assert updated["quiet_hours_start"] == "23:00"


def test_proactive_feed_ranking_and_expiration(sqlite_proactive_app):
    """Verify feed returns deterministically ranked insights and marks expired items."""
    client = TestClient(app)
    headers = {"X-User-ID": "user_feed"}

    # Seed insights directly into DB
    async def seed():
        async with sqlite_proactive_app() as session:
            now = datetime.now(UTC)
            # Low routine item
            item1 = ProactiveInsight(
                user_id="user_feed",
                source_type=str(SourceType.WORKFLOW),
                title="Routine Completed",
                summary="Done",
                priority=InsightPriority.LOW,
                status="read",
                fingerprint="fp1",
                created_at=now - timedelta(hours=2),
            )
            # High unread item
            item2 = ProactiveInsight(
                user_id="user_feed",
                source_type=str(SourceType.GITHUB),
                title="CI Failed on main",
                summary="Build failed",
                priority=InsightPriority.HIGH,
                status="delivered",
                fingerprint="fp2",
                created_at=now - timedelta(minutes=10),
            )
            # Expired item
            item3 = ProactiveInsight(
                user_id="user_feed",
                source_type=str(SourceType.APPROVAL),
                title="Stale Approval",
                summary="Expired",
                priority=InsightPriority.HIGH,
                status="delivered",
                fingerprint="fp3",
                created_at=now - timedelta(days=2),
                expires_at=now - timedelta(hours=1),
            )
            session.add_all([item1, item2, item3])
            await session.commit()

    asyncio.run(seed())

    res = client.get("/api/v1/proactive/feed", headers=headers)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    # Expired item should be excluded from active feed
    assert data["total"] == 2
    assert data["unread_count"] == 1
    # Ranked: HIGH item should be first
    assert data["items"][0]["title"] == "CI Failed on main"
    assert data["items"][1]["title"] == "Routine Completed"


def test_notifications_read_and_dismiss_and_isolation(sqlite_proactive_app):
    """Test notification list, mark read, dismiss, and cross-user tenant isolation."""
    client = TestClient(app)
    headers_alice = {"X-User-ID": "user_alice"}
    headers_bob = {"X-User-ID": "user_bob"}

    # Seed an insight for Alice
    insight_id = ""

    async def seed():
        nonlocal insight_id
        async with sqlite_proactive_app() as session:
            ins = await ProactiveService.process_event(
                db_session=session,
                user_id="user_alice",
                source_type=SourceType.WORKFLOW,
                category="workflow.failed",
                payload={"workflow_name": "ETL", "error": "Disk full"},
            )
            assert ins is not None
            insight_id = ins.id

    asyncio.run(seed())

    # 1. Alice sees 1 unread notification
    list_res = client.get("/api/v1/notifications", headers=headers_alice)
    assert list_res.status_code == status.HTTP_200_OK
    assert list_res.json()["unread_count"] == 1

    # 2. Bob sees 0 notifications (tenant isolation)
    bob_list = client.get("/api/v1/notifications", headers=headers_bob)
    assert bob_list.status_code == status.HTTP_200_OK
    assert bob_list.json()["total"] == 0

    # 3. Bob attempts to mark Alice's notification as read -> 404
    bob_read = client.post(f"/api/v1/notifications/{insight_id}/read", headers=headers_bob)
    assert bob_read.status_code == status.HTTP_404_NOT_FOUND

    # 4. Alice marks it read
    alice_read = client.post(f"/api/v1/notifications/{insight_id}/read", headers=headers_alice)
    assert alice_read.status_code == status.HTTP_200_OK
    assert alice_read.json()["status"] == "read"

    # 5. Alice dismisses it
    alice_dismiss = client.post(f"/api/v1/notifications/{insight_id}/dismiss", headers=headers_alice)
    assert alice_dismiss.status_code == status.HTTP_200_OK
    assert alice_dismiss.json()["status"] == "dismissed"


def test_web_monitors_api_and_validation(sqlite_proactive_app):
    """Test web monitor endpoints with validation and CRUD."""
    client = TestClient(app)
    headers = {"X-User-ID": "user_web_api"}

    # 1. Reject SSRF URL
    bad_res = client.post(
        "/api/v1/web-monitors",
        json={"name": "Bad", "url": "http://10.0.0.1/admin"},
        headers=headers,
    )
    assert bad_res.status_code == status.HTTP_400_BAD_REQUEST

    # 2. Create valid monitor
    good_res = client.post(
        "/api/v1/web-monitors",
        json={"name": "Docs", "url": "https://example.com/docs"},
        headers=headers,
    )
    assert good_res.status_code == status.HTTP_201_CREATED
    m_id = good_res.json()["id"]

    # 3. List
    list_res = client.get("/api/v1/web-monitors", headers=headers)
    assert len(list_res.json()) == 1

    # 4. Patch
    patch_res = client.patch(
        f"/api/v1/web-monitors/{m_id}",
        json={"name": "Updated Docs"},
        headers=headers,
    )
    assert patch_res.status_code == status.HTTP_200_OK
    assert patch_res.json()["name"] == "Updated Docs"

    # 5. Delete
    del_res = client.delete(f"/api/v1/web-monitors/{m_id}", headers=headers)
    assert del_res.status_code == status.HTTP_204_NO_CONTENT
