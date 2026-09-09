"""API and Router tests for Kairo Unified Command & Intent layer (Spec 53-56, 122, 123, 154-158)."""

from datetime import UTC, datetime
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base, get_db_session
from app.intent.planner_bridge import CommandRouter
from app.intent.schemas import IntentConstraints, IntentRiskLevel, IntentSchema, IntentType
from app.main import create_app


@pytest.fixture
async def app_and_session():
    """Create test application bound to in-memory async database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_maker() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client, session_maker

    await engine.dispose()


@pytest.mark.asyncio
async def test_submit_command_endpoint(app_and_session):
    """Verify POST /api/v1/commands parses, records, and returns command response (Spec 122)."""
    client, _ = app_and_session

    resp = await client.post(
        "/api/v1/commands",
        headers={"x-user-id": "user_alice"},
        json={
            "text": "Please summarize this document",
            "source_interface": "WEB",
            "attachments": [
                {"type": "document", "name": "architecture.pdf"}
            ],
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert "command_id" in data
    assert data["intent"]["type"] == "SUMMARIZE"
    assert data["intent"]["target"]["name"] == "architecture.pdf"
    assert data["execution_summary"]["subsystem"] == "skills_catalog"


@pytest.mark.asyncio
async def test_resolve_only_endpoint_does_not_execute(app_and_session):
    """Verify POST /api/v1/commands/resolve performs analysis without execution (Spec 123)."""
    client, _ = app_and_session

    resp = await client.post(
        "/api/v1/commands/resolve",
        headers={"x-user-id": "user_alice"},
        json={
            "text": "Deploy to staging if tests pass",
            "source_interface": "WEB",
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"]["type"] in ("TASK", "DEPLOY")
    assert data["intent"]["constraints"]["environment"] == "staging"
    assert data["execution_summary"]["status"] == "RESOLVED_ONLY"
    assert data["execution_summary"]["executed"] is False


@pytest.mark.asyncio
async def test_get_command_by_id_tenant_isolation(app_and_session):
    """Verify GET /api/v1/commands/{id} enforces strict user tenant isolation (Spec 118, 122)."""
    client, _ = app_and_session

    # 1. Alice creates a command
    create_resp = await client.post(
        "/api/v1/commands",
        headers={"x-user-id": "user_alice"},
        json={"text": "Check CI build", "source_interface": "WEB"},
    )
    cmd_id = create_resp.json()["command_id"]

    # 2. Alice retrieves her command
    alice_resp = await client.get(
        f"/api/v1/commands/{cmd_id}",
        headers={"x-user-id": "user_alice"},
    )
    assert alice_resp.status_code == 200
    assert alice_resp.json()["command_id"] == cmd_id
    assert alice_resp.json()["user_id"] == "user_alice"

    # 3. Bob attempts to retrieve Alice's command -> 404 (Not Found / Denied)
    bob_resp = await client.get(
        f"/api/v1/commands/{cmd_id}",
        headers={"x-user-id": "user_bob"},
    )
    assert bob_resp.status_code == 404


@pytest.mark.asyncio
async def test_planner_bridge_routes_to_task_engine():
    """Verify TASK intent is dispatched to Task Engine with constraints (Spec 154)."""
    intent = IntentSchema(
        intent_id="i1",
        source_command_id="c1",
        type=IntentType.TASK,
        objective="Investigate why CI is failing",
        risk=IntentRiskLevel.NORMAL,
        constraints=IntentConstraints(environment="development"),
        status="READY",
    )

    res = await CommandRouter.route_intent(intent, user_id="user_alice")
    assert res["subsystem"] == "task_engine"
    assert res["action"] == "task_creation"
    assert res["status"] == "DISPATCHED_TO_TASK_ENGINE"


@pytest.mark.asyncio
async def test_planner_bridge_routes_to_skills():
    """Verify ANALYZE intent maps to Skills Catalog (Spec 155)."""
    intent = IntentSchema(
        intent_id="i2",
        source_command_id="c2",
        type=IntentType.ANALYZE,
        objective="Analyze performance profile",
        risk=IntentRiskLevel.LOW,
        status="READY",
    )

    res = await CommandRouter.route_intent(intent, user_id="user_alice")
    assert res["subsystem"] == "skills_catalog"
    assert res["action"] == "skill_invocation"


@pytest.mark.asyncio
async def test_planner_bridge_routes_to_automation():
    """Verify AUTOMATE intent maps to Automation Service (Spec 157)."""
    intent = IntentSchema(
        intent_id="i3",
        source_command_id="c3",
        type=IntentType.AUTOMATE,
        objective="Every morning check CI",
        risk=IntentRiskLevel.NORMAL,
        status="READY",
    )

    res = await CommandRouter.route_intent(intent, user_id="user_alice")
    assert res["subsystem"] == "automation_service"
    assert res["action"] == "automation_creation"
