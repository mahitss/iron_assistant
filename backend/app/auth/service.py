"""Authentication service orchestrating login, token issuance, and session verification."""

import logging
from typing import Any

from app.auth.schemas import AuthSession, Token, User, UserRole
from app.auth.security import (
    generate_secure_token,
    hash_password,
    sign_token,
    verify_password,
    verify_signed_token,
)
from app.auth.sessions import get_session_store
from app.config.settings import get_settings

logger = logging.getLogger("kairo.auth.service")


class AuthenticationError(Exception):
    """Raised when authentication fails."""


class AuthService:
    """Service managing authentication, credential verification, and user sessions."""

    def __init__(self) -> None:
        self.session_store = get_session_store()
        # Seed default development users
        self._users: dict[str, dict[str, Any]] = {
            "admin": {
                "id": "usr_admin",
                "username": "admin",
                "password_hash": hash_password("admin12345"),
                "email": "admin@kairo.local",
                "role": UserRole.ADMIN,
                "is_active": True,
            },
            "kairo": {
                "id": "usr_kairo",
                "username": "kairo",
                "password_hash": hash_password("kairo_dev_password"),
                "email": "user@kairo.local",
                "role": UserRole.USER,
                "is_active": True,
            },
            "default_user": {
                "id": "default_user",
                "username": "default_user",
                "password_hash": hash_password("default_password"),
                "email": "default@kairo.local",
                "role": UserRole.USER,
                "is_active": True,
            },
        }

    def register_user(
        self, username: str, password: str, email: str | None = None, role: UserRole = UserRole.USER
    ) -> User:
        """Register a new user with securely hashed password."""
        user_id = f"usr_{username}"
        self._users[username] = {
            "id": user_id,
            "username": username,
            "password_hash": hash_password(password),
            "email": email,
            "role": role,
            "is_active": True,
        }
        return User(id=user_id, username=username, email=email, role=role, is_active=True)

    def get_user_by_username(self, username: str) -> User | None:
        """Fetch user by username."""
        data = self._users.get(username)
        if not data:
            return None
        return User(
            id=data["id"],
            username=data["username"],
            email=data.get("email"),
            role=data.get("role", UserRole.USER),
            is_active=data.get("is_active", True),
        )

    def get_user_by_id(self, user_id: str) -> User | None:
        """Fetch user by ID."""
        for data in self._users.values():
            if data["id"] == user_id:
                return User(
                    id=data["id"],
                    username=data["username"],
                    email=data.get("email"),
                    role=data.get("role", UserRole.USER),
                    is_active=data.get("is_active", True),
                )
        return None

    def authenticate(self, username: str, password: str) -> User:
        """Authenticate user credentials."""
        user_data = self._users.get(username)
        if not user_data:
            raise AuthenticationError("Invalid username or password.")

        if not user_data.get("is_active", True):
            raise AuthenticationError("User account is inactive.")

        if not verify_password(password, user_data["password_hash"]):
            raise AuthenticationError("Invalid username or password.")

        return User(
            id=user_data["id"],
            username=user_data["username"],
            email=user_data.get("email"),
            role=user_data.get("role", UserRole.USER),
            is_active=user_data.get("is_active", True),
        )

    def login(self, username: str, password: str) -> Token:
        """Authenticate credentials, create a security session, and issue a bearer token."""
        user = self.authenticate(username, password)
        raw_token = generate_secure_token()

        cfg = get_settings()
        secret_key = cfg.secret_key_str or "kairo_dev_secret_key_32_bytes_long_min"
        signed_token = sign_token(raw_token, secret_key)

        session = self.session_store.create_session(
            user_id=user.id,
            token=signed_token,
            role=user.role,
            metadata={"username": user.username},
        )

        return Token(
            access_token=signed_token,
            token_type="bearer",
            expires_in=self.session_store.default_ttl,
            user_id=user.id,
            session_id=session.session_id,
        )

    def validate_token(self, token: str) -> tuple[User, AuthSession] | None:
        """Validate signed bearer token and retrieve active user and session."""
        cfg = get_settings()
        secret_key = cfg.secret_key_str or "kairo_dev_secret_key_32_bytes_long_min"
        raw = verify_signed_token(token, secret_key)
        if not raw:
            # Fallback check on raw token string if unsigned
            raw = token

        session = self.session_store.get_session_by_token(token)
        if not session:
            return None

        user = self.get_user_by_id(session.user_id)
        if not user or not user.is_active:
            return None

        return user, session

    def logout(self, token: str) -> bool:
        """Revoke active session associated with token."""
        session = self.session_store.get_session_by_token(token)
        if not session:
            return False
        return self.session_store.revoke_session(session.session_id, reason="User logout")


_AUTH_SERVICE: AuthService | None = None


def get_auth_service() -> AuthService:
    """Return singleton instance of AuthService."""
    global _AUTH_SERVICE
    if _AUTH_SERVICE is None:
        _AUTH_SERVICE = AuthService()
    return _AUTH_SERVICE
