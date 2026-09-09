"""API tests for Kairo Unified Notification endpoints (Task 34, Spec 118, 119)."""

from datetime import UTC, datetime
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base, get_db_session
from app.main import create_app
from app.notifications.models import NotificationActionModel, NotificationModel
from app.notifications.schemas import (
    ActionStatus,
    ActionType,
    NotificationPriority,
    NotificationState,
    NotificationType,
)


@pytest.fixture
async def app_and_session():
    """Create test application bound to in-memory async database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_maker() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client, session_maker

    await engine.dispose()


@pytest.mark.asyncio
async def test_notifications_listing_and_filtering(app_and_session):
    """Verify GET /notifications returns user items with filters and pagination (Spec 119, 121, 122)."""
    client, session_maker = app_and_session

    now = datetime.now(UTC)
    async with session_maker() as session:
        # Create 2 notifications for Alice
        n1 = NotificationModel(
            id="n_alice_1",
            user_id="user_alice",
            type=NotificationType.TASK.value,
            priority=NotificationPriority.NORMAL.value,
            title="Task 1 Done",
            body="First task finished.",
            status=NotificationState.DELIVERED.value,
            created_at=now,
            correlation_id="c1",
        )
        n2 = NotificationModel(
            id="n_alice_2",
            user_id="user_alice",
            type=NotificationType.SECURITY.value,
            priority=NotificationPriority.URGENT.value,
            title="Security Alert",
            body="Suspicious session revoked.",
            status=NotificationState.DELIVERED.value,
            created_at=now,
            correlation_id="c2",
        )
        # Create 1 notification for Bob
        n3 = NotificationModel(
            id="n_bob_1",
            user_id="user_bob",
            type=NotificationType.TASK.value,
            priority=NotificationPriority.NORMAL.value,
            title="Bob Task",
            body="Bob content.",
            status=NotificationState.DELIVERED.value,
            created_at=now,
            correlation_id="c3",
        )
        session.add_all([n1, n2, n3])
        await session.commit()

    # Query Alice's notifications
    headers = {"X-User-Id": "user_alice"}
    resp = await client.get("/api/v1/notifications", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert data["unread_count"] == 2
    assert len(data["items"]) == 2

    # Filter by SECURITY type
    resp_sec = await client.get("/api/v1/notifications?type=SECURITY", headers=headers)
    assert resp_sec.status_code == 200
    sec_data = resp_sec.json()
    assert sec_data["total"] == 1
    assert sec_data["items"][0]["id"] == "n_alice_2"


@pytest.mark.asyncio
async def test_read_and_dismiss_and_mark_all_read(app_and_session):
    """Verify mark read, dismiss, and mark-all-read operations (Spec 76-78, 119)."""
    client, session_maker = app_and_session
    now = datetime.now(UTC)

    async with session_maker() as session:
        n = NotificationModel(
            id="n_read_test",
            user_id="user_alice",
            type=NotificationType.TASK.value,
            priority=NotificationPriority.NORMAL.value,
            title="Test Read",
            body="Content",
            status=NotificationState.DELIVERED.value,
            created_at=now,
            correlation_id="c_r",
        )
        session.add(n)
        await session.commit()

    headers = {"X-User-Id": "user_alice"}

    # 1. Mark Read
    r1 = await client.post("/api/v1/notifications/n_read_test/read", headers=headers)
    assert r1.status_code == 200
    assert r1.json()["status"] == "READ"

    # 2. Mark All Read
    r_all = await client.post("/api/v1/notifications/read-all", headers=headers)
    assert r_all.status_code == 200
    assert "marked_read_count" in r_all.json()

    # 3. Dismiss
    r2 = await client.post("/api/v1/notifications/n_read_test/dismiss", headers=headers)
    assert r2.status_code == 200
    assert r2.json()["status"] == "DISMISSED"


@pytest.mark.asyncio
async def test_preferences_api(app_and_session):
    """Verify GET and PUT preferences endpoints (Spec 118)."""
    client, _ = app_and_session
    headers = {"X-User-Id": "user_alice"}

    # 1. GET preferences
    r_get = await client.get("/api/v1/notifications/preferences", headers=headers)
    assert r_get.status_code == 200
    pref = r_get.json()
    assert pref["user_id"] == "user_alice"
    assert "WEB" in pref["enabled_channels"]

    # 2. PUT preferences
    update_payload = {
        "enabled_channels": ["WEB", "DESKTOP"],
        "quiet_hours_enabled": True,
        "quiet_hours_start": "23:00",
        "quiet_hours_end": "07:00",
        "timezone": "America/New_York",
        "min_priority": "NORMAL",
        "grouping_enabled": True,
        "digest_enabled": False,
        "digest_frequency": "daily",
        "type_preferences": {"TASK": True},
    }
    r_put = await client.put("/api/v1/notifications/preferences", json=update_payload, headers=headers)
    assert r_put.status_code == 200
    updated = r_put.json()
    assert updated["quiet_hours_enabled"] is True
    assert updated["timezone"] == "America/New_York"
    assert "DESKTOP" in updated["enabled_channels"]
