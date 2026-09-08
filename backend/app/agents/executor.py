"""Multi-Agent Executor orchestrating DAG task execution, parallel concurrency, and cancellation."""

import asyncio
import logging
from typing import Any, Callable

from app.agents.context import AgentContextBuilder
from app.agents.limits import AgentBudgetTracker
from app.agents.planner import PlanValidator
from app.agents.registry import AgentRegistry
from app.agents.runtime import AgentRuntime
from app.agents.schemas import AgentPlan, AgentResult, AgentTaskSpec
from app.agents.state import AgentTaskStatus
from app.core.config import get_settings
from app.models.router import ModelRouter
from app.tools.executor import ToolExecutor

logger = logging.getLogger("kairo.agents.executor")

# In-memory registry of cancelled parent tasks
_CANCELLED_TASKS: set[str] = set()


class MultiAgentExecutor:
    """Coordinates parallel and sequential sub-agent task execution over a validated DAG."""

    def __init__(
        self,
        registry: AgentRegistry,
        tool_executor: ToolExecutor,
        model_router: ModelRouter | None = None,
        provider: Any | None = None,
        max_parallel_agents: int | None = None,
        emergency_stop_service: Any | None = None,
    ) -> None:
        self.registry = registry
        self.tool_executor = tool_executor
        self.model_router = model_router
        self.provider = provider
        cfg = get_settings()
        self.max_parallel_agents = (
            max_parallel_agents
            if max_parallel_agents is not None
            else getattr(cfg, "KAIRO_MAX_PARALLEL_AGENTS", 3)
        )
        self.emergency_stop_service = emergency_stop_service

    @classmethod
    def cancel_task(cls, task_id: str) -> bool:
        """Mark a parent task as cancelled."""
        _CANCELLED_TASKS.add(task_id)
        logger.info("Task '%s' registered for multi-agent cancellation.", task_id)
        return True

    @classmethod
    def is_cancelled(cls, task_id: str) -> bool:
        """Check if parent task has been cancelled by user."""
        return task_id in _CANCELLED_TASKS

    @classmethod
    def clear_cancellation(cls, task_id: str) -> None:
        """Clear cancellation marker."""
        _CANCELLED_TASKS.discard(task_id)

    async def execute_plan(
        self,
        plan: AgentPlan,
        parent_task_id: str,
        user_id: str,
        session_id: str | None = None,
        budget_tracker: AgentBudgetTracker | None = None,
        event_callback: Callable[[str, str, str | None, str], Any] | None = None,
        db_session: Any = None,
    ) -> dict[str, AgentResult]:
        """Execute all tasks in the plan according to their dependency graph.

        Independent tasks run in parallel up to max_parallel_agents.
        """
        # Validate plan and get topological order
        sorted_task_ids = PlanValidator.validate_plan(plan, self.registry)
        task_map = {t.task_id: t for t in plan.tasks}

        completed_results: dict[str, AgentResult] = {}
        semaphore = asyncio.Semaphore(self.max_parallel_agents)

        tracker = budget_tracker or AgentBudgetTracker()

        # Group tasks into dependency tiers or schedule dynamically as dependencies finish
        # Dynamic scheduling: tasks whose dependencies are met are runnable
        running_tasks: dict[str, asyncio.Task[AgentResult]] = {}
        pending_task_ids = set(sorted_task_ids)

        try:
            while pending_task_ids or running_tasks:
                # 1. Check user cancellation
                if self.is_cancelled(parent_task_id):
                    logger.warning(
                        "Execution of multi-agent plan '%s' was cancelled by user.", parent_task_id
                    )
                    for tid, t in running_tasks.items():
                        t.cancel()
                    break

                # 2. Check emergency stop
                if self.emergency_stop_service and self.emergency_stop_service.is_stopped(user_id):
                    logger.critical(
                        "Emergency stop active during plan '%s'! Halting all agent tasks.", parent_task_id
                    )
                    for tid, t in running_tasks.items():
                        t.cancel()
                    break

                # 3. Find newly ready tasks (all dependencies completed successfully)
                ready_task_ids = [
                    tid
                    for tid in pending_task_ids
                    if all(
                        dep in completed_results
                        and completed_results[dep].status == AgentTaskStatus.COMPLETED
                        for dep in task_map[tid].dependencies
                    )
                ]

                # If no tasks are ready and nothing is running, but pending remains -> broken dependencies
                if not ready_task_ids and not running_tasks:
                    logger.warning(
                        "Unresolvable task dependencies in plan '%s'. Aborting remaining.", parent_task_id
                    )
                    for tid in pending_task_ids:
                        completed_results[tid] = AgentResult(
                            task_id=tid,
                            agent_type=str(task_map[tid].agent_type),
                            status=AgentTaskStatus.FAILED,
                            summary="Task dependency failed or aborted.",
                            errors=["Unfulfilled upstream dependency"],
                        )
                    break

                # 4. Launch ready tasks up to concurrency semaphore
                for tid in ready_task_ids:
                    pending_task_ids.remove(tid)
                    task_spec = task_map[tid]

                    if event_callback:
                        event_callback(
                            "agent_started",
                            str(task_spec.agent_type),
                            tid,
                            f"Started {task_spec.agent_type}: {task_spec.objective}",
                        )

                    running_tasks[tid] = asyncio.create_task(
                        self._run_task_guarded(
                            task=task_spec,
                            parent_task_id=parent_task_id,
                            user_id=user_id,
                            session_id=session_id,
                            dependencies_results=completed_results,
                            semaphore=semaphore,
                            budget_tracker=tracker,
                            db_session=db_session,
                        )
                    )

                # 5. Wait for at least one running task to finish
                if running_tasks:
                    done, _ = await asyncio.wait(running_tasks.values(), return_when=asyncio.FIRST_COMPLETED)
                    for finished_task in done:
                        # Find corresponding task_id
                        matched_tid = None
                        for tid, t in running_tasks.items():
                            if t == finished_task:
                                matched_tid = tid
                                break

                        if matched_tid:
                            del running_tasks[matched_tid]
                            try:
                                res = finished_task.result()
                                completed_results[matched_tid] = res
                                if event_callback:
                                    event_callback(
                                        "agent_completed"
                                        if res.status == AgentTaskStatus.COMPLETED
                                        else "agent_failed",
                                        str(res.agent_type),
                                        matched_tid,
                                        res.summary,
                                    )
                            except Exception as exc:
                                logger.exception(
                                    "Agent task '%s' raised uncaught exception: %s", matched_tid, exc
                                )
                                completed_results[matched_tid] = AgentResult(
                                    task_id=matched_tid,
                                    agent_type=str(task_map[matched_tid].agent_type),
                                    status=AgentTaskStatus.FAILED,
                                    summary=f"Uncaught task error: {exc}",
                                    errors=[str(exc)],
                                )

        finally:
            self.clear_cancellation(parent_task_id)

        return completed_results

    async def _run_task_guarded(
        self,
        task: AgentTaskSpec,
        parent_task_id: str,
        user_id: str,
        session_id: str | None,
        dependencies_results: dict[str, AgentResult],
        semaphore: asyncio.Semaphore,
        budget_tracker: AgentBudgetTracker,
        db_session: Any,
    ) -> AgentResult:
        """Execute single task wrapped in semaphore bound and isolated context."""
        async with semaphore:
            defn = self.registry.get(task.agent_type)
            context = AgentContextBuilder.build_context(
                task=task,
                parent_task_id=parent_task_id,
                user_id=user_id,
                session_id=session_id,
                dependencies_results=dependencies_results,
                allowed_tools=defn.allowed_tools,
                timeout_seconds=defn.max_execution_time_seconds,
                max_tool_calls=defn.max_tool_calls,
            )

            return await AgentRuntime.execute_task(
                task=task,
                context=context,
                registry=self.registry,
                tool_executor=self.tool_executor,
                model_router=self.model_router,
                provider=self.provider,
                budget_tracker=budget_tracker,
                emergency_stop_service=self.emergency_stop_service,
                db_session=db_session,
            )
