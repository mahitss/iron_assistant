"""Context isolation and scoped execution context builder for specialist agents."""

import logging

from app.agents.policies import AgentSecurityPolicy
from app.agents.schemas import AgentContext, AgentResult, AgentTaskSpec

logger = logging.getLogger("kairo.agents.context")


class AgentContextBuilder:
    """Builds isolated, bounded execution contexts for individual sub-agent tasks."""

    @classmethod
    def build_context(
        cls,
        task: AgentTaskSpec,
        parent_task_id: str,
        user_id: str,
        session_id: str | None,
        dependencies_results: dict[str, AgentResult],
        allowed_tools: list[str],
        timeout_seconds: int = 300,
        max_tool_calls: int = 20,
    ) -> AgentContext:
        """Construct scoped context isolating information strictly to what this specialist requires.

        Guarantees:
        1. Context isolation: only requested dependencies' results are visible.
        2. Prompt injection defense: inputs and outputs are sanitized and bounded.
        3. Identity binding: user_id and session_id are inherited from parent, never forged.
        4. Token/secret stripping: raw credentials are scrubbed.
        """
        # Filter dependency results to only those explicitly declared
        scoped_deps: dict[str, AgentResult] = {
            dep_id: dependencies_results[dep_id]
            for dep_id in task.dependencies
            if dep_id in dependencies_results
        }

        # Build bounded input combining task objective and dependency summaries
        input_parts: list[str] = [f"TASK OBJECTIVE: {task.objective}"]

        if scoped_deps:
            input_parts.append("\nPREVIOUS FINDINGS FROM DEPENDENCIES:")
            for dep_id, res in scoped_deps.items():
                input_parts.append(f"- [{res.agent_type} (task {dep_id})]: {res.summary}")
                if res.evidence:
                    for ev in res.evidence[:5]:
                        input_parts.append(
                            f"  * {ev.type}: {ev.statement}"
                            + (f" (Source: {ev.source})" if ev.source else "")
                        )

        bounded_text = "\n".join(input_parts)
        sanitized_input = AgentSecurityPolicy.sanitize_untrusted_input(bounded_text)

        return AgentContext(
            task_id=task.task_id,
            parent_task_id=parent_task_id,
            user_id=user_id,
            session_id=session_id,
            agent_type=task.agent_type,
            bounded_input=sanitized_input,
            dependencies_results=scoped_deps,
            allowed_tools=allowed_tools,
            max_tool_calls=max_tool_calls,
            timeout_seconds=timeout_seconds,
        )
