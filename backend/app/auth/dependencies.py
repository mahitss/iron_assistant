"""FastAPI dependencies for user authentication and session context."""

import logging
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from app.auth.schemas import AuthSession, User
from app.auth.service import get_auth_service
from app.config.settings import get_settings

logger = logging.getLogger("kairo.auth.dependencies")


def extract_bearer_token(authorization: Annotated[str | None, Header()] = None) -> str | None:
    """Extract raw bearer token from Authorization header if present."""
    if not authorization:
        return None
    parts = authorization.strip().split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def get_current_session_and_user(
    token: Annotated[str | None, Depends(extract_bearer_token)],
    x_user_id: Annotated[str | None, Header()] = None,
) -> tuple[User, AuthSession | None]:
    """Resolve current authenticated user and session, enforcing production requirements."""
    settings = get_settings()
    auth_service = get_auth_service()

    if token:
        validated = auth_service.validate_token(token)
        if not validated:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid, expired, or revoked authentication token.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return validated

    # When no token is supplied:
    if settings.ENVIRONMENT.is_production:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Bearer token missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # In development/testing, allow local fallback to default user or X-User-ID header
    fallback_id = x_user_id.strip() if x_user_id and x_user_id.strip() else "default_user"
    user = auth_service.get_user_by_id(fallback_id)
    if not user:
        user = User(id=fallback_id, username=fallback_id)
    return user, None


def get_current_user(
    context: Annotated[tuple[User, AuthSession | None], Depends(get_current_session_and_user)],
) -> User:
    """Dependency returning authenticated User."""
    return context[0]


def get_current_user_id(
    current_user: Annotated[User, Depends(get_current_user)],
) -> str:
    """Dependency returning authenticated user ID."""
    return current_user.id


def get_current_session(
    context: Annotated[tuple[User, AuthSession | None], Depends(get_current_session_and_user)],
) -> AuthSession | None:
    """Dependency returning active AuthSession if established."""
    return context[1]
