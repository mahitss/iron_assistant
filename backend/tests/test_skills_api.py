"""Tests for Skills REST API routes, discovery, health, execution, and toggling."""

import pytest
from app.main import app
from fastapi import status
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    """Provide a TestClient for Kairo FastAPI app."""
    return TestClient(app)


def test_api_list_skills(client: TestClient) -> None:
    """Ensure GET /api/v1/skills lists canonical skills with summary fields."""
    response = client.get("/api/v1/skills", headers={"X-User-ID": "user_api_test"})
    assert response.status_code == status.HTTP_200_OK
    skills = response.json()
    assert isinstance(skills, list)
    assert len(skills) >= 11

    # Check structure of summary items
    sample = skills[0]
    assert "id" in sample
    assert "name" in sample
    assert "version" in sample
    assert "category" in sample
    assert "risk_level" in sample
    assert "health_status" in sample
    assert "enabled" in sample


def test_api_get_skill_detail(client: TestClient) -> None:
    """Ensure GET /api/v1/skills/{skill_id} returns detail for known skill."""
    response = client.get("/api/v1/skills/research.web", headers={"X-User-ID": "user_api_test"})
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == "research.web"
    assert data["name"] == "Web Research"
    assert data["version"] == "1.0.0"
    assert "capabilities" in data
    assert "required_tools" in data
    assert "required_permissions" in data


def test_api_get_skill_not_found(client: TestClient) -> None:
    """Ensure GET /api/v1/skills/{skill_id} returns 404 for unknown skill ID."""
    response = client.get("/api/v1/skills/unknown.nonexistent", headers={"X-User-ID": "user_api_test"})
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_api_get_skill_health(client: TestClient) -> None:
    """Ensure GET /api/v1/skills/{skill_id}/health returns health and tool readiness."""
    response = client.get("/api/v1/skills/research.web/health", headers={"X-User-ID": "user_api_test"})
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["skill_id"] == "research.web"
    assert "health_status" in data
    assert "ready" in data


def test_api_toggle_skill(client: TestClient) -> None:
    """Ensure POST /api/v1/skills/{skill_id}/toggle enables/disables skill."""
    # Toggle off
    res_off = client.post(
        "/api/v1/skills/research.web/toggle",
        json={"enabled": False},
        headers={"X-User-ID": "user_api_test"},
    )
    assert res_off.status_code == status.HTTP_200_OK
    assert res_off.json()["enabled"] is False

    # Toggle back on
    res_on = client.post(
        "/api/v1/skills/research.web/toggle",
        json={"enabled": True},
        headers={"X-User-ID": "user_api_test"},
    )
    assert res_on.status_code == status.HTTP_200_OK
    assert res_on.json()["enabled"] is True


def test_api_execute_skill(client: TestClient) -> None:
    """Ensure POST /api/v1/skills/{skill_id}/execute executes or initiates execution."""
    payload = {
        "inputs": {"query": "Modern Python APIs"},
        "context": {},
    }
    response = client.post(
        "/api/v1/skills/research.web/execute",
        json=payload,
        headers={"X-User-ID": "user_api_test"},
    )
    assert response.status_code in (status.HTTP_200_OK, status.HTTP_202_ACCEPTED)
    data = response.json()
    assert "execution_id" in data
    assert "state" in data
