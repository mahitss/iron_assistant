"""Integration tests for Identity, Session, Presence, Handoff, and Trust REST APIs (Spec 116)."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base, get_db_session
from app.devices.models import DeviceModel
from app.main import create_app


@pytest.fixture
async def app_and_client():
    """Create test FastAPI client with in-memory database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    app = create_app()

    async def override_get_db():
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, async_session

    await engine.dispose()


@pytest.mark.asyncio
async def test_session_api_lifecycle(app_and_client):
    """Verify session create, list, revoke, and revoke-all endpoints (Spec 116)."""
    client, _ = app_and_client
    headers = {"x-user-id": "user_api_test"}

    # 1. Create session
    create_resp = await client.post(
        "/api/v1/identity/sessions",
        json={"client_type": "WEB", "metadata": {"ip": "127.0.0.1"}},
        headers=headers,
    )
    assert create_resp.status_code == 201
    sess_data = create_resp.json()
    sess_id = sess_data["session_id"]
    assert sess_data["status"] == "ACTIVE"

    # 2. List sessions
    list_resp = await client.get("/api/v1/identity/sessions", headers=headers)
    assert list_resp.status_code == 200
    sessions = list_resp.json()
    assert len(sessions) >= 1
    assert sessions[0]["session_id"] == sess_id

    # 3. Revoke single session
    revoke_resp = await client.post(
        f"/api/v1/identity/sessions/{sess_id}/revoke",
        json={"reason": "User logout"},
        headers=headers,
    )
    assert revoke_resp.status_code == 200
    assert revoke_resp.json()["status"] == "REVOKED"

    # 4. Create another session and test revoke-all
    await client.post("/api/v1/identity/sessions", json={"client_type": "DESKTOP"}, headers=headers)
    await client.post("/api/v1/identity/sessions", json={"client_type": "VOICE"}, headers=headers)

    revoke_all_resp = await client.post("/api/v1/identity/sessions/revoke-all", headers=headers)
    assert revoke_all_resp.status_code == 200
    assert revoke_all_resp.json()["revoked_count"] == 2


@pytest.mark.asyncio
async def test_presence_api_endpoints(app_and_client):
    """Verify presence heartbeat and online status endpoints (Spec 116)."""
    client, _ = app_and_client
    headers = {"x-user-id": "user_api_test"}

    # Create session first
    create_resp = await client.post(
        "/api/v1/identity/sessions",
        json={"client_type": "WEB"},
        headers=headers,
    )
    sess_id = create_resp.json()["session_id"]

    # Send heartbeat
    heartbeat_resp = await client.post(
        "/api/v1/identity/presence/heartbeat",
        json={"session_id": sess_id, "interface": "WEB", "state": "ACTIVE"},
        headers=headers,
    )
    assert heartbeat_resp.status_code == 200
    assert heartbeat_resp.json()["state"] == "ACTIVE"

    # Get presence
    presence_resp = await client.get("/api/v1/identity/presence", headers=headers)
    assert presence_resp.status_code == 200
    assert len(presence_resp.json()) == 1

    # Get online status
    online_resp = await client.get("/api/v1/identity/presence/online-status", headers=headers)
    assert online_resp.status_code == 200
    assert online_resp.json()["status_text"] == "Kairo session active"


@pytest.mark.asyncio
async def test_handoff_api_endpoints(app_and_client):
    """Verify cross-interface handoff ticket creation and completion (Spec 116)."""
    client, _ = app_and_client
    headers = {"x-user-id": "user_api_test"}

    # Create source session
    s1 = (await client.post("/api/v1/identity/sessions", json={"client_type": "WEB"}, headers=headers)).json()
    # Create target session
    s2 = (await client.post("/api/v1/identity/sessions", json={"client_type": "DESKTOP"}, headers=headers)).json()

    # Initiate handoff
    create_resp = await client.post(
        "/api/v1/identity/handoff",
        json={
            "source_session_id": s1["session_id"],
            "conversation_id": "conv_999",
            "explicit_consent": True,
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    handoff_data = create_resp.json()
    ho_id = handoff_data["handoff_id"]
    token = handoff_data["handoff_token"]

    # Complete handoff
    complete_resp = await client.post(
        f"/api/v1/identity/handoff/{ho_id}/complete",
        json={"handoff_token": token, "target_session_id": s2["session_id"]},
        headers=headers,
    )
    assert complete_resp.status_code == 200
    assert complete_resp.json()["conversation_id"] == "conv_999"


@pytest.mark.asyncio
async def test_device_trust_and_pairing_api(app_and_client):
    """Verify device trust and pairing code endpoints (Spec 116)."""
    client, session_factory = app_and_client
    headers = {"x-user-id": "user_api_test"}

    # 1. Initiate pairing
    pair_resp = await client.post(
        "/api/v1/devices/pair",
        json={"device_name": "Companion-Node", "client_type": "LOCAL_COMPANION", "capabilities": ["SCREEN"]},
        headers=headers,
    )
    assert pair_resp.status_code == 201
    pair_data = pair_resp.json()
    assert "pairing_code" in pair_data
    dev_id = pair_data["device_id"]

    # 2. Consume pairing code
    consume_resp = await client.post(
        "/api/v1/devices/pair/consume",
        json={"device_id": dev_id, "pairing_code": pair_data["pairing_code"]},
        headers=headers,
    )
    assert consume_resp.status_code == 200
    assert consume_resp.json()["status"] == "ACTIVE"

    # 3. Explicitly trust device
    trust_resp = await client.post(
        f"/api/v1/devices/{dev_id}/trust",
        json={"trust_status": "TRUSTED", "expires_in_days": 30},
        headers=headers,
    )
    assert trust_resp.status_code == 200
    assert trust_resp.json()["trust_status"] == "TRUSTED"
