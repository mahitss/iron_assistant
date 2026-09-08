"""Authentication context middleware populating request state."""

import logging
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.auth.dependencies import extract_bearer_token
from app.auth.service import get_auth_service
from app.config.settings import get_settings

logger = logging.getLogger("kairo.auth.middleware")


class AuthContextMiddleware(BaseHTTPMiddleware):
    """Middleware populating authenticated user and session ID into request.state."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        auth_service = get_auth_service()
        settings = get_settings()

        auth_header = request.headers.get("Authorization")
        token = extract_bearer_token(auth_header)

        user_id = "anonymous"
        session_id = None

        if token:
            validated = auth_service.validate_token(token)
            if validated:
                user, session = validated
                user_id = user.id
                session_id = session.session_id
        elif not settings.ENVIRONMENT.is_production:
            # Development fallback from X-User-ID header
            x_user_id = request.headers.get("X-User-ID")
            user_id = x_user_id.strip() if x_user_id and x_user_id.strip() else "default_user"

        request.state.user_id = user_id
        request.state.session_id = session_id

        return await call_next(request)
