"""Authentication schemas and session models."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class UserRole(str, Enum):
    """User authorization roles."""

    ADMIN = "admin"
    USER = "user"
    SERVICE = "service"


class User(BaseModel):
    """Authenticated user representation."""

    id: str
    username: str
    email: str | None = None
    role: UserRole = UserRole.USER
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    """User login request credentials."""

    username: str
    password: str


class Token(BaseModel):
    """Authentication bearer token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    session_id: str


class AuthSession(BaseModel):
    """Active user security session."""

    session_id: str
    user_id: str
    role: UserRole = UserRole.USER
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    is_revoked: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
