"""Tests for AgentRuntime and MultiAgentExecutor (concurrency, timeouts, limits, cancellation)."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from app.agents.executor import MultiAgentExecutor
from app.agents.limits import AgentBudgetTracker, AgentToolLimitExceededError
from app.agents.registry import AgentRegistry
from app.agents.runtime import AgentRuntime
from app.agents.schemas import AgentContext, AgentDefinition, AgentPlan, AgentResult, AgentTaskSpec
from app.agents.state import AgentTaskStatus, AgentType


@pytest.mark.asyncio
async def test_budget_tracker_enforces_per_agent_and_total_limits():
    """Budget tracker raises AgentToolLimitExceededError when agent or total limits are exceeded."""
    tracker = AgentBudgetTracker(max_tool_calls_per_agent=3, max_total_tool_calls=5)

    # 3 calls for researcher succeed
    for _ in range(3):
        tracker.record_tool_call(str(AgentType.RESEARCHER))

    # 4th call for researcher should fail per-agent limit
    with pytest.raises(AgentToolLimitExceededError, match="exceeded maximum allowed tool calls"):
        tracker.record_tool_call(str(AgentType.RESEARCHER))

    # 2 calls for developer should bring total to 5
    tracker.record_tool_call(str(AgentType.DEVELOPER))
    tracker.record_tool_call(str(AgentType.DEVELOPER))

    # 6th total call should fail total limit
    with pytest.raises(AgentToolLimitExceededError, match="exceeded maximum total tool calls"):
        tracker.record_tool_call(str(AgentType.DEVELOPER))


@pytest.mark.asyncio
async def test_runtime_timeout_marks_task_timed_out(monkeypatch):
    """Runtime catches asyncio.TimeoutError and records TIMED_OUT status."""
    from app.agents.specialists.researcher import ResearcherSpecialist

    async def _slow_run(*args, **kwargs):
        await asyncio.sleep(2.0)
        return AgentResult(
            task_id="slow_task",
            agent_type=str(AgentType.RESEARCHER),
            summary="Completed slowly",
        )

    monkeypatch.setattr(ResearcherSpecialist, "run", _slow_run)

    task = AgentTaskSpec(
        task_id="t_timeout",
        agent_type=AgentType.RESEARCHER,
        objective="Research something very slow",
    )
    context = AgentContext(
        task_id="t_timeout",
        agent_type=AgentType.RESEARCHER,
        bounded_input="Research something very slow",
        allowed_tools=["web_search"],
        timeout_seconds=1,
    )

    registry = AgentRegistry()
    registry.register(
        AgentDefinition(
            name="researcher",
            agent_type=AgentType.RESEARCHER,
            description="Web researcher",
            allowed_tools=["web_search"],
        )
    )

    result = await AgentRuntime.execute_task(
        task=task,
        context=context,
        registry=registry,
        tool_executor=AsyncMock(),
    )

    assert result.status == AgentTaskStatus.TIMED_OUT
    assert (
        "timed out" in (result.errors[0] if result.errors else "").lower()
        or "timed out" in result.summary.lower()
    )


@pytest.mark.asyncio
async def test_executor_parallel_execution_respects_dag_and_concurrency(monkeypatch):
    """Executor schedules independent tasks in parallel and runs dependent tasks after parents finish."""
    active_count = 0
    max_observed_concurrency = 0

    async def mock_execute_task(cls, task, context, **kwargs):
        nonlocal active_count, max_observed_concurrency
        active_count += 1
        if active_count > max_observed_concurrency:
            max_observed_concurrency = active_count

        await asyncio.sleep(0.05)
        active_count -= 1

        return AgentResult(
            task_id=task.task_id,
            agent_type=str(task.agent_type),
            status=AgentTaskStatus.COMPLETED,
            summary=f"Result for {task.task_id}",
        )

    monkeypatch.setattr(AgentRuntime, "execute_task", classmethod(mock_execute_task))

    registry = AgentRegistry()
    for agent_type in [AgentType.RESEARCHER, AgentType.DEVELOPER, AgentType.BROWSER, AgentType.ANALYST]:
        registry.register(
            AgentDefinition(
                name=agent_type.value.lower(),
                agent_type=agent_type,
                description=f"Agent {agent_type}",
                allowed_tools=[],
            )
        )

    executor = MultiAgentExecutor(
        registry=registry,
        tool_executor=AsyncMock(),
        max_parallel_agents=3,
    )

    plan = AgentPlan(
        tasks=[
            AgentTaskSpec(task_id="t1", agent_type=AgentType.RESEARCHER, objective="Search A"),
            AgentTaskSpec(task_id="t2", agent_type=AgentType.DEVELOPER, objective="Inspect B"),
            AgentTaskSpec(task_id="t3", agent_type=AgentType.BROWSER, objective="Inspect C"),
            AgentTaskSpec(task_id="t4", agent_type=AgentType.RESEARCHER, objective="Search D"),
            AgentTaskSpec(
                task_id="t5",
                agent_type=AgentType.ANALYST,
                objective="Combine",
                dependencies=["t1", "t2", "t3", "t4"],
            ),
        ]
    )

    results = await executor.execute_plan(
        plan=plan,
        parent_task_id="parent_parallel_test",
        user_id="user_123",
        session_id="session_456",
    )

    assert len(results) == 5
    assert all(r.status == AgentTaskStatus.COMPLETED for r in results.values())
    # Concurrency bounded by max_parallel_agents (3)
    assert max_observed_concurrency <= 3
    assert results["t5"].summary == "Result for t5"


@pytest.mark.asyncio
async def test_executor_cancellation():
    """Executor halts pending tasks when parent task is cancelled."""
    registry = AgentRegistry()
    registry.register(
        AgentDefinition(
            name="researcher", agent_type=AgentType.RESEARCHER, description="Res", allowed_tools=[]
        )
    )
    registry.register(
        AgentDefinition(name="developer", agent_type=AgentType.DEVELOPER, description="Dev", allowed_tools=[])
    )

    executor = MultiAgentExecutor(
        registry=registry,
        tool_executor=AsyncMock(),
        max_parallel_agents=2,
    )

    plan = AgentPlan(
        tasks=[
            AgentTaskSpec(task_id="t1", agent_type=AgentType.RESEARCHER, objective="Task 1"),
            AgentTaskSpec(
                task_id="t2", agent_type=AgentType.DEVELOPER, objective="Task 2", dependencies=["t1"]
            ),
        ]
    )

    # Cancel immediately
    MultiAgentExecutor.cancel_task("test_parent_task")

    try:
        results = await executor.execute_plan(
            plan=plan,
            parent_task_id="test_parent_task",
            user_id="user_123",
            session_id="session_456",
        )

        # All tasks should be marked CANCELLED
        assert all(r.status == AgentTaskStatus.CANCELLED for r in results.values())
    finally:
        MultiAgentExecutor.clear_cancellation("test_parent_task")
