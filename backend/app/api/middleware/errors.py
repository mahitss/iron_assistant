"""Centralized exception handlers mapping errors to safe API responses without leaking internal stack traces."""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.middleware.request_id import get_request_id
from app.auth.service import AuthenticationError
from app.models.provider import ProviderAPIError
from app.security.exceptions import SecurityError

logger = logging.getLogger("kairo.api.errors")


def register_exception_handlers(app: FastAPI) -> None:
    """Register uniform exception handlers onto FastAPI application."""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        req_id = get_request_id()
        logger.warning("[%s] Request validation error: %s", req_id, exc)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "status": "error",
                "code": "VALIDATION_ERROR",
                "detail": exc.errors(),
                "message": "Invalid request parameters or payload structure.",
                "request_id": req_id,
            },
        )

    @app.exception_handler(AuthenticationError)
    async def auth_exception_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
        req_id = get_request_id()
        logger.warning("[%s] Authentication failure: %s", req_id, exc)
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "status": "error",
                "code": "AUTHENTICATION_ERROR",
                "detail": str(exc),
                "message": str(exc),
                "request_id": req_id,
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(SecurityError)
    async def security_exception_handler(request: Request, exc: SecurityError) -> JSONResponse:
        req_id = get_request_id()
        logger.warning("[%s] Security policy violation: %s", req_id, exc)
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "status": "error",
                "code": "FORBIDDEN",
                "detail": str(exc),
                "message": str(exc),
                "request_id": req_id,
            },
        )

    @app.exception_handler(ProviderAPIError)
    async def provider_exception_handler(request: Request, exc: ProviderAPIError) -> JSONResponse:
        req_id = get_request_id()
        logger.error("[%s] Upstream provider error: %s", req_id, exc)
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "status": "error",
                "code": "PROVIDER_UNAVAILABLE",
                "detail": str(exc),
                "message": "Upstream model provider returned an error or is unavailable.",
                "request_id": req_id,
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        req_id = get_request_id()
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "code": f"HTTP_{exc.status_code}",
                "detail": exc.detail,
                "message": str(exc.detail),
                "request_id": req_id,
            },
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        req_id = get_request_id()
        # Log the full exception stack trace server-side ONLY
        logger.exception("[%s] Unhandled internal server error: %s", req_id, exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "code": "INTERNAL_SERVER_ERROR",
                "detail": "An unexpected error occurred. Please contact the administrator.",
                "message": "An unexpected error occurred. Please contact the administrator.",
                "request_id": req_id,
            },
        )
