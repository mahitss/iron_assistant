"""Tests for Knowledge Fabric REST API routes, auth scoping, and IDOR prevention."""

import asyncio
import io

import pytest
from app.db.session import Base, get_db_session
from app.main import app
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.fixture
def sqlite_knowledge_app():
    """Setup app with in-memory SQLite database session override for knowledge tests."""
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


def test_decisions_api_lifecycle(sqlite_knowledge_app):
    """Verify decision recording, retrieval, and supersession via REST API."""
    client = TestClient(app)
    headers = {"X-User-ID": "user_api_1"}

    # 1. Create Decision
    dec_payload = {
        "decision": "Use FastAPI for REST API backend",
        "rationale": "High performance async python framework with auto OpenAPI documentation.",
        "project_id": "proj_kairo",
    }
    res = client.post("/api/v1/knowledge/decisions", json=dec_payload, headers=headers)
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()
    assert data["decision"] == "Use FastAPI for REST API backend"
    assert data["status"] == "ACTIVE"
    dec_id = data["id"]

    # 2. List Decisions
    res_list = client.get("/api/v1/knowledge/decisions?project_id=proj_kairo", headers=headers)
    assert res_list.status_code == status.HTTP_200_OK
    items = res_list.json()
    assert len(items) == 1
    assert items[0]["id"] == dec_id

    # 3. Supersede Decision
    super_payload = {
        "new_decision": "Use FastAPI with uvloop and Pydantic v2",
        "reason": "Performance benchmark optimization.",
    }
    res_super = client.post(
        f"/api/v1/knowledge/decisions/{dec_id}/supersede",
        json=super_payload,
        headers=headers,
    )
    assert res_super.status_code == status.HTTP_200_OK
    super_data = res_super.json()
    assert super_data["decision"] == "Use FastAPI with uvloop and Pydantic v2"

    # Verify listing reflects active and superseded decisions
    res_list2 = client.get("/api/v1/knowledge/decisions", headers=headers)
    assert res_list2.status_code == status.HTTP_200_OK
    items2 = res_list2.json()
    assert len(items2) == 2


def test_document_upload_and_search_api(sqlite_knowledge_app):
    """Verify document upload, chunking, and subsequent hybrid search via REST API."""
    client = TestClient(app)
    headers = {"X-User-ID": "user_api_2"}

    # 1. Upload Markdown file
    file_content = (
        b"# Kairo Knowledge Fabric\n\n"
        b"The knowledge fabric connects projects, repositories, and decisions into a graph.\n\n"
        b"## Security Model\n\n"
        b"Multi-tenant isolation is enforced at query time.\n"
    )
    files = {
        "file": ("knowledge_spec.md", io.BytesIO(file_content), "text/markdown"),
    }
    data = {"project_id": "proj_spec"}

    res = client.post("/api/v1/knowledge/documents/upload", files=files, data=data, headers=headers)
    assert res.status_code == status.HTTP_201_CREATED
    upload_res = res.json()
    assert upload_res["filename"] == "knowledge_spec.md"
    assert upload_res["chunks_created"] >= 1
    doc_node_id = upload_res["document_id"]

    # 2. Search Knowledge API
    search_res = client.get("/api/v1/knowledge/search?q=security+isolation+graph", headers=headers)
    assert search_res.status_code == status.HTTP_200_OK
    search_data = search_res.json()
    assert search_data["total_matches"] >= 1
    assert any("knowledge" in item["title"].lower() for item in search_data["results"])

    # 3. Fetch Node Detail
    node_res = client.get(f"/api/v1/knowledge/{doc_node_id}", headers=headers)
    assert node_res.status_code == status.HTTP_200_OK
    assert node_res.json()["title"] == "knowledge_spec.md"

    # 4. IDOR Check: User 3 cannot fetch User 2's document node
    headers_user3 = {"X-User-ID": "user_api_3"}
    forbidden_res = client.get(f"/api/v1/knowledge/{doc_node_id}", headers=headers_user3)
    assert forbidden_res.status_code == status.HTTP_404_NOT_FOUND


def test_timeline_and_backfill_api(sqlite_knowledge_app):
    """Verify timeline generation and backfill triggers."""
    client = TestClient(app)
    headers = {"X-User-ID": "user_api_4"}

    # Trigger backfill (idempotent, safe on empty DB)
    bf_res = client.post("/api/v1/knowledge/backfill", headers=headers)
    assert bf_res.status_code == status.HTTP_200_OK
    assert "total_indexed" in bf_res.json()

    # Timeline fetch
    tl_res = client.get("/api/v1/knowledge/timeline", headers=headers)
    assert tl_res.status_code == status.HTTP_200_OK
    assert "events" in tl_res.json()
