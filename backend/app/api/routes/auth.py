"""Authentication REST API endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.auth.dependencies import extract_bearer_token, get_current_user
from app.auth.schemas import LoginRequest, Token, User
from app.auth.service import AuthenticationError, get_auth_service

logger = logging.getLogger("kairo.api.auth")

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token, status_code=status.HTTP_200_OK)
async def login(credentials: LoginRequest) -> Token:
    """Authenticate user credentials and return a bearer token with active security session."""
    auth_service = get_auth_service()
    try:
        token = auth_service.login(credentials.username, credentials.password)
        logger.info("User '%s' authenticated successfully.", credentials.username)
        return token
    except AuthenticationError as exc:
        logger.warning("Failed login attempt for username '%s': %s", credentials.username, exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, str]:
    """Revoke the active security session associated with the bearer token."""
    token = extract_bearer_token(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization bearer token required for logout.",
        )

    auth_service = get_auth_service()
    success = auth_service.logout(token)
    if not success:
        logger.debug("Logout requested for invalid or expired session.")

    return {"message": "Successfully logged out and session revoked."}


@router.get("/me", response_model=User)
async def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """Return currently authenticated user profile."""
    return current_user
