"""Unit tests for AgentPlanner heuristic decomposition and PlanValidator DAG rules."""

import pytest

from app.agents.planner import AgentPlanner, PlanValidationError, PlanValidator
from app.agents.registry import create_default_agent_registry
from app.agents.schemas import AgentPlan, AgentTaskSpec
from app.agents.state import AgentType


def test_should_decompose_heuristics():
    """Verify simple questions stay single-agent while complex cross-domain tasks decompose."""
    # Simple questions: NO decomposition
    assert not AgentPlanner.should_decompose("What is Python?")
    assert not AgentPlanner.should_decompose("Hello Kairo")
    assert not AgentPlanner.should_decompose("Help me calculate 100 * 4")
    assert not AgentPlanner.should_decompose("Who is Ada Lovelace?")

    # Complex questions: YES decomposition
    assert AgentPlanner.should_decompose(
        "Research the latest Python release, inspect my Kairo repository, and tell me whether we should upgrade."
    )
    assert AgentPlanner.should_decompose("Investigate why CI is failing and propose a fix.")
    assert AgentPlanner.should_decompose("Compare our repository code with current documentation.")


@pytest.mark.asyncio
async def test_deterministic_plan_creation():
    """Verify deterministic plan generation produces valid DAG for upgrade request."""
    registry = create_default_agent_registry()
    planner = AgentPlanner(registry=registry)

    plan = await planner.create_plan(
        "Research latest Python release, inspect our repo, and tell me whether we should upgrade."
    )

    assert len(plan.tasks) == 3
    tasks_by_id = {t.task_id: t for t in plan.tasks}

    assert "task_research" in tasks_by_id
    assert "task_developer" in tasks_by_id
    assert "task_analyst" in tasks_by_id

    # Validate dependencies: Analyst depends on Researcher and Developer
    analyst_task = tasks_by_id["task_analyst"]
    assert "task_research" in analyst_task.dependencies
    assert "task_developer" in analyst_task.dependencies

    # Plan validator must pass
    sorted_tasks = PlanValidator.validate_plan(plan, registry)
    assert sorted_tasks[-1] == "task_analyst"


def test_plan_validator_detects_cycles():
    """Circular dependencies in task plan DAG must be rejected."""
    registry = create_default_agent_registry()

    cyclic_plan = AgentPlan(
        tasks=[
            AgentTaskSpec(
                task_id="t1",
                agent_type=AgentType.RESEARCHER,
                objective="Task 1",
                dependencies=["t2"],
            ),
            AgentTaskSpec(
                task_id="t2",
                agent_type=AgentType.DEVELOPER,
                objective="Task 2",
                dependencies=["t1"],
            ),
        ]
    )

    with pytest.raises(PlanValidationError) as exc:
        PlanValidator.validate_plan(cyclic_plan, registry)
    assert "Circular dependency" in str(exc.value)


def test_plan_validator_rejects_self_dependency():
    """Task depending on itself must be rejected."""
    registry = create_default_agent_registry()

    self_dep_plan = AgentPlan(
        tasks=[
            AgentTaskSpec(
                task_id="t1",
                agent_type=AgentType.RESEARCHER,
                objective="Task 1",
                dependencies=["t1"],
            ),
        ]
    )

    with pytest.raises(PlanValidationError) as exc:
        PlanValidator.validate_plan(self_dep_plan, registry)
    assert "cannot depend on itself" in str(exc.value)


def test_plan_validator_rejects_missing_dependency():
    """Task referencing non-existent dependency must be rejected."""
    registry = create_default_agent_registry()

    bad_plan = AgentPlan(
        tasks=[
            AgentTaskSpec(
                task_id="t1",
                agent_type=AgentType.RESEARCHER,
                objective="Task 1",
                dependencies=["non_existent_task"],
            ),
        ]
    )

    with pytest.raises(PlanValidationError) as exc:
        PlanValidator.validate_plan(bad_plan, registry)
    assert "non-existent dependency" in str(exc.value)


def test_plan_validator_enforces_task_limit():
    """Plans exceeding KAIRO_MAX_AGENT_TASKS (8) must be rejected."""
    registry = create_default_agent_registry()

    too_many = AgentPlan(
        tasks=[
            AgentTaskSpec(
                task_id=f"t{i}",
                agent_type=AgentType.RESEARCHER,
                objective=f"Task {i}",
                dependencies=[],
            )
            for i in range(12)
        ]
    )

    with pytest.raises(PlanValidationError) as exc:
        PlanValidator.validate_plan(too_many, registry)
    assert "exceeds limit" in str(exc.value)


def test_plan_validator_rejects_unknown_agent():
    """Tasks specifying unregistered agent types must be rejected."""
    registry = create_default_agent_registry()

    unknown_plan = AgentPlan(
        tasks=[
            AgentTaskSpec(
                task_id="t1",
                agent_type="MALICIOUS_AGENT",
                objective="Task 1",
                dependencies=[],
            )
        ]
    )

    with pytest.raises(PlanValidationError) as exc:
        PlanValidator.validate_plan(unknown_plan, registry)
    assert "not registered" in str(exc.value)
