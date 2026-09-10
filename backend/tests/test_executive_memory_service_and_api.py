"""Test suite for ExecutiveMemoryService orchestration and FastAPI REST endpoints (Task 53)."""

from datetime import UTC, datetime
import pytest
from httpx import ASGITransport, AsyncClient

from app.executive_memory.schemas import (
    BlockerStatus,
    ExecutiveStateScope,
    OpenLoopStatus,
    TimelineEventType,
)
from app.executive_memory.service import ExecutiveMemoryService, executive_memory_service
from app.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


def test_executive_memory_service_orchestration():
    """Verify ExecutiveMemoryService coordinates events, loops, blockers, reconstruction, and queries."""
    svc = ExecutiveMemoryService()

    # 1. Record Timeline Event
    ev = svc.record_timeline_event(
        event_type=TimelineEventType.CREATED,
        source="projects",
        description_reference="Service orchestration initialized",
        project_id="proj_orch",
    )
    assert ev.event_id is not None
    assert ev.event_type == TimelineEventType.CREATED

    # 2. Create Open Loop
    loop = svc.create_open_loop(
        description="Verify edge cases in state synthesis",
        owner="kairo",
        source="testing",
        project_id="proj_orch",
    )
    assert loop.status == OpenLoopStatus.OPEN

    # 3. Create Blocker with evidence
    blocker = svc.create_blocker(
        description="Missing test runner binary",
        affected_tasks=["task_test"],
        source="os_system",
        causality_evidence="Exit code 127: pytest not in PATH",
        project_id="proj_orch",
    )
    assert blocker.status == BlockerStatus.ACTIVE

    # 4. Canonical Continuity Query
    ans = svc.answer_continuity_query(
        question_type="WHAT_WERE_WE_DOING",
        project_id="proj_orch",
    )
    assert "Service orchestration initialized" in ans.answer

    # 5. Resolve Blocker and Close Loop
    resolved = svc.resolve_blocker(blocker.blocker_id, resolution_evidence="Installed pytest in virtual environment")
    assert resolved.status == BlockerStatus.RESOLVED

    closed = svc.close_open_loop(loop.loop_id, evidence="All edge cases tested")
    assert closed.status == OpenLoopStatus.COMPLETED


@pytest.mark.anyio
async def test_executive_memory_api_endpoints(client: AsyncClient):
    """Test all FastAPI endpoints under /api/v1/executive-memory/."""

    # 1. POST /query
    q_resp = await client.post(
        "/api/v1/executive-memory/query",
        json={"question_type": "WHAT_IS_HAPPENING", "project_id": "api_proj"},
    )
    assert q_resp.status_code == 200
    assert "answer" in q_resp.json()

    # 2. POST /timeline/events
    ev_resp = await client.post(
        "/api/v1/executive-memory/timeline/events",
        json={
            "event_type": "STARTED",
            "source": "api_test",
            "description_reference": "API test run initiated",
            "project_id": "api_proj",
        },
    )
    assert ev_resp.status_code == 201
    ev_data = ev_resp.json()
    assert ev_data["event_type"] == "STARTED"

    # 3. GET /timeline
    tl_resp = await client.get("/api/v1/executive-memory/timeline", params={"project_id": "api_proj"})
    assert tl_resp.status_code == 200
    assert len(tl_resp.json()) >= 1

    # 4. POST /open-loops
    loop_resp = await client.post(
        "/api/v1/executive-memory/open-loops",
        json={
            "description": "API open loop tracking test",
            "owner": "test_user",
            "project_id": "api_proj",
        },
    )
    assert loop_resp.status_code == 201
    loop_id = loop_resp.json()["loop_id"]

    # 5. GET /open-loops
    list_loops = await client.get("/api/v1/executive-memory/open-loops", params={"project_id": "api_proj"})
    assert list_loops.status_code == 200
    assert any(l["loop_id"] == loop_id for l in list_loops.json())

    # 6. POST /open-loops/{id}/close
    close_resp = await client.post(
        f"/api/v1/executive-memory/open-loops/{loop_id}/close",
        json={"evidence": "API test loop verified and closed"},
    )
    assert close_resp.status_code == 200
    assert close_resp.json()["status"] == "COMPLETED"

    # 7. POST /blockers
    blk_resp = await client.post(
        "/api/v1/executive-memory/blockers",
        json={
            "description": "Database connection pool exhausted",
            "affected_tasks": ["task_db"],
            "source": "database",
            "severity": "HIGH",
            "causality_evidence": "FATAL: remaining connection slots are reserved for non-replication superuser connections",
            "project_id": "api_proj",
        },
    )
    assert blk_resp.status_code == 201
    blk_id = blk_resp.json()["blocker_id"]

    # 8. POST /blockers/{id}/resolve
    res_blk = await client.post(
        f"/api/v1/executive-memory/blockers/{blk_id}/resolve",
        json={"resolution_evidence": "Increased max_connections to 200 and restarted service"},
    )
    assert res_blk.status_code == 200
    assert res_blk.json()["status"] == "RESOLVED"

    # 9. POST /briefs/{project_id}
    brief_resp = await client.post(
        "/api/v1/executive-memory/briefs/api_proj",
        json={
            "current_status": "API endpoints verified and green",
            "recent_progress": [{"summary": "Executed integration tests"}],
        },
    )
    assert brief_resp.status_code == 200
    assert brief_resp.json()["current_status"] == "API endpoints verified and green"

    # 10. GET /briefs/{project_id}
    get_brief = await client.get("/api/v1/executive-memory/briefs/api_proj")
    assert get_brief.status_code == 200
    assert get_brief.json()["current_status"] == "API endpoints verified and green"

    # 11. GET /metrics
    metrics_resp = await client.get("/api/v1/executive-memory/metrics")
    assert metrics_resp.status_code == 200
    assert "false_continuity_rate" in metrics_resp.json()
