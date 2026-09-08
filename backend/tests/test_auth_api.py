"""Tests for Authentication REST API endpoints (/login, /logout, /me)."""

from fastapi import status
from fastapi.testclient import TestClient

from app.main import app


def test_auth_login_success():
    """User can authenticate with valid credentials and receive bearer token."""
    client = TestClient(app)

    res = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin12345"},
    )
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user_id"] == "usr_admin"
    assert "session_id" in data


def test_auth_login_invalid_credentials():
    """Login with wrong password returns 401."""
    client = TestClient(app)

    res = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "wrong_password"},
    )
    assert res.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid username or password" in res.json()["message"]


def test_auth_me_and_logout_lifecycle():
    """User can inspect profile with bearer token, and logout revokes token."""
    client = TestClient(app)

    # 1. Login
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": "kairo", "password": "kairo_dev_password"},
    )
    assert login_res.status_code == status.HTTP_200_OK
    token = login_res.json()["access_token"]

    # 2. Get me with bearer token
    auth_headers = {"Authorization": f"Bearer {token}"}
    me_res = client.get("/api/v1/auth/me", headers=auth_headers)
    assert me_res.status_code == status.HTTP_200_OK
    assert me_res.json()["username"] == "kairo"
    assert me_res.json()["id"] == "usr_kairo"

    # 3. Logout
    logout_res = client.post("/api/v1/auth/logout", headers=auth_headers)
    assert logout_res.status_code == status.HTTP_200_OK

    # 4. Subsequent me request with revoked token fails with 401
    revoked_res = client.get("/api/v1/auth/me", headers=auth_headers)
    assert revoked_res.status_code == status.HTTP_401_UNAUTHORIZED
