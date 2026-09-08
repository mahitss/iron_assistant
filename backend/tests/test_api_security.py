"""Tests for API security, security headers, correlation IDs, and body size limits."""

from fastapi import status
from fastapi.testclient import TestClient

from app.main import app


def test_request_id_generated_and_propagated():
    """Middleware generates UUID request_id if none provided and echos on response header."""
    client = TestClient(app)

    res = client.get("/health")
    assert res.status_code == status.HTTP_200_OK
    assert "X-Request-ID" in res.headers
    assert res.headers["X-Request-ID"].startswith("req_")


def test_request_id_preserved_from_client():
    """Middleware preserves client-supplied correlation ID."""
    client = TestClient(app)

    custom_id = "req_custom_trace_98765"
    res = client.get("/health", headers={"X-Request-ID": custom_id})
    assert res.status_code == status.HTTP_200_OK
    assert res.headers["X-Request-ID"] == custom_id


def test_security_headers_present_on_all_responses():
    """Defensive OWASP headers are injected on all HTTP responses."""
    client = TestClient(app)

    res = client.get("/health")
    assert res.status_code == status.HTTP_200_OK
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"
    assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "default-src 'self'" in res.headers.get("Content-Security-Policy", "")


def test_body_size_limit_rejects_oversized_payloads():
    """Body size middleware returns 413 when content-length exceeds maximum configured bytes."""
    client = TestClient(app)

    # Simulate 15MB content length (limit is 10MB)
    oversized_headers = {"Content-Length": "15728640"}
    res = client.post("/api/v1/chat", content=b"x", headers=oversized_headers)
    assert res.status_code == 413
    data = res.json()
    assert data["code"] == "PAYLOAD_TOO_LARGE"


def test_exception_handler_masks_internal_stack_traces(monkeypatch):
    """Internal server errors are logged safely and return clean 500 JSON without stack traces."""
    from app.api.routes import auth

    def _broken_handler(*args, **kwargs):
        raise RuntimeError("Database connection password=secret_password_123 exploded!")

    monkeypatch.setattr(auth, "get_auth_service", _broken_handler)

    client = TestClient(app, raise_server_exceptions=False)
    res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "pwd"})

    assert res.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    data = res.json()
    assert data["status"] == "error"
    assert data["code"] == "INTERNAL_SERVER_ERROR"
    # Never leak internal variable names, stack traces, or passwords
    assert "secret_password_123" not in str(data)
    assert "Traceback" not in str(data)
