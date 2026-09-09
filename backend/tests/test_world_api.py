"""Integration tests for World Model FastAPI REST API endpoints (Task 32, Spec 120, 121)."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base, get_db_session
from app.main import create_app
from app.world.entities import EntityType, WorldEntityCreateRequest
from app.world.model import get_world_model
from app.world.relationships import RelationshipType, WorldRelationshipCreateRequest


@pytest.fixture
async def app_and_client():
    """Create test application with in-memory database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    app = create_app()

    async def override_get_db():
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, async_session

    await engine.dispose()


@pytest.mark.asyncio
async def test_get_world_overview_endpoint(app_and_client):
    """Verify GET /api/v1/world returns status and aggregate metrics (Spec 120)."""
    client, _ = app_and_client
    headers = {"x-user-id": "user_api_test"}

    resp = await client.get("/api/v1/world", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "projects_count" in data["data"]
    assert "connected_devices_count" in data["data"]


@pytest.mark.asyncio
async def test_world_entity_and_dependencies_api(app_and_client):
    """Verify entity retrieval and dependency extraction via REST API (Spec 120)."""
    client, _ = app_and_client
    headers = {"x-user-id": "user_api_test"}
    model = get_world_model()

    # Seed entities into model
    e1 = await model.upsert_entity(
        request=WorldEntityCreateRequest(
            type=EntityType.SERVICE,
            name="web-gateway",
            project_id="p1",
            source="observability",
            source_id="svc_gateway",
            state="HEALTHY",
        ),
        owner_id="user_api_test",
    )

    e2 = await model.upsert_entity(
        request=WorldEntityCreateRequest(
            type=EntityType.SERVICE,
            name="auth-db",
            project_id="p1",
            source="observability",
            source_id="svc_auth_db",
            state="HEALTHY",
        ),
        owner_id="user_api_test",
    )

    await model.add_relationship(
        request=WorldRelationshipCreateRequest(
            source_entity_id=e1.id,
            target_entity_id=e2.id,
            relationship_type=RelationshipType.DEPENDS_ON,
        ),
        owner_id="user_api_test",
    )

    # 1. Get single entity
    resp1 = await client.get(f"/api/v1/world/entities/{e1.id}", headers=headers)
    assert resp1.status_code == 200
    assert resp1.json()["data"]["name"] == "web-gateway"

    # 2. Get dependencies
    resp2 = await client.get(f"/api/v1/world/entities/{e1.id}/dependencies", headers=headers)
    assert resp2.status_code == 200
    dep_data = resp2.json()["data"]
    assert len(dep_data["dependencies"]) == 1
    assert dep_data["dependencies"][0]["id"] == e2.id


@pytest.mark.asyncio
async def test_world_changes_and_refresh_api(app_and_client):
    """Verify GET /api/v1/world/changes and POST /api/v1/world/refresh (Spec 95, 98, 120)."""
    client, _ = app_and_client
    headers = {"x-user-id": "user_api_test"}

    # Query changes
    changes_resp = await client.get("/api/v1/world/changes?since_seconds=3600", headers=headers)
    assert changes_resp.status_code == 200
    assert changes_resp.json()["status"] == "success"

    # Trigger refresh
    refresh_resp = await client.post("/api/v1/world/refresh", headers=headers)
    assert refresh_resp.status_code == 200
    assert refresh_resp.json()["status"] == "success"


@pytest.mark.asyncio
async def test_world_snapshot_and_health_api(app_and_client):
    """Verify snapshot creation and operational health endpoints (Spec 36, 91, 120)."""
    client, _ = app_and_client
    headers = {"x-user-id": "user_api_test"}

    # Create snapshot
    snap_resp = await client.post("/api/v1/world/snapshots", headers=headers)
    assert snap_resp.status_code == 200
    assert "snapshot_id" in snap_resp.json()

    # Health telemetry
    health_resp = await client.get("/api/v1/world/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["data"]["status"] in ("HEALTHY", "DEGRADED")
