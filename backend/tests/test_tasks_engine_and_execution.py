"""Tests for AutonomousTaskEngine loop, checkpoints, recovery, and step execution (Spec 22-26, 38-41)."""

import asyncio
from datetime import UTC, datetime
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.tasks.checkpoint import CheckpointService
from app.tasks.engine import AutonomousTaskEngine
from app.tasks.executor import StepExecutor
from app.tasks.planner import TaskPlanner
from app.tasks.recovery import TaskRecoveryService
from app.tasks.replanner import TaskReplanner
from app.tasks.schemas import (
    AutonomyLevel,
    FailureClassification,
    StepStatus,
    TaskBudget,
    TaskRiskLevel,
    TaskStatus,
    TaskStepSchema,
)


@pytest.fixture
async def async_test_session():
    """Create in-memory SQLite database session for unit tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_autonomous_engine_read_task_execution(async_test_session):
    """Verify autonomous execution loop completes a multi-step research task without user intervention."""
    engine = AutonomousTaskEngine()

    result = await engine.run_task(
        task_id="task_test_research",
        user_id="test_user",
        objective="Research vector-search changes in PostgreSQL and summarize what matters",
        autonomy_level=AutonomyLevel.AUTONOMOUS_READ,
        session=async_test_session,
    )

    assert result.outcome == "COMPLETED"
    assert "concluded with status COMPLETED" in result.summary
    assert len(result.evidence) >= 1
    assert result.verification.get("status") == "COMPLETED"


@pytest.mark.asyncio
async def test_checkpoint_serialization_and_recovery():
    """Verify checkpoint captures state and allows safe resumption without duplicate writes (Spec 38, 39)."""
    budget = TaskBudget(max_steps=10, steps_used=3)
    completed_steps = ["step_1", "step_2"]
    pending_steps = ["step_3"]

    state_data = CheckpointService.serialize_state(
        task_id="task_ckpt_1",
        status=TaskStatus.RUNNING,
        plan_version=1,
        completed_step_ids=completed_steps,
        pending_step_ids=pending_steps,
        budget=budget,
        artifacts=[{"name": "patch.diff", "content": "+fix"}],
        step_results={"step_1": {"output": "ok"}},
    )

    assert state_data["task_id"] == "task_ckpt_1"
    assert state_data["completed_step_ids"] == ["step_1", "step_2"]
    assert state_data["budget"]["steps_used"] == 3

    # Resumption payload preparation
    resumption = TaskRecoveryService.prepare_resumption(
        task=None,
        checkpoint_data=state_data,
    )
    assert resumption["can_resume"] is True
    assert resumption["completed_step_ids"] == ["step_1", "step_2"]
    assert resumption["pending_step_ids"] == ["step_3"]


@pytest.mark.asyncio
async def test_idempotency_key_generation():
    """Verify deterministic idempotency key computation for external mutations (Spec 40)."""
    key1 = TaskRecoveryService.generate_idempotency_key("task_abc", "step_1", 0)
    key2 = TaskRecoveryService.generate_idempotency_key("task_abc", "step_1", 0)
    key_attempt1 = TaskRecoveryService.generate_idempotency_key("task_abc", "step_1", 1)

    assert key1 == key2
    assert key1 != key_attempt1
    assert len(key1) == 32


@pytest.mark.asyncio
async def test_transient_failure_retry_backoff():
    """Verify retry policy approves transient failures with exponential backoff and rejects permanent failures (Spec 32, 33)."""
    replanner = TaskReplanner()

    step_read = TaskStepSchema(
        task_id="t1", plan_id="p1", sequence=1,
        id="s1", title="Read Logs", objective="Read logs",
        risk_level=TaskRiskLevel.READ, retry_count=0
    )

    # Transient error is eligible for retry
    can_retry, delay = replanner.should_retry_step(step_read, FailureClassification.TRANSIENT)
    assert can_retry is True
    assert delay == 1.0  # 2^0 = 1.0s

    # Destructive action is NEVER eligible for retry
    step_destructive = TaskStepSchema(
        task_id="t1", plan_id="p1", sequence=2,
        id="s2", title="Delete Old Cache", objective="Delete cache",
        risk_level=TaskRiskLevel.DESTRUCTIVE, retry_count=0
    )
    can_retry, _ = replanner.should_retry_step(step_destructive, FailureClassification.TRANSIENT)
    assert can_retry is False

    # Security error is NEVER eligible for retry
    can_retry, _ = replanner.should_retry_step(step_read, FailureClassification.SECURITY)
    assert can_retry is False
