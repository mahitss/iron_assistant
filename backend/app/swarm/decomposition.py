"""Task decomposition, DAG dependency resolution, critical path analysis, and parallel batching (Task 64)."""

from __future__ import annotations

import logging
from collections import defaultdict, deque

from app.swarm.safety import SwarmSafetyError, SwarmSpawnLimiter
from app.swarm.schemas import CollectiveObjective, SwarmTaskNode, SwarmTopology, TaskDAG

logger = logging.getLogger(__name__)


class TaskDecompositionError(SwarmSafetyError):
    """Raised when DAG cycle or invalid dependency is detected."""


class TaskDecomposer:
    """Decomposes complex collective objectives into dependency-bounded Task DAGs (Spec 9 & 10)."""

    def __init__(self, limiter: SwarmSpawnLimiter | None = None) -> None:
        self.limiter = limiter or SwarmSpawnLimiter()

    def decompose(
        self,
        objective: CollectiveObjective,
        topology: SwarmTopology = SwarmTopology.STAR,
    ) -> TaskDAG:
        """Decompose objective into a structured DAG appropriate for the chosen swarm topology."""
        # 1. Generate specialized task nodes based on domain and topology
        tasks: list[SwarmTaskNode] = []

        if topology == SwarmTopology.STAR:
            # Parallel specialists -> Synthesis -> Verification
            t_research = SwarmTaskNode(
                title="Evidence & Literature Gathering",
                description=f"Collect empirical sources, benchmarks, and architectural precedents for: {objective.goal}",
                role_needed="RESEARCHER",
                dependencies=[],
            )
            t_arch = SwarmTaskNode(
                title="System Architecture & Tradeoff Evaluation",
                description=f"Design structural components and evaluate trade-offs for: {objective.goal}",
                role_needed="ARCHITECT",
                dependencies=[],
            )
            t_sec = SwarmTaskNode(
                title="Security & Threat Surface Audit",
                description=f"Analyze security boundaries, credentials, and vulnerability vectors for: {objective.goal}",
                role_needed="SECURITY_ANALYST",
                dependencies=[],
            )
            t_risk = SwarmTaskNode(
                title="Failure Mode & Blast Radius Analysis",
                description=f"Identify failure modes, cascading degradation, and recovery strategies for: {objective.goal}",
                role_needed="RISK_ANALYST",
                dependencies=[],
            )
            t_critic = SwarmTaskNode(
                title="Skeptical Review & Counter-Position Probe",
                description=f"Probe hidden assumptions, edge-case failures, and counter-positions for: {objective.goal}",
                role_needed="CRITIC",
                dependencies=[],
            )
            t_synth = SwarmTaskNode(
                title="Collective Synthesis & Consensus Reconciliation",
                description="Synthesize findings from all specialists, preserve minority opinions, and reconcile contradictions.",
                role_needed="SYNTHESIZER",
                dependencies=[
                    t_research.task_id,
                    t_arch.task_id,
                    t_sec.task_id,
                    t_risk.task_id,
                    t_critic.task_id,
                ],
            )
            t_verif = SwarmTaskNode(
                title="Truth & Safety Verification Gate",
                description="Verify synthesized conclusions against ground truth criteria and safety invariants.",
                role_needed="VERIFIER",
                dependencies=[t_synth.task_id],
            )
            tasks = [t_research, t_arch, t_sec, t_risk, t_critic, t_synth, t_verif]

        elif topology == SwarmTopology.PIPELINE:
            # Sequential pipeline: Research -> Architecture -> Security -> Risk -> Synthesis -> Verification
            t1 = SwarmTaskNode(
                title="Pipeline Stage 1: Empirical Research",
                description=f"Gather foundational evidence for: {objective.goal}",
                role_needed="RESEARCHER",
                dependencies=[],
            )
            t2 = SwarmTaskNode(
                title="Pipeline Stage 2: Architecture Formulation",
                description="Formulate architectural proposals using Stage 1 evidence.",
                role_needed="ARCHITECT",
                dependencies=[t1.task_id],
            )
            t3 = SwarmTaskNode(
                title="Pipeline Stage 3: Security & Invariant Audit",
                description="Audit Stage 2 architecture for security vulnerabilities.",
                role_needed="SECURITY_ANALYST",
                dependencies=[t2.task_id],
            )
            t4 = SwarmTaskNode(
                title="Pipeline Stage 4: Synthesis & Final Recommendation",
                description="Synthesize pipeline outcomes into verified collective recommendation.",
                role_needed="SYNTHESIZER",
                dependencies=[t3.task_id],
            )
            t5 = SwarmTaskNode(
                title="Pipeline Stage 5: Formal Verification",
                description="Verify synthesized output against requirements.",
                role_needed="VERIFIER",
                dependencies=[t4.task_id],
            )
            tasks = [t1, t2, t3, t4, t5]

        elif topology == SwarmTopology.DEBATE:
            # Thesis -> Antithesis -> Synthesis -> Verification
            t_thesis = SwarmTaskNode(
                title="Thesis Formulation",
                description=f"Develop primary affirmative proposal for: {objective.goal}",
                role_needed="ARCHITECT",
                dependencies=[],
            )
            t_antithesis = SwarmTaskNode(
                title="Antithesis & Counter-Evidence",
                description=f"Develop adversarial critique and alternative hypotheses for: {objective.goal}",
                role_needed="CRITIC",
                dependencies=[t_thesis.task_id],
            )
            t_synth = SwarmTaskNode(
                title="Dialectical Synthesis & Rebuttal Resolution",
                description="Reconcile thesis and antithesis, preserving substantiated minority viewpoints.",
                role_needed="SYNTHESIZER",
                dependencies=[t_thesis.task_id, t_antithesis.task_id],
            )
            t_verif = SwarmTaskNode(
                title="Verification Gate",
                description="Verify resolved outcome.",
                role_needed="VERIFIER",
                dependencies=[t_synth.task_id],
            )
            tasks = [t_thesis, t_antithesis, t_synth, t_verif]

        else:
            # General / Hierarchical / Peer-to-Peer default
            t_fact = SwarmTaskNode(
                title="Fact & Evidence Baseline",
                description=f"Establish verified factual baseline for: {objective.goal}",
                role_needed="FACT_CHECKER",
                dependencies=[],
            )
            t_analysis = SwarmTaskNode(
                title="Specialist Analysis",
                description=f"Conduct multi-perspective evaluation for: {objective.goal}",
                role_needed="ANALYST",
                dependencies=[t_fact.task_id],
            )
            t_synth = SwarmTaskNode(
                title="Collective Synthesis",
                description="Synthesize multi-agent findings.",
                role_needed="SYNTHESIZER",
                dependencies=[t_analysis.task_id],
            )
            tasks = [t_fact, t_analysis, t_synth]

        # 2. Check task limits
        self.limiter.check_task_addition(len(tasks))

        # 3. Detect cycles and compute DAG properties
        dep_map = {t.task_id: list(t.dependencies) for t in tasks}
        self._validate_no_cycles(dep_map)

        parallel_groups = self._compute_parallel_groups(tasks)
        critical_path = self._compute_critical_path(tasks)

        dag = TaskDAG(
            objective_id=objective.objective_id,
            tasks=tasks,
            critical_path=critical_path,
            parallel_groups=parallel_groups,
            dependencies_map=dep_map,
        )
        logger.info(
            "TASK_DAG_DECOMPOSED: obj_id=%s topology=%s tasks=%d parallel_groups=%d",
            objective.objective_id,
            topology.value,
            len(tasks),
            len(parallel_groups),
        )
        return dag

    def _validate_no_cycles(self, dep_map: dict[str, list[str]]) -> None:
        """Validate that the task dependency graph is strictly acyclic using DFS."""
        visited: dict[str, int] = {}  # 0=unvisited, 1=visiting, 2=visited

        def dfs(node: str) -> None:
            visited[node] = 1
            for neighbor in dep_map.get(node, []):
                state = visited.get(neighbor, 0)
                if state == 1:
                    raise TaskDecompositionError(
                        f"Circular dependency cycle detected in Task DAG involving '{neighbor}'"
                    )
                if state == 0:
                    dfs(neighbor)
            visited[node] = 2

        for task_id in dep_map:
            if visited.get(task_id, 0) == 0:
                dfs(task_id)

    def _compute_parallel_groups(self, tasks: list[SwarmTaskNode]) -> list[list[str]]:
        """Group tasks into parallel execution batches using topological levels."""
        in_degree: dict[str, int] = {t.task_id: len(t.dependencies) for t in tasks}
        dependents: dict[str, list[str]] = defaultdict(list)
        for t in tasks:
            for dep in t.dependencies:
                dependents[dep].append(t.task_id)

        queue = deque([t_id for t_id, deg in in_degree.items() if deg == 0])
        groups: list[list[str]] = []

        while queue:
            batch = list(queue)
            groups.append(batch)
            queue.clear()
            for t_id in batch:
                for child in dependents.get(t_id, []):
                    in_degree[child] -= 1
                    if in_degree[child] == 0:
                        queue.append(child)

        return groups

    def _compute_critical_path(self, tasks: list[SwarmTaskNode]) -> list[str]:
        """Compute the longest path through the task DAG as critical path."""
        dependents: dict[str, list[str]] = defaultdict(list)
        for t in tasks:
            for dep in t.dependencies:
                dependents[dep].append(t.task_id)

        roots = [t.task_id for t in tasks if not t.dependencies]
        memo: dict[str, list[str]] = {}

        def get_longest_path(node_id: str) -> list[str]:
            if node_id in memo:
                return memo[node_id]
            children = dependents.get(node_id, [])
            if not children:
                res = [node_id]
            else:
                longest_child = max((get_longest_path(c) for c in children), key=len)
                res = [node_id] + longest_child
            memo[node_id] = res
            return res

        longest_overall: list[str] = []
        for r in roots:
            path = get_longest_path(r)
            if len(path) > len(longest_overall):
                longest_overall = path

        # Mark nodes on critical path
        cp_set = set(longest_overall)
        for t in tasks:
            if t.task_id in cp_set:
                t.is_critical_path = True

        return longest_overall
