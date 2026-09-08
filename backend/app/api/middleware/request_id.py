"""Request ID middleware propagating correlation IDs through requests, tools, and responses."""

import contextvars
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Context variable for correlation ID across async execution contexts
current_request_id: contextvars.ContextVar[str] = contextvars.ContextVar("current_request_id", default="")


def get_request_id() -> str:
    """Retrieve current request correlation ID."""
    val = current_request_id.get()
    return val if val else "req_system"


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Assigns or propagates X-Request-ID to ensure full lifecycle observability."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        inbound_id = request.headers.get("X-Request-ID")
        req_id = inbound_id.strip() if inbound_id and inbound_id.strip() else f"req_{uuid.uuid4().hex[:16]}"

        token = current_request_id.set(req_id)
        request.state.request_id = req_id

        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            return response
        finally:
            current_request_id.reset(token)
