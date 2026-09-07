"""Tests for the health check endpoint."""

from fastapi import status
from fastapi.testclient import TestClient


def test_health_check_status_code(client: TestClient) -> None:
    """Ensure GET /health returns 200 OK."""
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK


def test_health_check_payload(client: TestClient) -> None:
    """Ensure GET /health returns expected schema and fields."""
    response = client.get("/health")
    data = response.json()

    assert data["status"] == "healthy"
    assert data["app"] == "Kairo"
    assert "version" in data
    assert "environment" in data
