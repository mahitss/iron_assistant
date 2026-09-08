"""API integration tests for Context Engine and Memory CRUD endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.api.routes.context import get_context_engine
from app.api.routes.memory import get_memory_service
from app.context.schemas import (
    ContextItem,
    ContextPacket,
    ContextSettings,
    ContextType,
    ProjectResponse,
    ProjectStatus,
)
from app.main import app
from app.memory.schemas import MemoryResponse, MemoryType


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_overrides():
    yield
    app.dependency_overrides.clear()


# --- 1. Current Context & Project Context Endpoints ---


def test_context_current_and_project_endpoints(client):
    """Verify /api/v1/context/current and /api/v1/context/projects/{id} endpoints."""
    mock_packet = ContextPacket(
        session_id="sess_123",
        user_id="user_alice",
        active_project=ProjectResponse(
            id="proj_1",
            user_id="user_alice",
            name="Kairo",
            status=ProjectStatus.ACTIVE,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            last_active_at=datetime.now(UTC),
        ),
        items=[
            ContextItem(
                source_type=ContextType.PROJECT_CONTEXT,
                source_id="proj_1",
                title="Project Kairo",
                content="Autonomous AI Assistant",
                relevance_score=0.9,
                confidence=1.0,
            )
        ],
        total_items=1,
    )

    mock_engine = AsyncMock()
    mock_engine.resolve_context = AsyncMock(return_value=mock_packet)
    mock_engine.get_project_context = AsyncMock(return_value=mock_packet)

    app.dependency_overrides[get_context_engine] = lambda: mock_engine

    # 1. Current Context
    resp_cur = client.get("/api/v1/context/current", headers={"x-user-id": "user_alice"})
    assert resp_cur.status_code == status.HTTP_200_OK
    data = resp_cur.json()
    assert data["active_project"]["name"] == "Kairo"
    assert data["total_items"] == 1

    # 2. Project Context
    resp_proj = client.get("/api/v1/context/projects/proj_1", headers={"x-user-id": "user_alice"})
    assert resp_proj.status_code == status.HTTP_200_OK
    assert resp_proj.json()["active_project"]["id"] == "proj_1"


# --- 2. Context Search Endpoint ---


def test_context_search_endpoint(client):
    """Verify /api/v1/context/search hybrid contextual lookup."""
    mock_item = ContextItem(
        source_type=ContextType.MEMORY_CONTEXT,
        source_id="mem_01",
        title="PostgreSQL Tech Stack",
        content="Kairo uses PostgreSQL for conversation persistence",
        relevance_score=0.88,
        confidence=1.0,
    )

    mock_engine = AsyncMock()
    mock_engine.search_context = AsyncMock(return_value=[mock_item])

    app.dependency_overrides[get_context_engine] = lambda: mock_engine

    resp = client.get("/api/v1/context/search?q=database", headers={"x-user-id": "user_alice"})
    assert resp.status_code == status.HTTP_200_OK
    items = resp.json()
    assert len(items) == 1
    assert "PostgreSQL" in items[0]["content"]


# --- 3. Context Personalization Settings Endpoints ---


def test_context_settings_get_and_patch(client):
    """Verify /api/v1/context/settings read and update."""
    mock_settings = ContextSettings(
        user_id="user_alice",
        context_enabled=True,
        memory_enabled=True,
        project_context_enabled=True,
        proactive_context_enabled=True,
    )

    mock_engine = AsyncMock()
    mock_engine.get_user_settings = AsyncMock(return_value=mock_settings)
    mock_engine.update_user_settings = AsyncMock(
        return_value=mock_settings.model_copy(update={"project_context_enabled": False})
    )

    app.dependency_overrides[get_context_engine] = lambda: mock_engine

    # GET settings
    resp_get = client.get("/api/v1/context/settings", headers={"x-user-id": "user_alice"})
    assert resp_get.status_code == status.HTTP_200_OK
    assert resp_get.json()["context_enabled"] is True

    # PATCH settings
    resp_patch = client.patch(
        "/api/v1/context/settings",
        json={"project_context_enabled": False},
        headers={"x-user-id": "user_alice"},
    )
    assert resp_patch.status_code == status.HTTP_200_OK
    assert resp_patch.json()["project_context_enabled"] is False


# --- 4. Memory CRUD Endpoints (/api/v1/memory) ---


def test_memory_crud_api_endpoints(client):
    """Verify user-facing /api/v1/memory CRUD inspection and deletion."""
    mock_mem = MemoryResponse(
        id="mem-uuid-1",
        content="Prefers dark mode and concise responses",
        memory_type=MemoryType.PREFERENCE,
        importance=0.8,
        source="user_explicit",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        last_accessed_at=datetime.now(UTC),
    )

    mock_service = AsyncMock()
    mock_service.list_memories = AsyncMock(return_value=[mock_mem])
    mock_service.get_memory = AsyncMock(return_value=mock_mem)
    mock_service.update_memory = AsyncMock(return_value=mock_mem.model_copy(update={"importance": 0.95}))
    mock_service.delete_memory = AsyncMock(return_value=True)

    app.dependency_overrides[get_memory_service] = lambda: mock_service

    # 1. List memories
    resp_list = client.get("/api/v1/memory")
    assert resp_list.status_code == status.HTTP_200_OK
    assert len(resp_list.json()) == 1

    # 2. Get memory by ID
    resp_get = client.get("/api/v1/memory/mem-uuid-1")
    assert resp_get.status_code == status.HTTP_200_OK
    assert resp_get.json()["id"] == "mem-uuid-1"

    # 3. Patch memory
    resp_patch = client.patch("/api/v1/memory/mem-uuid-1", json={"importance": 0.95})
    assert resp_patch.status_code == status.HTTP_200_OK
    assert resp_patch.json()["importance"] == 0.95

    # 4. Delete memory
    resp_del = client.delete("/api/v1/memory/mem-uuid-1")
    assert resp_del.status_code == status.HTTP_204_NO_CONTENT
