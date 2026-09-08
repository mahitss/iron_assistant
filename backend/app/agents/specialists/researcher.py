"""Researcher Specialist Agent gathering public web sources and verified citations."""

import logging
from typing import Any

from app.agents.limits import AgentBudgetTracker
from app.agents.policies import AgentSecurityPolicy
from app.agents.schemas import AgentCitation, AgentContext, AgentEvidence, AgentResult
from app.agents.state import AgentTaskStatus, AgentType, EvidenceType
from app.models.registry import ModelCapability
from app.models.router import ModelRouter
from app.tools.executor import ToolExecutor
from app.tools.schemas import ToolCall

logger = logging.getLogger("kairo.agents.specialists.researcher")


class ResearcherSpecialist:
    """Specialist agent responsible for public web research, document retrieval, and citation tracking."""

    agent_type = AgentType.RESEARCHER

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
        """Execute research task: search web, fetch documentation, extract citations."""
        # Enforce agent tool permissions
        allowed_tools = context.allowed_tools or ["web_search", "web_fetch"]

        citations: list[AgentCitation] = []
        evidence: list[AgentEvidence] = []
        tool_calls_count = 0
        findings: list[str] = []

        # Derive search query from bounded input
        query = context.bounded_input.replace("TASK OBJECTIVE:", "").strip()
        if len(query) > 100:
            query = query[:100]

        # 1. Execute web search
        if "web_search" in allowed_tools:
            AgentSecurityPolicy.assert_tool_allowed(cls.agent_type, "web_search", allowed_tools)
            if budget_tracker:
                budget_tracker.record_tool_call(cls.agent_type)

            call = ToolCall(
                id=f"call_{context.task_id}_search",
                name="web_search",
                arguments={"query": query, "num_results": 3},
            )
            res = await tool_executor.execute(
                tool_call=call,
                user_id=context.user_id,
                session_id=context.session_id,
                db_session=db_session,
            )
            tool_calls_count += 1

            if res.success and isinstance(res.result, dict):
                results_list = res.result.get("results", [])
                for idx, r in enumerate(results_list, start=1):
                    title = r.get("title", f"Source {idx}")
                    url = r.get("url", "")
                    snippet = r.get("snippet", "")
                    citations.append(AgentCitation(id=idx, title=title, url=url, snippet=snippet))
                    evidence.append(
                        AgentEvidence(
                            type=EvidenceType.OBSERVED,
                            statement=f"{title}: {snippet}",
                            source=url,
                        )
                    )
                    findings.append(f"[{idx}] {title}: {snippet}")

        # If LLM is available, synthesize summary of research
        summary = (
            "\n".join(findings)
            if findings
            else f"Completed research on '{query}'. No external web matches found."
        )

        if model_router and provider and findings:
            try:
                model = model_router.select_model(ModelCapability.FAST)
                prompt = (
                    f"You are Kairo's Researcher Agent. Summarize the following research facts concisely in 1-3 sentences. "
                    f"Include bracketed citations like [1] where applicable.\n\nFacts:\n{summary}"
                )
                resp = await provider.complete(
                    model=model.id,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=200,
                )
                summary = resp.choices[0].message.content.strip()
            except Exception as exc:
                logger.debug("LLM research summarization skipped: %s", exc)

        return AgentResult(
            task_id=context.task_id,
            agent_type=cls.agent_type,
            status=AgentTaskStatus.COMPLETED,
            summary=summary,
            evidence=evidence,
            citations=citations,
            structured_output={"sources_count": len(citations), "findings": findings},
            tool_calls_count=tool_calls_count,
        )
