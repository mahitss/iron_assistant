"""Tests for GET /health/version safe release metadata endpoint."""

from fastapi import status
from fastapi.testclient import TestClient

from app.config.settings import get_settings
from app.main import app


def test_version_endpoint_structure():
    """Verify /health/version returns safe metadata without leaking internal secrets."""
    client = TestClient(app)
    response = client.get("/health/version")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "version" in data
    assert "git_sha" in data
    assert "build_timestamp" in data
    assert "environment" in data

    # Verify zero leakage of credentials, URLs, or environment dumps
    lowered_keys = [k.lower() for k in data.keys()]
    assert "database_url" not in lowered_keys
    assert "secret_key" not in lowered_keys
    assert "openrouter_api_key" not in lowered_keys
    assert "auth_secret_key" not in lowered_keys
    assert "password" not in str(data).lower()


def test_version_endpoint_matches_settings(monkeypatch):
    """Verify /health/version reflects configured settings."""
    settings = get_settings()
    monkeypatch.setattr(settings, "GIT_SHA", "test-sha-12345678")
    monkeypatch.setattr(settings, "BUILD_TIMESTAMP", "2026-09-08T12:00:00Z")

    client = TestClient(app)
    response = client.get("/health/version")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["git_sha"] == "test-sha-12345678"
    assert data["build_timestamp"] == "2026-09-08T12:00:00Z"
