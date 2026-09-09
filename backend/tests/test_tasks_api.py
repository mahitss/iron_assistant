"""Integration tests for Tasks FastAPI routes and security scoping (Spec 123-126)."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base, get_db_session
from app.main import create_app
from app.tasks.models import TaskModel, TaskStepModel
from app.tasks.schemas import StepStatus, TaskRiskLevel, TaskStatus


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
async def test_create_and_list_tasks(app_and_client):
    """Test task creation and listing via REST API."""
    client, _ = app_and_client
    headers = {"x-user-id": "alice"}

    # 1. Create a task
    resp = await client.post(
        "/api/v1/tasks",
        headers=headers,
        json={
            "objective": "Investigate why Kairo CI is failing",
            "autonomy_level": "SUPERVISED",
            "priority": "NORMAL",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["objective"] == "Investigate why Kairo CI is failing"
    assert data["status"] in ("QUEUED", "PLANNING", "RUNNING")
    assert data["user_id"] == "alice"
    task_id = data["id"]

    # 2. List tasks
    list_resp = await client.get("/api/v1/tasks", headers=headers)
    assert list_resp.status_code == 200
    tasks = list_resp.json()
    assert len(tasks) >= 1
    assert any(t["id"] == task_id for t in tasks)


@pytest.mark.asyncio
async def test_task_cross_user_access_denial(app_and_client):
    """Verify that User B cannot access or control User A's tasks (Spec 124, 156 Q11)."""
    client, _ = app_and_client

    # Alice creates task
    resp = await client.post(
        "/api/v1/tasks",
        headers={"x-user-id": "alice"},
        json={"objective": "Alice private task"},
    )
    task_id = resp.json()["id"]

    # Bob attempts to get Alice's task -> 403 Forbidden
    bob_resp = await client.get(f"/api/v1/tasks/{task_id}", headers={"x-user-id": "bob"})
    assert bob_resp.status_code == 403
    assert "Access denied" in bob_resp.json()["detail"]


@pytest.mark.asyncio
async def test_task_pause_resume_cancel(app_and_client):
    """Test pausing, resuming, and cancelling tasks via API."""
    client, session_maker = app_and_client
    headers = {"x-user-id": "charlie"}

    # Create task
    resp = await client.post(
        "/api/v1/tasks",
        headers=headers,
        json={"objective": "Test control operations"},
    )
    task_id = resp.json()["id"]

    # Manually transition task to RUNNING in DB for state transition testing
    async with session_maker() as session:
        task = await session.get(TaskModel, task_id)
        task.status = TaskStatus.RUNNING.value
        await session.commit()

    # Pause
    pause_resp = await client.post(f"/api/v1/tasks/{task_id}/pause", headers=headers)
    assert pause_resp.status_code == 200
    assert pause_resp.json()["status"] == "PAUSED"

    # Resume
    resume_resp = await client.post(f"/api/v1/tasks/{task_id}/resume", headers=headers)
    assert resume_resp.status_code == 200
    assert resume_resp.json()["status"] == "RUNNING"

    # Cancel
    cancel_resp = await client.post(f"/api/v1/tasks/{task_id}/cancel", headers=headers)
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "CANCELLED"


@pytest.mark.asyncio
async def test_task_step_approval_flow(app_and_client):
    """Test approving a step in WAITING_APPROVAL state."""
    client, session_maker = app_and_client
    headers = {"x-user-id": "dana"}

    resp = await client.post(
        "/api/v1/tasks",
        headers=headers,
        json={"objective": "Test approval flow"},
    )
    task_id = resp.json()["id"]

    # Setup DB state with a step in WAITING_APPROVAL
    async with session_maker() as session:
        task = await session.get(TaskModel, task_id)
        task.status = TaskStatus.WAITING_APPROVAL.value

        step = TaskStepModel(
            task_id=task_id,
            plan_id="plan_1",
            sequence=1,
            title="Modify database config",
            objective="Update connection string",
            risk_level=TaskRiskLevel.WRITE.value,
            approval_required=True,
            status=StepStatus.WAITING_APPROVAL.value,
            dependencies=[],
            resources=[],
        )
        session.add(step)
        await session.commit()

    # Approve the step
    appr_resp = await client.post(
        f"/api/v1/tasks/{task_id}/approve",
        headers=headers,
        json={"approved": True, "reason": "Authorized by team lead"},
    )
    assert appr_resp.status_code == 200
    data = appr_resp.json()
    assert data["status"] == "RUNNING"


@pytest.mark.asyncio
async def test_task_waiting_user_clarification_response(app_and_client):
    """Test answering clarification question in WAITING_USER state."""
    client, session_maker = app_and_client
    headers = {"x-user-id": "elena"}

    resp = await client.post(
        "/api/v1/tasks",
        headers=headers,
        json={"objective": "Investigate environment"},
    )
    task_id = resp.json()["id"]

    async with session_maker() as session:
        task = await session.get(TaskModel, task_id)
        task.status = TaskStatus.WAITING_USER.value
        task.metadata_json = {"waiting_question": "Which environment should I investigate?"}
        await session.commit()

    # Elena submits clarification
    resp_prompt = await client.post(
        f"/api/v1/tasks/{task_id}/respond",
        headers=headers,
        json={"response": "Staging"},
    )
    assert resp_prompt.status_code == 200
    assert resp_prompt.json()["status"] in ("PLANNING", "RUNNING")
