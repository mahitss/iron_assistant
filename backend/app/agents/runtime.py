"""Agent Runtime executing individual specialist tasks safely within bounds, timeouts, and policies."""

import asyncio
import logging
from typing import Any

from app.agents.limits import AgentBudgetTracker
from app.agents.policies import AgentSecurityPolicy
from app.agents.registry import AgentRegistry
from app.agents.schemas import AgentContext, AgentResult, AgentTaskSpec
from app.agents.specialists.analyst import AnalystSpecialist
from app.agents.specialists.browser import BrowserSpecialist
from app.agents.specialists.developer import DeveloperSpecialist
from app.agents.specialists.researcher import ResearcherSpecialist
from app.agents.state import AgentTaskStatus, AgentType
from app.models.router import ModelRouter
from app.tools.executor import ToolExecutor

logger = logging.getLogger("kairo.agents.runtime")


class AgentRuntime:
    """Safely executes an individual sub-agent task through the ToolExecutor and SecurityCenter."""

    SPECIALIST_MAP = {
        AgentType.RESEARCHER: ResearcherSpecialist,
        AgentType.DEVELOPER: DeveloperSpecialist,
        AgentType.ANALYST: AnalystSpecialist,
        AgentType.BROWSER: BrowserSpecialist,
    }

    @classmethod
    async def execute_task(
        cls,
        task: AgentTaskSpec,
        context: AgentContext,
        registry: AgentRegistry,
        tool_executor: ToolExecutor,
        model_router: ModelRouter | None = None,
        provider: Any | None = None,
        budget_tracker: AgentBudgetTracker | None = None,
        emergency_stop_service: Any | None = None,
        db_session: Any = None,
    ) -> AgentResult:
        """Run an isolated sub-agent task subject to per-task deadline and security checks."""
        agent_type_str = str(task.agent_type).upper()

        # 1. Emergency stop check
        if emergency_stop_service:
            AgentSecurityPolicy.check_emergency_stop(
                context.user_id, f"agent_task_{agent_type_str}", emergency_stop_service
            )

        # 2. Lookup specialist implementation
        specialist_cls = cls.SPECIALIST_MAP.get(agent_type_str)
        if not specialist_cls:
            logger.error("No specialist implementation registered for '%s'", agent_type_str)
            return AgentResult(
                task_id=task.task_id,
                agent_type=agent_type_str,
                status=AgentTaskStatus.FAILED,
                summary=f"Specialist '{agent_type_str}' has no runner implementation.",
                errors=[f"Unsupported specialist type: {agent_type_str}"],
            )

        # 3. Execute with timeout
        timeout = context.timeout_seconds or 300
        try:
            result = await asyncio.wait_for(
                specialist_cls.run(
                    context=context,
                    tool_executor=tool_executor,
                    model_router=model_router,
                    provider=provider,
                    budget_tracker=budget_tracker,
                    db_session=db_session,
                ),
                timeout=float(timeout),
            )
            return result
        except TimeoutError:
            logger.warning("Agent task '%s' (%s) timed out after %ds", task.task_id, agent_type_str, timeout)
            return AgentResult(
                task_id=task.task_id,
                agent_type=agent_type_str,
                status=AgentTaskStatus.TIMED_OUT,
                summary=f"Agent '{agent_type_str}' timed out after {timeout} seconds.",
                errors=["Execution timed out"],
            )
        except Exception as exc:
            logger.exception("Agent task '%s' (%s) failed with error: %s", task.task_id, agent_type_str, exc)
            return AgentResult(
                task_id=task.task_id,
                agent_type=agent_type_str,
                status=AgentTaskStatus.FAILED,
                summary=f"Agent '{agent_type_str}' encountered an error: {exc}",
                errors=[str(exc)],
            )
