"""API integration tests for Project CRUD and resource associations."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.api.routes.projects import get_project_service
from app.context.schemas import ProjectResponse, ProjectStatus
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_overrides():
    yield
    app.dependency_overrides.clear()


# --- 1. Project Creation, Retrieval, and Lifecycle ---


def test_project_crud_lifecycle(client):
    """Verify creating, reading, updating, and deleting a project via REST API."""
    mock_proj = ProjectResponse(
        id="proj-1234",
        user_id="user_alice",
        name="Kairo Project",
        description="Autonomous Assistant",
        status=ProjectStatus.ACTIVE,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        last_active_at=datetime.now(UTC),
        repositories=[],
        workflows=[],
        conversations=[],
    )

    mock_service = AsyncMock()
    mock_service.create_project = AsyncMock(return_value=mock_proj)
    mock_service.get_project = AsyncMock(return_value=mock_proj)
    mock_service.list_projects = AsyncMock(return_value=[mock_proj])
    mock_service.update_project = AsyncMock(
        return_value=mock_proj.model_copy(update={"status": ProjectStatus.PAUSED})
    )
    mock_service.delete_project = AsyncMock(return_value=True)

    app.dependency_overrides[get_project_service] = lambda: mock_service

    # 1. Create Project
    resp = client.post(
        "/api/v1/projects",
        json={"name": "Kairo Project", "description": "Autonomous Assistant"},
        headers={"x-user-id": "user_alice"},
    )
    assert resp.status_code == status.HTTP_201_CREATED
    data = resp.json()
    assert data["name"] == "Kairo Project"
    assert data["status"] == "ACTIVE"

    # 2. List Projects
    resp_list = client.get("/api/v1/projects", headers={"x-user-id": "user_alice"})
    assert resp_list.status_code == status.HTTP_200_OK
    assert len(resp_list.json()) == 1

    # 3. Get Project by ID
    resp_get = client.get("/api/v1/projects/proj-1234", headers={"x-user-id": "user_alice"})
    assert resp_get.status_code == status.HTTP_200_OK
    assert resp_get.json()["id"] == "proj-1234"

    # 4. Update Project Status
    resp_patch = client.patch(
        "/api/v1/projects/proj-1234",
        json={"status": "PAUSED"},
        headers={"x-user-id": "user_alice"},
    )
    assert resp_patch.status_code == status.HTTP_200_OK
    assert resp_patch.json()["status"] == "PAUSED"

    # 5. Delete Project
    resp_del = client.delete("/api/v1/projects/proj-1234", headers={"x-user-id": "user_alice"})
    assert resp_del.status_code == status.HTTP_204_NO_CONTENT


# --- 2. Resource Linking (Repositories & Workflows) ---


def test_project_resource_linking(client):
    """Verify linking repositories and workflows to an existing project."""
    mock_service = AsyncMock()
    mock_service.link_repository = AsyncMock(return_value=True)
    mock_service.link_workflow = AsyncMock(return_value=True)

    app.dependency_overrides[get_project_service] = lambda: mock_service

    # Link Repository
    resp_repo = client.post(
        "/api/v1/projects/proj-1234/repositories",
        json={"repository_path": "mahitss/iron_assistant", "is_primary": True},
        headers={"x-user-id": "user_alice"},
    )
    assert resp_repo.status_code == status.HTTP_201_CREATED
    assert resp_repo.json()["status"] == "linked"

    # Link Workflow
    resp_wf = client.post(
        "/api/v1/projects/proj-1234/workflows",
        json={"workflow_id": "wf-ci-monitor"},
        headers={"x-user-id": "user_alice"},
    )
    assert resp_wf.status_code == status.HTTP_201_CREATED
    assert resp_wf.json()["status"] == "linked"


# --- 3. Cross-User Ownership Enforcement ---


def test_project_ownership_isolation(client):
    """Verify users cannot access or modify projects owned by other users."""
    mock_service = AsyncMock()
    # User Bob attempting to access Alice's project returns None / 404
    mock_service.get_project = AsyncMock(return_value=None)
    mock_service.delete_project = AsyncMock(return_value=False)

    app.dependency_overrides[get_project_service] = lambda: mock_service

    resp_get = client.get("/api/v1/projects/proj-alice", headers={"x-user-id": "user_bob"})
    assert resp_get.status_code == status.HTTP_404_NOT_FOUND

    resp_del = client.delete("/api/v1/projects/proj-alice", headers={"x-user-id": "user_bob"})
    assert resp_del.status_code == status.HTTP_404_NOT_FOUND
