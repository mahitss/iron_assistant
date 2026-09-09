"""Integration tests for Experience & Feedback REST API routes and tenant isolation (Sections 33, 34, 40, 86, 87, 88)."""

import asyncio
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base, get_db_session
from app.main import app


@pytest.fixture
def sqlite_experience_app():
    """Setup app with in-memory SQLite database session override for experience tests."""
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
    yield session_factory
    app.dependency_overrides.pop(get_db_session, None)
    asyncio.run(engine.dispose())


def test_feedback_api_lifecycle_and_tenant_isolation(sqlite_experience_app):
    """Sections 33, 34, 88: User A cannot view User B feedback."""
    client = TestClient(app)
    headers_user_a = {"X-User-ID": "user_a"}
    headers_user_b = {"X-User-ID": "user_b"}

    # 1. User A submits feedback
    fb_payload = {
        "feedback_type": "POSITIVE",
        "session_id": "sess_101",
        "message_id": "msg_001",
        "rating": 5,
        "comment": "Great accurate response on docker compose",
    }
    res_a = client.post("/api/v1/feedback", json=fb_payload, headers=headers_user_a)
    assert res_a.status_code == status.HTTP_201_CREATED
    data_a = res_a.json()
    assert data_a["user_id"] == "user_a"
    assert data_a["rating"] == 5
    fb_id = data_a["id"]

    # 2. User A can retrieve their feedback
    res_list_a = client.get("/api/v1/feedback", headers=headers_user_a)
    assert res_list_a.status_code == status.HTTP_200_OK
    assert len(res_list_a.json()) == 1

    # 3. User B cannot see User A's feedback in list
    res_list_b = client.get("/api/v1/feedback", headers=headers_user_b)
    assert res_list_b.status_code == status.HTTP_200_OK
    assert len(res_list_b.json()) == 0

    # 4. User B cannot access User A's feedback detail (Section 34: 403 Forbidden)
    res_detail_b = client.get(f"/api/v1/feedback/{fb_id}", headers=headers_user_b)
    assert res_detail_b.status_code == status.HTTP_403_FORBIDDEN


def test_experience_corrections_and_preferences_api(sqlite_experience_app):
    """Sections 7, 8, 30, 41, 86: Corrections and preferences API with safety guards."""
    client = TestClient(app)
    headers = {"X-User-ID": "dev_user"}

    # 1. Create explicit correction
    corr_payload = {
        "summary": "Use SQLite for test runs",
        "correction": "For test runs, always use SQLite in-memory",
        "project_id": "proj_kairo",
        "scope": "PROJECT",
    }
    res_corr = client.post("/api/v1/experience/corrections", json=corr_payload, headers=headers)
    assert res_corr.status_code == status.HTTP_201_CREATED
    data_corr = res_corr.json()
    assert data_corr["type"] == "USER_CORRECTION"
    assert data_corr["scope"] == "PROJECT"
    exp_id = data_corr["id"]

    # 2. Retrieve experience detail
    res_detail = client.get(f"/api/v1/experience/{exp_id}", headers=headers)
    assert res_detail.status_code == status.HTTP_200_OK
    assert res_detail.json()["id"] == exp_id

    # 3. Create valid preference
    pref_payload = {
        "key": "preferred_compiler",
        "value": "clang",
        "scope": "USER",
    }
    res_pref = client.post("/api/v1/experience/preferences", json=pref_payload, headers=headers)
    assert res_pref.status_code == status.HTTP_201_CREATED
    assert res_pref.json()["key"] == "preferred_compiler"

    # 4. Attempt to mutate governance domain via preferences (should fail 403)
    bad_sec_payload = {
        "key": "security_center_bypass",
        "value": "enabled",
        "scope": "USER",
    }
    res_bad_sec = client.post("/api/v1/experience/preferences", json=bad_sec_payload, headers=headers)
    assert res_bad_sec.status_code == status.HTTP_403_FORBIDDEN

    # 5. Attempt sensitive profiling via preferences (should fail 422)
    bad_prof_payload = {
        "key": "political_affiliation",
        "value": "independent",
        "scope": "USER",
    }
    res_bad_prof = client.post("/api/v1/experience/preferences", json=bad_prof_payload, headers=headers)
    assert res_bad_prof.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_experience_export_api(sqlite_experience_app):
    """Section 40: Structured export API."""
    client = TestClient(app)
    headers = {"X-User-ID": "export_user"}

    # Add a correction
    client.post(
        "/api/v1/experience/corrections",
        json={"summary": "Use Python 3.12", "correction": "Python 3.12"},
        headers=headers,
    )

    res = client.get("/api/v1/experience/export", headers=headers)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["user_id"] == "export_user"
    assert "experiences" in data
    assert "preferences" in data
    assert len(data["experiences"]) >= 1
