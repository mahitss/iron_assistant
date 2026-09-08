"""Tests for /health, /health/live, /health/ready, and /metrics observability endpoints."""

from unittest.mock import MagicMock

from fastapi import status
from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint():
    """GET /health returns 200 and basic application metadata."""
    client = TestClient(app)

    res = client.get("/health")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["status"] == "healthy"
    assert data["app"] == "Kairo"
    assert "version" in data


def test_health_live_endpoint():
    """GET /health/live indicates the process is executing."""
    client = TestClient(app)

    res = client.get("/health/live")
    assert res.status_code == status.HTTP_200_OK
    assert res.json() == {"status": "alive"}


def test_health_ready_success_when_unconfigured():
    """GET /health/ready returns 200 when databases are unconfigured or active."""
    client = TestClient(app)

    res = client.get("/health/ready")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["status"] == "ready"
    assert "components" in data


def test_health_ready_degraded_when_database_fails(monkeypatch):
    """GET /health/ready returns 503 without exposing credentials when database check fails."""
    from app.config.settings import get_settings
    from app.observability import health

    # Simulate configured database
    cfg = get_settings()
    monkeypatch.setattr(cfg, "DATABASE_URL", "postgresql+asyncpg://usr:secret_pwd@localhost:5432/db")

    # Simulate broken database connection
    def _mock_sessionmaker():
        mock_sm = MagicMock()
        mock_sm.return_value.__aenter__.side_effect = ConnectionRefusedError(
            "Connection refused to postgres:5432"
        )
        return mock_sm

    monkeypatch.setattr(health, "get_sessionmaker", _mock_sessionmaker)

    client = TestClient(app)
    res = client.get("/health/ready")

    assert res.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    data = res.json()
    assert data["status"] == "degraded"
    assert data["components"]["database"] == "failed"
    # Never expose credentials in health responses
    assert "secret_pwd" not in str(data)


def test_metrics_endpoint():
    """GET /metrics returns 200 and Prometheus text format."""
    client = TestClient(app)

    res = client.get("/metrics")
    assert res.status_code == status.HTTP_200_OK
    assert "text/plain" in res.headers["content-type"]
