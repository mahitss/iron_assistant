"""Integration tests for Multi-Agent Orchestration REST API endpoints and tenant isolation."""

import asyncio

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.agents.executor import MultiAgentExecutor
from app.agents.models import AgentTask
from app.agents.state import AgentTaskStatus, AgentType
from app.db.session import Base, get_db_session
from app.main import app


@pytest.fixture
def sqlite_agents_app():
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
    yield session_factory
    app.dependency_overrides.pop(get_db_session, None)
    asyncio.run(engine.dispose())


def test_cancel_agent_task_in_memory_and_db(sqlite_agents_app):
    """User can cancel an in-flight orchestrated agent task."""
    client = TestClient(app)
    headers = {"X-User-ID": "user_alice"}

    task_id = "task_cancel_123"

    res = client.post(f"/api/v1/agents/tasks/{task_id}/cancel", headers=headers)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["task_id"] == task_id
    assert data["cancelled"] is True
    assert data["status"] == "CANCELLED"
    assert MultiAgentExecutor.is_cancelled(task_id)

    MultiAgentExecutor.clear_cancellation(task_id)


def test_get_agent_task_not_found(sqlite_agents_app):
    """Querying a nonexistent agent task returns 404."""
    client = TestClient(app)
    headers = {"X-User-ID": "user_alice"}

    res = client.get("/api/v1/agents/tasks/nonexistent_task", headers=headers)
    assert res.status_code == status.HTTP_404_NOT_FOUND


def test_agent_task_tenant_isolation(sqlite_agents_app):
    """Users cannot inspect or cancel agent tasks belonging to another user."""
    session_factory = sqlite_agents_app

    async def create_task():
        async with session_factory() as s:
            task = AgentTask(
                id="alice_task_999",
                user_id="user_alice",
                session_id="session_1",
                agent_type=AgentType.RESEARCHER,
                status=AgentTaskStatus.RUNNING,
                objective="Inspect confidential repo",
            )
            s.add(task)
            await s.commit()

    asyncio.run(create_task())

    client = TestClient(app)

    # 1. Alice can view her task
    res = client.get("/api/v1/agents/tasks/alice_task_999", headers={"X-User-ID": "user_alice"})
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["id"] == "alice_task_999"
    assert res.json()["user_id"] == "user_alice"

    # 2. Bob cannot view Alice's task (403)
    bob_get_res = client.get("/api/v1/agents/tasks/alice_task_999", headers={"X-User-ID": "user_bob"})
    assert bob_get_res.status_code == status.HTTP_403_FORBIDDEN

    # 3. Bob cannot cancel Alice's task (403)
    bob_cancel_res = client.post(
        "/api/v1/agents/tasks/alice_task_999/cancel", headers={"X-User-ID": "user_bob"}
    )
    assert bob_cancel_res.status_code == status.HTTP_403_FORBIDDEN

    # 4. Alice can cancel her task (200)
    alice_cancel_res = client.post(
        "/api/v1/agents/tasks/alice_task_999/cancel", headers={"X-User-ID": "user_alice"}
    )
    assert alice_cancel_res.status_code == status.HTTP_200_OK
    assert alice_cancel_res.json()["cancelled"] is True
