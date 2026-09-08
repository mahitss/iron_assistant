"""Developer Specialist Agent inspecting local repositories, Git history, and codebases."""

import logging
from typing import Any

from app.agents.limits import AgentBudgetTracker
from app.agents.policies import AgentSecurityPolicy
from app.agents.schemas import AgentContext, AgentEvidence, AgentResult
from app.agents.state import AgentTaskStatus, AgentType, EvidenceType
from app.models.registry import ModelCapability
from app.models.router import ModelRouter
from app.tools.executor import ToolExecutor
from app.tools.schemas import ToolCall

logger = logging.getLogger("kairo.agents.specialists.developer")


class DeveloperSpecialist:
    """Specialist agent responsible for repository inspection, code analysis, and Git diagnostics."""

    agent_type = AgentType.DEVELOPER

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
        """Execute developer task: check git status/diff, search code, inspect configuration."""
        allowed_tools = context.allowed_tools or [
            "git_status",
            "git_diff",
            "git_log",
            "code_search",
            "code_read_file",
        ]

        evidence: list[AgentEvidence] = []
        tool_calls_count = 0
        findings: list[str] = []

        lowered = context.bounded_input.lower()

        # 1. Run git_status if requested or relevant
        if "git_status" in allowed_tools and any(
            k in lowered for k in ("git", "repo", "status", "uncommitted", "version", "upgrade")
        ):
            AgentSecurityPolicy.assert_tool_allowed(cls.agent_type, "git_status", allowed_tools)
            if budget_tracker:
                budget_tracker.record_tool_call(cls.agent_type)

            call = ToolCall(
                id=f"call_{context.task_id}_status",
                name="git_status",
                arguments={},
            )
            res = await tool_executor.execute(
                tool_call=call,
                user_id=context.user_id,
                session_id=context.session_id,
                db_session=db_session,
            )
            tool_calls_count += 1

            if res.success and isinstance(res.result, dict):
                clean = res.result.get("is_clean", True)
                branch = res.result.get("branch", "main")
                status_text = f"Repository on branch '{branch}' (clean={clean})."
                evidence.append(
                    AgentEvidence(
                        type=EvidenceType.OBSERVED,
                        statement=status_text,
                        source="git_status",
                    )
                )
                findings.append(status_text)

        # 2. Search code / config (e.g. pyproject.toml, requirements.txt, Dockerfile)
        if "code_search" in allowed_tools and any(
            k in lowered for k in ("version", "python", "upgrade", "dependency", "config")
        ):
            AgentSecurityPolicy.assert_tool_allowed(cls.agent_type, "code_search", allowed_tools)
            if budget_tracker:
                budget_tracker.record_tool_call(cls.agent_type)

            call = ToolCall(
                id=f"call_{context.task_id}_search",
                name="code_search",
                arguments={"query": "python_version", "max_results": 3},
            )
            res = await tool_executor.execute(
                tool_call=call,
                user_id=context.user_id,
                session_id=context.session_id,
                db_session=db_session,
            )
            tool_calls_count += 1

            if res.success and isinstance(res.result, dict):
                matches = res.result.get("matches", [])
                for m in matches[:3]:
                    file_p = m.get("file", "")
                    content = m.get("content", "").strip()
                    evidence.append(
                        AgentEvidence(
                            type=EvidenceType.OBSERVED,
                            statement=f"Found in {file_p}: {content}",
                            source=file_p,
                        )
                    )
                    findings.append(f"{file_p}: {content}")

        summary = (
            "\n".join(findings)
            if findings
            else f"Inspected repository for '{context.bounded_input}'. No critical issues found."
        )

        if model_router and provider and findings:
            try:
                model = model_router.select_model(ModelCapability.CODING)
                prompt = f"You are Kairo's Developer Agent. Summarize the following code/git findings in 1-3 sentences.\n\nFindings:\n{summary}"
                resp = await provider.complete(
                    model=model.id,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=200,
                )
                summary = resp.choices[0].message.content.strip()
            except Exception as exc:
                logger.debug("LLM developer summarization skipped: %s", exc)

        return AgentResult(
            task_id=context.task_id,
            agent_type=cls.agent_type,
            status=AgentTaskStatus.COMPLETED,
            summary=summary,
            evidence=evidence,
            structured_output={"findings": findings},
            tool_calls_count=tool_calls_count,
        )
