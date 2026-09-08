"""Integration tests for Automations REST API and cross-user isolation."""

import asyncio

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base, get_db_session
from app.main import app


@pytest.fixture
def sqlite_automations_app():
    """Setup app with in-memory SQLite database session override."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

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


def test_automations_crud_and_cross_user_isolation(sqlite_automations_app):
    """Verify workflow creation, listing, updating, deletion, and user isolation."""
    client = TestClient(app)

    user_a_headers = {"X-User-ID": "user_alice"}
    user_b_headers = {"X-User-ID": "user_bob"}

    # 1. User Alice creates a workflow
    payload = {
        "name": "Alice CI Workflow",
        "description": "Checks CI status",
        "enabled": True,
        "trigger": {
            "trigger_type": "schedule",
            "interval": "daily",
            "time": "09:00",
            "timezone": "UTC",
        },
        "actions": {
            "steps": [
                {
                    "type": "action",
                    "config": {"tool": "datetime", "arguments": {}},
                }
            ]
        },
    }
    res = client.post("/api/v1/automations", json=payload, headers=user_a_headers)
    assert res.status_code == status.HTTP_201_CREATED
    wf_data = res.json()
    wf_id = wf_data["id"]
    assert wf_data["name"] == "Alice CI Workflow"
    assert wf_data["user_id"] == "user_alice"

    # 2. User Alice lists her workflows
    res_list_a = client.get("/api/v1/automations", headers=user_a_headers)
    assert res_list_a.status_code == status.HTTP_200_OK
    assert len(res_list_a.json()) == 1

    # 3. User Bob lists workflows -> should be empty
    res_list_b = client.get("/api/v1/automations", headers=user_b_headers)
    assert res_list_b.status_code == status.HTTP_200_OK
    assert len(res_list_b.json()) == 0

    # 4. User Bob tries to get Alice's workflow -> 403 Forbidden
    res_get_b = client.get(f"/api/v1/automations/{wf_id}", headers=user_b_headers)
    assert res_get_b.status_code == status.HTTP_403_FORBIDDEN

    # 5. User Bob tries to update Alice's workflow -> 403 Forbidden
    res_patch_b = client.patch(
        f"/api/v1/automations/{wf_id}", json={"name": "Hacked"}, headers=user_b_headers
    )
    assert res_patch_b.status_code == status.HTTP_403_FORBIDDEN

    # 6. User Alice updates her workflow
    res_patch_a = client.patch(
        f"/api/v1/automations/{wf_id}", json={"enabled": False}, headers=user_a_headers
    )
    assert res_patch_a.status_code == status.HTTP_200_OK
    assert res_patch_a.json()["enabled"] is False

    # 7. User Alice triggers a manual run
    res_run = client.post(f"/api/v1/automations/{wf_id}/run", headers=user_a_headers)
    assert res_run.status_code == status.HTTP_202_ACCEPTED
    run_data = res_run.json()
    assert run_data["workflow_id"] == wf_id
    run_id = run_data["id"]

    # 8. User Alice inspects runs
    res_runs = client.get(f"/api/v1/automations/{wf_id}/runs", headers=user_a_headers)
    assert res_runs.status_code == status.HTTP_200_OK
    assert len(res_runs.json()) >= 1

    # 9. User Bob tries to inspect Alice's run -> 403 Forbidden
    res_run_b = client.get(f"/api/v1/automations/runs/{run_id}", headers=user_b_headers)
    assert res_run_b.status_code == status.HTTP_403_FORBIDDEN

    # 10. User Alice deletes her workflow
    res_del = client.delete(f"/api/v1/automations/{wf_id}", headers=user_a_headers)
    assert res_del.status_code == status.HTTP_204_NO_CONTENT
