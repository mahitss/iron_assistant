"""Tests for internal memory API routes (/api/v1/internal/memories)."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base, get_db_session
from app.main import app


@pytest.fixture
def sqlite_db_app():
    """Setup app with in-memory SQLite database session override."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    import asyncio
    async def init_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    asyncio.run(init_tables())

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db_session] = override_get_db
    yield
    app.dependency_overrides.pop(get_db_session, None)
    asyncio.run(engine.dispose())


def test_internal_memory_crud_api(client: TestClient, sqlite_db_app):
    """Test full CRUD lifecycle through internal memory endpoints."""
    # 1. Create a memory
    create_payload = {
        "content": "User prefers concise python explanations.",
        "memory_type": "preference",
        "importance": 0.8,
        "source": "unit_test",
    }
    res_create = client.post("/api/v1/internal/memories", json=create_payload)
    assert res_create.status_code == status.HTTP_201_CREATED
    data = res_create.json()
    assert data["content"] == create_payload["content"]
    assert data["memory_type"] == "preference"
    assert data["importance"] == 0.8
    # Verify no embedding vector is exposed in the API response schema
    assert "embedding" not in data
    memory_id = data["id"]

    # 2. Get memory by ID
    res_get = client.get(f"/api/v1/internal/memories/{memory_id}")
    assert res_get.status_code == status.HTTP_200_OK
    assert res_get.json()["id"] == memory_id

    # 3. List memories
    res_list = client.get("/api/v1/internal/memories")
    assert res_list.status_code == status.HTTP_200_OK
    assert len(res_list.json()) >= 1

    # 4. Search memories
    res_search = client.get("/api/v1/internal/memories/search?q=python")
    assert res_search.status_code == status.HTTP_200_OK
    assert isinstance(res_search.json(), list)

    # 5. Update memory
    update_payload = {"importance": 0.95}
    res_update = client.patch(f"/api/v1/internal/memories/{memory_id}", json=update_payload)
    assert res_update.status_code == status.HTTP_200_OK
    assert res_update.json()["importance"] == 0.95

    # 6. Delete memory
    res_delete = client.delete(f"/api/v1/internal/memories/{memory_id}")
    assert res_delete.status_code == status.HTTP_204_NO_CONTENT

    # 7. Verify deletion
    res_after = client.get(f"/api/v1/internal/memories/{memory_id}")
    assert res_after.status_code == status.HTTP_404_NOT_FOUND


def test_internal_memory_rejects_credentials(client: TestClient, sqlite_db_app):
    """Test that creating a memory with secrets is rejected with HTTP 400."""
    bad_payload = {
        "content": "Secret API key is pk_test_sample_token_secret_1234567890abcdef",
        "memory_type": "fact",
    }
    response = client.post("/api/v1/internal/memories", json=bad_payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "sensitive credentials" in response.json()["detail"].lower()
