"""Tests for Kairo Device Runtime API, tenant boundaries, capability gating, and command dispatch."""

import asyncio

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base, get_db_session
from app.main import app
from app.security.center import get_security_center


@pytest.fixture
def sqlite_device_app():
    """Setup app with in-memory SQLite database session override for device tests."""
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


def test_device_registration_and_list(sqlite_device_app):
    """Verify device registration flow and listing under authenticated user."""
    client = TestClient(app)
    reg_payload = {
        "device_name": "Workstation Alpha",
        "os_name": "windows",
        "os_version": "10.0.26100",
        "companion_version": "1.1.0",
        "allowed_paths": ["C:\\Projects\\Kairo"],
    }
    headers = {"X-User-ID": "user_dev_1"}

    # 1. Register Device
    res = client.post("/api/v1/devices/register", json=reg_payload, headers=headers)
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()

    device_id = data["device_id"]
    assert device_id.startswith("dev_")
    assert data["device_name"] == "Workstation Alpha"
    assert data["status"] == "ACTIVE"
    assert "device_token" in data
    assert data["device_token"].startswith("kairo_dtk_")
    assert data["capabilities"]["computer_control"] is False
    assert data["capabilities"]["voice"] is False
    assert data["capabilities"]["camera"] is False
    assert data["capabilities"]["filesystem"] is False
    assert data["allowed_paths"] == ["C:\\Projects\\Kairo"]

    # 2. List Devices
    res = client.get("/api/v1/devices", headers=headers)
    assert res.status_code == status.HTTP_200_OK
    devices = res.json()
    assert len(devices) >= 1
    assert any(d["device_id"] == device_id for d in devices)


def test_device_tenant_isolation(sqlite_device_app):
    """Verify strict tenant isolation: user A cannot inspect or modify user B's device."""
    client = TestClient(app)
    user_a = {"X-User-ID": "user_alice"}
    user_b = {"X-User-ID": "user_bob"}

    reg_payload = {
        "device_name": "Alice Laptop",
        "os_name": "darwin",
        "os_version": "14.2",
    }
    res = client.post("/api/v1/devices/register", json=reg_payload, headers=user_a)
    assert res.status_code == status.HTTP_201_CREATED
    device_id = res.json()["device_id"]

    # User B attempts to access Alice's device
    res_b = client.get(f"/api/v1/devices/{device_id}", headers=user_b)
    assert res_b.status_code == status.HTTP_403_FORBIDDEN

    # User B attempts to update Alice's device
    res_b_patch = client.patch(
        f"/api/v1/devices/{device_id}",
        json={"device_name": "Hijacked Device"},
        headers=user_b,
    )
    assert res_b_patch.status_code == status.HTTP_403_FORBIDDEN


def test_device_capability_update_and_command_gating(sqlite_device_app):
    """Verify capability updates and allowlisted command dispatch lifecycle."""
    client = TestClient(app)
    headers = {"X-User-ID": "user_dev_commands"}

    # 1. Register device (capabilities start OFF)
    reg_payload = {"device_name": "Test Rig", "os_name": "linux"}
    res = client.post("/api/v1/devices/register", json=reg_payload, headers=headers)
    device_id = res.json()["device_id"]

    # 2. Attempt command while computer_control is disabled -> 403 CapabilityDisabledError
    res = client.post(
        f"/api/v1/devices/{device_id}/commands",
        json={"action": "mouse.click", "parameters": {"x": 100, "y": 200}},
        headers=headers,
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN
    assert "disabled" in res.json()["detail"].lower()

    # 3. Enable computer_control capability
    res = client.patch(
        f"/api/v1/devices/{device_id}",
        json={"computer_control_enabled": True},
        headers=headers,
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["capabilities"]["computer_control"] is True

    # 4. Dispatch risky action without approval artifact -> returns PENDING_APPROVAL
    res = client.post(
        f"/api/v1/devices/{device_id}/commands",
        json={"action": "mouse.click", "parameters": {"x": 100, "y": 200}},
        headers=headers,
    )
    assert res.status_code == status.HTTP_200_OK
    cmd_data = res.json()
    assert cmd_data["status"] == "PENDING_APPROVAL"
    assert cmd_data["approval_required"] is True
    assert cmd_data["approval_id"] is not None

    # 5. Dispatch with valid approval context -> returns DISPATCHED
    sec_center = get_security_center()
    approval_artifact = sec_center.create_device_approval_artifact(
        user_id="user_dev_commands",
        device_id=device_id,
        action="mouse.click",
    )
    assert sec_center.verify_device_approval_artifact(approval_artifact) is True

    res = client.post(
        f"/api/v1/devices/{device_id}/commands",
        json={
            "action": "mouse.click",
            "parameters": {"x": 100, "y": 200},
            "authorization_context": approval_artifact["signature"],
        },
        headers=headers,
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["status"] == "DISPATCHED"


def test_device_forbidden_actions_rejected(sqlite_device_app):
    """Verify arbitrary shell execution and unknown actions are blocked with 400 Bad Request."""
    client = TestClient(app)
    headers = {"X-User-ID": "user_dev_security"}
    reg_payload = {"device_name": "Sec Test", "os_name": "windows"}
    res = client.post("/api/v1/devices/register", json=reg_payload, headers=headers)
    device_id = res.json()["device_id"]

    # Enable all capabilities
    client.patch(
        f"/api/v1/devices/{device_id}",
        json={"computer_control_enabled": True, "filesystem_enabled": True},
        headers=headers,
    )

    # 1. Arbitrary shell command
    res = client.post(
        f"/api/v1/devices/{device_id}/commands",
        json={"action": "shell.execute", "parameters": {"command": "dir"}},
        headers=headers,
    )
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert "forbidden" in res.json()["detail"].lower()

    # 2. PowerShell command
    res = client.post(
        f"/api/v1/devices/{device_id}/commands",
        json={"action": "powershell.run", "parameters": {"cmd": "Get-Process"}},
        headers=headers,
    )
    assert res.status_code == status.HTTP_400_BAD_REQUEST

    # 3. Arbitrary Python
    res = client.post(
        f"/api/v1/devices/{device_id}/commands",
        json={"action": "arbitrary_python", "parameters": {"code": "import os"}},
        headers=headers,
    )
    assert res.status_code == status.HTTP_400_BAD_REQUEST


def test_device_revocation(sqlite_device_app):
    """Verify device revocation immediately invalidates credentials and stops commands."""
    client = TestClient(app)
    headers = {"X-User-ID": "user_dev_revoke"}
    reg_payload = {"device_name": "Old Phone", "os_name": "linux"}
    res = client.post("/api/v1/devices/register", json=reg_payload, headers=headers)
    device_id = res.json()["device_id"]

    # Revoke device
    res = client.post(f"/api/v1/devices/{device_id}/revoke", headers=headers)
    assert res.status_code == status.HTTP_200_OK
    rev_data = res.json()
    assert rev_data["status"] == "REVOKED"
    assert rev_data["capabilities"]["computer_control"] is False
    assert rev_data["revoked_at"] is not None

    # Attempt to dispatch command to revoked device -> 400 Bad Request
    res = client.post(
        f"/api/v1/devices/{device_id}/commands",
        json={"action": "screen.capture"},
        headers=headers,
    )
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert "revoked" in res.json()["detail"].lower()
