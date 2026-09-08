"""Tests for authentication service, password hashing, session lifecycle, and revocation."""

from datetime import datetime, timedelta, timezone

import pytest

from app.auth.schemas import UserRole
from app.auth.security import hash_password, verify_password
from app.auth.service import AuthenticationError, AuthService
from app.auth.sessions import SessionStore


def test_password_hashing_and_verification():
    """Passwords are hashed with salt and verified using constant-time comparison."""
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)

    assert hashed != password
    assert ":" in hashed
    assert verify_password(password, hashed)
    assert not verify_password("WrongPassword!", hashed)


def test_auth_service_authentication():
    """AuthService validates credentials and rejects unknown or invalid passwords."""
    service = AuthService()

    # Valid login
    user = service.authenticate("admin", "admin12345")
    assert user.username == "admin"
    assert user.role == UserRole.ADMIN

    # Invalid password
    with pytest.raises(AuthenticationError, match="Invalid username or password"):
        service.authenticate("admin", "wrong_pass")

    # Unknown user
    with pytest.raises(AuthenticationError, match="Invalid username or password"):
        service.authenticate("nonexistent_user", "password")


def test_session_store_idle_timeout_and_expiration():
    """Sessions expire when absolute TTL or idle timeout is exceeded."""
    store = SessionStore(default_ttl_seconds=10, idle_timeout_seconds=2)

    session = store.create_session(user_id="user_1", token="test_token_abc")
    assert session.user_id == "user_1"

    # Immediately valid
    retrieved = store.get_session_by_token("test_token_abc")
    assert retrieved is not None
    assert retrieved.session_id == session.session_id

    # Simulate idle timeout
    session.last_activity = datetime.now(timezone.utc) - timedelta(seconds=5)
    timed_out = store.get_session_by_token("test_token_abc")
    assert timed_out is None


def test_session_revocation():
    """Revoking session marks it revoked and invalidates token lookup."""
    store = SessionStore()
    session = store.create_session(user_id="user_2", token="test_token_xyz")

    assert store.get_session_by_token("test_token_xyz") is not None

    # Revoke
    revoked = store.revoke_session(session.session_id, reason="User logged out")
    assert revoked is True

    # Token lookup fails
    assert store.get_session_by_token("test_token_xyz") is None
    # ID lookup returns None or revoked
    assert store.get_session(session.session_id) is None
