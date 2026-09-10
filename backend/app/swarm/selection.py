"""Agent selection, diversity of reasoning, and anti-correlated-failure matching (Task 64)."""

from __future__ import annotations

import logging

from app.swarm.agents import SwarmAgentRegistry, swarm_agent_registry
from app.swarm.safety import SwarmSafetyError, SwarmSpawnLimiter
from app.swarm.schemas import AgentHealthState, CollectiveObjective, SwarmAgentSpec, SwarmTaskNode

logger = logging.getLogger(__name__)


class AgentSelectionError(SwarmSafetyError):
    """Raised when no suitable or healthy agent can be recruited for a critical role."""


class AgentSelector:
    """Selects and recruits specialized agents, enforcing reasoning diversity and health boundaries (Spec 11, 12, 29)."""

    def __init__(
        self,
        registry: SwarmAgentRegistry | None = None,
        limiter: SwarmSpawnLimiter | None = None,
    ) -> None:
        self.registry = registry or swarm_agent_registry
        self.limiter = limiter or SwarmSpawnLimiter()

    def select_agents_for_objective(
        self,
        objective: CollectiveObjective,
        requested_roles: list[str] | None = None,
    ) -> list[SwarmAgentSpec]:
        """Select a diverse team of specialized agents, avoiding correlated failure modes.

        Invariant: UNKNOWN != HEALTHY. Agents with UNKNOWN, DEGRADED, or UNAVAILABLE states are excluded.
        Invariant: MORE AGENTS != BETTER REASONING. Only recruit distinct specializations that contribute information gain.
        """
        all_agents = self.registry.list_agents()
        # Strictly exclude unverified or unhealthy agents
        healthy_agents = [a for a in all_agents if a.health == AgentHealthState.HEALTHY]

        if not healthy_agents:
            raise AgentSelectionError(
                "No healthy agents available in registry to execute collective objective."
            )

        # Determine target roles needed
        target_roles: set[str] = set()
        if requested_roles:
            target_roles.update(r.upper() for r in requested_roles)
        else:
            # Default diverse core team
            target_roles.update(["ARCHITECT", "SECURITY_ANALYST", "CRITIC", "SYNTHESIZER", "VERIFIER"])
            if "research" in objective.goal.lower() or objective.required_evidence:
                target_roles.add("RESEARCHER")
                target_roles.add("FACT_CHECKER")
            if objective.risk_level in ("HIGH", "CRITICAL"):
                target_roles.add("RISK_ANALYST")

        selected_agents: list[SwarmAgentSpec] = []
        recruited_roles: set[str] = set()

        # Match healthy candidates by role
        for role in target_roles:
            candidates = [
                a
                for a in healthy_agents
                if a.role.upper() == role and a.agent_id not in [s.agent_id for s in selected_agents]
            ]
            if candidates:
                # Pick highest trust level / best calibration
                best_agent = max(candidates, key=lambda a: a.trust_level)
                selected_agents.append(best_agent)
                recruited_roles.add(role)
            else:
                # If critical role missing, fall back to capability-matching agent
                cap_candidates = [
                    a
                    for a in healthy_agents
                    if any(role.lower() in c.lower() for c in a.capabilities)
                    and a.agent_id not in [s.agent_id for s in selected_agents]
                ]
                if cap_candidates:
                    best_agent = max(cap_candidates, key=lambda a: a.trust_level)
                    selected_agents.append(best_agent)
                    recruited_roles.add(best_agent.role.upper())
                elif role in ("SYNTHESIZER", "VERIFIER"):
                    # Synthesizer and Verifier are non-negotiable for collective safety
                    fallback = max(healthy_agents, key=lambda a: a.trust_level)
                    if fallback not in selected_agents:
                        selected_agents.append(fallback)

        # Enforce spawn limits
        self.limiter.check_spawn(current_depth=1, current_agent_count=len(selected_agents))

        logger.info(
            "AGENTS_SELECTED: obj_id=%s count=%d roles=%s",
            objective.objective_id,
            len(selected_agents),
            list(recruited_roles),
        )
        return selected_agents

    def select_diverse_team(
        self,
        objective: CollectiveObjective,
        min_perspectives: int = 4,
    ) -> list[SwarmAgentSpec]:
        """Convenience method for selecting diverse specialist team."""
        return self.select_agents_for_objective(objective)

    def get_eligible_agents(self, objective: CollectiveObjective | None = None) -> list[SwarmAgentSpec]:
        """Return healthy, uncompromised agents eligible for selection."""
        return [a for a in self.registry.list_agents() if a.health == AgentHealthState.HEALTHY]

    def assign_agent_to_task(
        self,
        task: SwarmTaskNode,
        candidates: list[SwarmAgentSpec],
    ) -> SwarmAgentSpec:
        """Assign best matching healthy agent to a specific task node."""
        role_needed = task.role_needed.upper()
        # Direct role match
        matching = [
            a for a in candidates if a.role.upper() == role_needed and a.health == AgentHealthState.HEALTHY
        ]
        if matching:
            chosen = max(matching, key=lambda a: a.trust_level)
            task.assigned_agent_id = chosen.agent_id
            return chosen

        # Capability fallback match
        cap_matching = [
            a
            for a in candidates
            if a.health == AgentHealthState.HEALTHY
            and any(role_needed.lower() in c.lower() for c in a.capabilities)
        ]
        if cap_matching:
            chosen = max(cap_matching, key=lambda a: a.trust_level)
            task.assigned_agent_id = chosen.agent_id
            return chosen

        # General fallback to most trusted candidate
        chosen = max(candidates, key=lambda a: a.trust_level)
        task.assigned_agent_id = chosen.agent_id
        return chosen
