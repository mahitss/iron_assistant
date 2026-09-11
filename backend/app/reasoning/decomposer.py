"""Structured Problem Decomposition Engine (Task 71).

Decomposes complex questions or objectives into a bounded DAG of sub-problems
with strict depth limits (<= 3) and dependency ordering.
"""

from typing import Any

from app.reasoning.schemas import ReasoningDepth, SubProblem


class ProblemDecomposer:
    """Decomposes complex problems into structured, bounded sub-problems."""

    MAX_DEPTH_BY_TIER = {
        ReasoningDepth.QUICK: 1,
        ReasoningDepth.STANDARD: 2,
        ReasoningDepth.DEEP: 3,
        ReasoningDepth.CRITICAL: 3,
    }

    MAX_SUBPROBLEMS_BY_TIER = {
        ReasoningDepth.QUICK: 2,
        ReasoningDepth.STANDARD: 5,
        ReasoningDepth.DEEP: 8,
        ReasoningDepth.CRITICAL: 10,
    }

    @classmethod
    def decompose(
        cls,
        question: str,
        objective: str = "",
        depth: ReasoningDepth = ReasoningDepth.STANDARD,
        context_hints: dict[str, Any] | None = None,
        max_depth: int | None = None,
    ) -> list[SubProblem]:
        """Decompose question into ordered, dependency-linked sub-problems."""
        max_subproblems = cls.MAX_SUBPROBLEMS_BY_TIER.get(depth, 5)
        effective_max_depth = max_depth or cls.MAX_DEPTH_BY_TIER.get(depth, 3)

        subproblems: list[SubProblem] = []
        q_lower = question.lower()

        # Diagnostic incident pattern
        if any(
            w in q_lower
            for w in [
                "unstable",
                "latency",
                "failure",
                "error",
                "outage",
                "slow",
                "bug",
                "cpu",
                "memory",
                "leak",
                "crash",
            ]
        ):
            p1 = SubProblem(
                question=f"What recent changes or anomalies occurred before '{question[:40]}...'?",
                objective="Identify temporal changes, deployments, or environmental shifts.",
                priority="HIGH",
                depth_level=1,
            )
            p2 = SubProblem(
                question="What components, services, or dependencies are exhibiting symptoms?",
                objective="Determine the blast radius and affected subsystems.",
                priority="HIGH",
                depth_level=1,
                dependencies=[p1.subproblem_id],
            )
            p3 = SubProblem(
                question="What hypotheses explain the observed symptoms and anomalies?",
                objective="Formulate distinct candidate root causes.",
                priority="NORMAL",
                depth_level=2,
                parent_id=p2.subproblem_id,
                dependencies=[p1.subproblem_id, p2.subproblem_id],
            )
            p4 = SubProblem(
                question="What evidence exists to support or refute each candidate hypothesis?",
                objective="Collect and cross-examine empirical evidence.",
                priority="NORMAL",
                depth_level=2,
                parent_id=p3.subproblem_id,
                dependencies=[p3.subproblem_id],
            )
            p5 = SubProblem(
                question="What corrective or mitigating alternatives exist and what are their tradeoffs?",
                objective="Evaluate alternative solutions under risk and reversibility constraints.",
                priority="HIGH",
                depth_level=2,
                parent_id=p4.subproblem_id,
                dependencies=[p4.subproblem_id],
            )
            subproblems.extend([p1, p2, p3, p4, p5])

        # Architectural or comparative planning pattern
        elif any(w in q_lower for w in ["compare", "choose", "architect", "design", "evaluate", "best"]):
            p1 = SubProblem(
                question="What are the essential requirements and hard constraints?",
                objective="Establish functional, non-functional, and security boundaries.",
                priority="HIGH",
                depth_level=1,
            )
            p2 = SubProblem(
                question="What candidate alternatives satisfy the core requirements?",
                objective="Generate viable architectural or operational approaches.",
                priority="NORMAL",
                depth_level=1,
                dependencies=[p1.subproblem_id],
            )
            p3 = SubProblem(
                question="What are the comparative tradeoffs (risk, cost, time, reversibility)?",
                objective="Multi-criteria comparison across alternatives.",
                priority="HIGH",
                depth_level=2,
                parent_id=p2.subproblem_id,
                dependencies=[p2.subproblem_id],
            )
            subproblems.extend([p1, p2, p3])

        # General analytical pattern
        else:
            p1 = SubProblem(
                question=f"What are the established facts and evidence regarding '{question[:50]}'?",
                objective="Gather baseline observations and verified context.",
                priority="HIGH",
                depth_level=1,
            )
            p2 = SubProblem(
                question="What assumptions are being made and what are the key uncertainties?",
                objective="Surface unverified premises and knowledge gaps.",
                priority="NORMAL",
                depth_level=1,
                dependencies=[p1.subproblem_id],
            )
            p3 = SubProblem(
                question="What conclusion has the strongest empirical support?",
                objective="Synthesize evidence-backed answer.",
                priority="HIGH",
                depth_level=2,
                parent_id=p1.subproblem_id,
                dependencies=[p1.subproblem_id, p2.subproblem_id],
            )
            subproblems.extend([p1, p2, p3])

        # Enforce depth and budget limits
        filtered = [sp for sp in subproblems if sp.depth_level <= effective_max_depth]
        return filtered[:max_subproblems]

    @classmethod
    def get_execution_order(cls, subproblems: list[SubProblem]) -> list[SubProblem]:
        """Topologically sort subproblems by dependencies."""
        resolved: list[str] = []
        ordered: list[SubProblem] = []
        remaining = list(subproblems)

        max_passes = len(subproblems) + 1
        passes = 0
        while remaining and passes < max_passes:
            passes += 1
            progress = False
            for sp in list(remaining):
                if not sp.dependencies or all(dep in resolved for dep in sp.dependencies):
                    ordered.append(sp)
                    resolved.append(sp.subproblem_id)
                    remaining.remove(sp)
                    progress = True
            if not progress:
                # Cycle or unresolved dependency break: append remaining
                ordered.extend(remaining)
                break

        return ordered

    @classmethod
    def topological_sort(cls, subproblems: list[SubProblem]) -> list[SubProblem]:
        """Alias for get_execution_order."""
        return cls.get_execution_order(subproblems)
