"""Request body size limit middleware protecting against large payload DOS attacks."""

import logging
from collections.abc import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config.settings import get_settings

logger = logging.getLogger("kairo.api.body_size")


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Enforces maximum allowed request payload size."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        settings = get_settings()
        max_bytes = getattr(settings, "KAIRO_MAX_REQUEST_BODY_BYTES", 10_485_760)

        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > max_bytes:
                    logger.warning(
                        "Rejected payload exceeding limit: %d bytes (limit: %d)", length, max_bytes
                    )
                    return JSONResponse(
                        status_code=413,
                        content={
                            "status": "error",
                            "code": "PAYLOAD_TOO_LARGE",
                            "message": f"Request body exceeds limit of {max_bytes} bytes.",
                        },
                    )
            except ValueError:
                pass

        return await call_next(request)
