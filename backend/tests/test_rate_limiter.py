"""Tests for rate limiting logic and emergency stop exemption."""

from fastapi import status
from fastapi.testclient import TestClient

from app.api.middleware.rate_limit import RateLimiter, get_rate_limiter
from app.main import app


def test_rate_limiter_sliding_window():
    """RateLimiter permits up to max_requests and rejects subsequent requests with retry_after."""
    limiter = RateLimiter()

    key = "test_user_key"
    max_requests = 3
    window_seconds = 10

    for _ in range(max_requests):
        allowed, retry_after = limiter.is_allowed(
            key, max_requests=max_requests, window_seconds=window_seconds
        )
        assert allowed is True
        assert retry_after == 0

    # 4th request must be rejected
    allowed, retry_after = limiter.is_allowed(key, max_requests=max_requests, window_seconds=window_seconds)
    assert allowed is False
    assert retry_after > 0


def test_rate_limit_middleware_returns_429_on_excessive_calls():
    """Middleware intercepts excessive calls and returns HTTP 429 with Retry-After header."""
    limiter = get_rate_limiter()
    limiter.reset()

    client = TestClient(app)
    headers = {"X-User-ID": "spammer_user"}

    # Exhaust limit for login attempts (10/min)
    for _ in range(10):
        client.post("/api/v1/auth/login", json={"username": "a", "password": "b"}, headers=headers)

    # 11th attempt must be 429
    res = client.post("/api/v1/auth/login", json={"username": "a", "password": "b"}, headers=headers)
    assert res.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    data = res.json()
    assert data["code"] == "RATE_LIMIT_EXCEEDED"
    assert "Retry-After" in res.headers

    limiter.reset()


def test_emergency_stop_exempt_from_aggressive_rate_limiting():
    """Emergency stop endpoint must never be blocked by rate limiting."""
    limiter = get_rate_limiter()
    limiter.reset()

    client = TestClient(app)
    headers = {"X-User-ID": "test_emergency_user"}

    # Repeated emergency stop queries must all succeed (never 429)
    for _ in range(25):
        res = client.get("/api/v1/security/emergency-stop", headers=headers)
        assert res.status_code != status.HTTP_429_TOO_MANY_REQUESTS

    limiter.reset()
