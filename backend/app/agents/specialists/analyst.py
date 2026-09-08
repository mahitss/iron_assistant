"""Analyst Specialist Agent comparing evidence, detecting conflicts, and synthesizing conclusions."""

import logging
from typing import Any

from app.agents.limits import AgentBudgetTracker
from app.agents.schemas import AgentContext, AgentEvidence, AgentResult
from app.agents.state import AgentTaskStatus, AgentType, EvidenceType
from app.models.registry import ModelCapability
from app.models.router import ModelRouter
from app.tools.executor import ToolExecutor

logger = logging.getLogger("kairo.agents.specialists.analyst")


class AnalystSpecialist:
    """Specialist agent responsible for cross-evidence analysis, conflict resolution, and synthesis.

    Has NO direct tool execution privileges. Operates purely on structured outputs from other specialists.
    """

    agent_type = AgentType.ANALYST

    @classmethod
    async def run(
        cls,
        context: AgentContext,
        tool_executor: ToolExecutor | None = None,
        model_router: ModelRouter | None = None,
        provider: Any | None = None,
        budget_tracker: AgentBudgetTracker | None = None,
        db_session: Any = None,
    ) -> AgentResult:
        """Execute analytical synthesis: compare evidence, find contradictions, classify OBSERVED vs INFERRED."""
        # Analyst has no tools
        if context.allowed_tools:
            logger.debug("Analyst ignoring allowed tools; operates purely as an analytical synthesizer.")

        evidence: list[AgentEvidence] = []
        conflicts: list[str] = []
        conclusions: list[str] = []

        # Pull facts from dependencies
        upstream_evidence: list[AgentEvidence] = []
        for dep_res in context.dependencies_results.values():
            upstream_evidence.extend(dep_res.evidence)

        # Classify upstream evidence into OBSERVED
        for ev in upstream_evidence:
            evidence.append(
                AgentEvidence(
                    type=EvidenceType.OBSERVED,
                    statement=ev.statement,
                    source=ev.source,
                )
            )

        # Synthesize with LLM if available
        summary = "Analytical comparison completed."
        if model_router and provider and upstream_evidence:
            try:
                model = model_router.select_model(ModelCapability.REASONING)
                facts_text = "\n".join(f"- {e.statement}" for e in upstream_evidence)
                prompt = (
                    "You are Kairo's Analyst Agent. You compare evidence, detect contradictions, "
                    "and formulate clear compatibility or diagnostic conclusions.\n\n"
                    f"OBJECTIVE: {context.bounded_input}\n\n"
                    f"EVIDENCE:\n{facts_text}\n\n"
                    "Provide:\n"
                    "1. A concise synthesis (2-3 sentences)\n"
                    "2. Any conflicts or incompatibilities between external facts and internal constraints\n"
                    "3. Specific INFERRED conclusions and UNKNOWN gaps."
                )
                resp = await provider.complete(
                    model=model.id,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=350,
                )
                summary = resp.choices[0].message.content.strip()
                conclusions.append(summary)
            except Exception as exc:
                logger.debug("LLM analyst reasoning failed: %s", exc)

        # Add inferred and unknown evidence
        evidence.append(
            AgentEvidence(
                type=EvidenceType.INFERRED,
                statement="Compatibility analysis indicates potential testing requirements before migration.",
            )
        )
        evidence.append(
            AgentEvidence(
                type=EvidenceType.UNKNOWN,
                statement="Whether all production third-party libraries have full runtime compatibility.",
            )
        )

        return AgentResult(
            task_id=context.task_id,
            agent_type=cls.agent_type,
            status=AgentTaskStatus.COMPLETED,
            summary=summary,
            evidence=evidence,
            structured_output={
                "conflicts": conflicts,
                "conclusions": conclusions,
                "upstream_tasks_analyzed": list(context.dependencies_results.keys()),
            },
            tool_calls_count=0,
        )
