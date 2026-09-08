"""Browser Specialist Agent for controlled webpage inspection, navigation, and screenshots."""

import logging
from typing import Any

from app.agents.limits import AgentBudgetTracker
from app.agents.policies import AgentSecurityPolicy
from app.agents.schemas import AgentContext, AgentEvidence, AgentResult
from app.agents.state import AgentTaskStatus, AgentType, EvidenceType
from app.models.router import ModelRouter
from app.tools.executor import ToolExecutor
from app.tools.schemas import ToolCall

logger = logging.getLogger("kairo.agents.specialists.browser")


class BrowserSpecialist:
    """Specialist agent responsible for browser inspection and visual page verification."""

    agent_type = AgentType.BROWSER

    @classmethod
    async def run(
        cls,
        context: AgentContext,
        tool_executor: ToolExecutor,
        model_router: ModelRouter | None = None,
        provider: Any | None = None,
        budget_tracker: AgentBudgetTracker | None = None,
        db_session: Any = None,
    ) -> AgentResult:
        """Execute browser task: inspect page or capture visual state."""
        allowed_tools = context.allowed_tools or [
            "browser_open",
            "browser_navigate",
            "browser_inspect",
            "browser_screenshot",
        ]

        evidence: list[AgentEvidence] = []
        tool_calls_count = 0
        findings: list[str] = []

        # Derive URL from bounded input if present
        target_url = "https://example.com"
        for word in context.bounded_input.split():
            if word.startswith("http://") or word.startswith("https://"):
                target_url = word.strip(".,;:\"'")
                break

        if "browser_inspect" in allowed_tools:
            AgentSecurityPolicy.assert_tool_allowed(cls.agent_type, "browser_inspect", allowed_tools)
            if budget_tracker:
                budget_tracker.record_tool_call(cls.agent_type)

            call = ToolCall(
                id=f"call_{context.task_id}_inspect",
                name="browser_inspect",
                arguments={"url": target_url},
            )
            res = await tool_executor.execute(
                tool_call=call,
                user_id=context.user_id,
                session_id=context.session_id,
                db_session=db_session,
            )
            tool_calls_count += 1

            if res.success and isinstance(res.result, dict):
                page_title = res.result.get("title", "Web Page")
                summary_text = f"Browser inspected '{target_url}' (Title: {page_title})."
                evidence.append(
                    AgentEvidence(
                        type=EvidenceType.OBSERVED,
                        statement=summary_text,
                        source=target_url,
                    )
                )
                findings.append(summary_text)

        summary = (
            "\n".join(findings) if findings else f"Browser specialist completed observation for {target_url}."
        )

        return AgentResult(
            task_id=context.task_id,
            agent_type=cls.agent_type,
            status=AgentTaskStatus.COMPLETED,
            summary=summary,
            evidence=evidence,
            structured_output={"url": target_url, "findings": findings},
            tool_calls_count=tool_calls_count,
        )
