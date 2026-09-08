"""Integration tests for Security Center REST API and cross-user isolation."""

import asyncio

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base, get_db_session
from app.main import app
from app.security.approvals import ApprovalManager


@pytest.fixture
def sqlite_security_app():
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


def test_security_settings_api(sqlite_security_app):
    """Verify capabilities can be inspected and updated per-user."""
    client = TestClient(app)
    headers = {"X-User-ID": "user_alice"}

    # 1. Get initial settings
    res = client.get("/api/v1/security/settings", headers=headers)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["computer_control"] is False
    assert data["web_research"] is True

    # 2. Update settings (enable computer control, disable voice)
    patch_res = client.patch(
        "/api/v1/security/settings",
        json={"computer_control": True, "voice": False},
        headers=headers,
    )
    assert patch_res.status_code == status.HTTP_200_OK
    updated = patch_res.json()
    assert updated["computer_control"] is True
    assert updated["voice"] is False


def test_security_approvals_api_and_cross_user_isolation(sqlite_security_app):
    """Verify approval endpoints and cross-user 403 Forbidden enforcement."""
    client = TestClient(app)
    session_factory = sqlite_security_app

    # Create an approval request for Alice directly in DB
    async def create_req():
        async with session_factory() as session:
            return await ApprovalManager.create_request(
                db_session=session,
                user_id="user_alice",
                tool_name="git_push",
                arguments={"branch": "release"},
                risk_level="HIGH",
            )

    req = asyncio.run(create_req())

    alice_headers = {"X-User-ID": "user_alice"}
    bob_headers = {"X-User-ID": "user_bob"}

    # 1. Alice lists approvals -> sees 1
    res_list = client.get("/api/v1/security/approvals", headers=alice_headers)
    assert res_list.status_code == status.HTTP_200_OK
    assert len(res_list.json()) == 1

    # 2. Bob tries to approve Alice's request -> 403 Forbidden
    res_bob = client.post(f"/api/v1/security/approvals/{req.id}/approve", headers=bob_headers)
    assert res_bob.status_code == status.HTTP_403_FORBIDDEN

    # 3. Alice approves her own request -> 200 OK
    res_alice = client.post(f"/api/v1/security/approvals/{req.id}/approve", headers=alice_headers)
    assert res_alice.status_code == status.HTTP_200_OK
    assert res_alice.json()["status"] == "approved"


def test_emergency_stop_api(sqlite_security_app):
    """Verify emergency stop trigger and reset endpoints."""
    client = TestClient(app)
    headers = {"X-User-ID": "user_stop_test"}

    # 1. Check initially active
    res1 = client.get("/api/v1/security/emergency-stop", headers=headers)
    assert res1.status_code == status.HTTP_200_OK
    assert res1.json()["is_stopped"] is False

    # 2. Trigger stop
    res2 = client.post("/api/v1/security/emergency-stop", json={"reason": "Safety alarm"}, headers=headers)
    assert res2.status_code == status.HTTP_200_OK
    assert res2.json()["is_stopped"] is True
    assert res2.json()["status"] == "STOPPED"

    # 3. Reset stop
    res3 = client.post("/api/v1/security/emergency-stop/reset", headers=headers)
    assert res3.status_code == status.HTTP_200_OK
    assert res3.json()["is_stopped"] is False
    assert res3.json()["status"] == "ACTIVE"


def test_security_audit_api(sqlite_security_app):
    """Verify audit events retrieval."""
    client = TestClient(app)
    headers = {"X-User-ID": "user_audit_test"}

    # Trigger emergency stop to generate audit event
    client.post("/api/v1/security/emergency-stop", json={"reason": "Audit trigger"}, headers=headers)

    res = client.get("/api/v1/security/audit", headers=headers)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["total"] >= 1
    assert data["items"][0]["event_type"] == "emergency_stop.enabled"
