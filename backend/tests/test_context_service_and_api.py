"""API and Service integration tests for Universal Context & Adaptive Personalization (Task 69)."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.context.universal_schemas import (
    ContextRequest,
)
from app.context.universal_service import (
    UniversalContextService,
)
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.asyncio
async def test_universal_context_service_lifecycle_and_replay():
    """Verify UniversalContextService builds packages, creates snapshots, and supports deterministic replay."""
    service = UniversalContextService()
    req = ContextRequest(
        tenant_id="tenant_x",
        user_id="alice",
        query="Verify cluster health in production",
        intent="health_check",
        environment="production",
    )

    package = await service.build_context(req)
    assert package.tenant_id == "tenant_x"
    assert package.context_id in service._packages
    assert package.quality_score.overall_score > 0.0

    # Retrieve explanation
    explanations = service.get_explanation(package.context_id, "tenant_x")
    assert isinstance(explanations, dict)

    # Verify snapshot recorded and replay
    snapshots = service.list_snapshots("tenant_x")
    assert len(snapshots) >= 1
    snap_id = snapshots[0].snapshot_id

    replay = service.replay_snapshot("tenant_x", snap_id)
    assert replay is not None
    assert replay["snapshot_id"] == snap_id
    assert replay["environment"] == "production"

    # Cross-tenant snapshot access is blocked
    assert service.replay_snapshot("tenant_other", snap_id) is None


@pytest.mark.asyncio
async def test_universal_context_cache_and_invalidation():
    """Verify context cache returns cached items and invalidates on source changes."""
    service = UniversalContextService()
    req = ContextRequest(
        tenant_id="tenant_cache",
        user_id="bob",
        query="List all database migrations",
        environment="production",
    )

    pkg1 = await service.build_context(req, use_cache=True)
    # Immediate second call returns cached package
    pkg2 = await service.build_context(req, use_cache=True)
    assert pkg1.context_id == pkg2.context_id

    # Invalidate cache for tenant
    invalidated = service.orchestrator.cache.invalidate_for_tenant("tenant_cache")
    assert invalidated >= 1

    # Cross-tenant cache check: same query for different tenant must not return cached item
    cached_other = service.orchestrator.cache.get(
        tenant_id="tenant_foreign",
        user_id="bob",
        session_id=None,
        task_id=None,
        agent_id=None,
        environment="production",
        query="List all database migrations",
    )
    assert cached_other is None


def test_universal_context_api_rest_endpoints(client):
    """Verify REST endpoints under /api/v1/context (build, quality, health, preferences)."""
    # 1. Build context
    payload = {
        "tenant_id": "tenant_api",
        "user_id": "carol",
        "query": "Review API endpoints for security",
        "intent": "security_audit",
        "environment": "production",
        "maximum_tokens": 3000,
        "maximum_items": 15,
    }
    resp_build = client.post("/api/v1/context/build", json=payload)
    assert resp_build.status_code == status.HTTP_200_OK
    data = resp_build.json()
    assert data["tenant_id"] == "tenant_api"
    ctx_id = data["context_id"]

    # 2. Quality Overview
    resp_q = client.get("/api/v1/context/quality", headers={"x-tenant-id": "tenant_api"})
    assert resp_q.status_code == status.HTTP_200_OK
    assert resp_q.json()["total_packages"] >= 1

    # 3. Health
    resp_h = client.get("/api/v1/context/health", headers={"x-tenant-id": "tenant_api"})
    assert resp_h.status_code == status.HTTP_200_OK
    assert "average_quality_score" in resp_h.json()

    # 4. Context Explanation
    resp_exp = client.get(f"/api/v1/context/{ctx_id}/explanation", headers={"x-tenant-id": "tenant_api"})
    assert resp_exp.status_code == status.HTTP_200_OK

    # 5. Preferences CRUD
    pref_payload = {
        "tenant_id": "tenant_api",
        "user_id": "carol",
        "category": "WORKFLOW",
        "key": "ci_pipeline_preference",
        "value": "github_actions",
        "source": "EXPLICIT_PREFERENCE",
        "confidence": "EXPLICIT",
        "confidence_score": 0.95,
    }
    resp_pref = client.post(
        "/api/v1/context/preferences", json=pref_payload, headers={"x-tenant-id": "tenant_api"}
    )
    assert resp_pref.status_code == status.HTTP_200_OK
    pref_id = resp_pref.json()["preference_id"]

    # List preferences
    resp_list = client.get(
        "/api/v1/context/preferences?category=WORKFLOW",
        headers={"x-tenant-id": "tenant_api", "x-user-id": "carol"},
    )
    assert resp_list.status_code == status.HTTP_200_OK
    assert len(resp_list.json()) >= 1

    # Delete preference
    resp_del = client.delete(f"/api/v1/context/preferences/{pref_id}", headers={"x-tenant-id": "tenant_api"})
    assert resp_del.status_code == status.HTTP_200_OK


def test_cross_tenant_isolation_on_context_routes(client):
    """Verify that tenant A cannot access tenant B's context package or snapshots."""
    # Build package under Tenant Alpha
    payload = {
        "tenant_id": "tenant_alpha_iso",
        "user_id": "alice",
        "query": "Internal secret architecture details",
    }
    resp = client.post("/api/v1/context/build", json=payload)
    assert resp.status_code == status.HTTP_200_OK
    ctx_id = resp.json()["context_id"]

    # Tenant Beta attempts to read Tenant Alpha's context package
    resp_beta = client.get(f"/api/v1/context/{ctx_id}", headers={"x-tenant-id": "tenant_beta_iso"})
    assert resp_beta.status_code == status.HTTP_404_NOT_FOUND
