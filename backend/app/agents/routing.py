"""Specialist Agent Routing, Task Classification, and ModelRouter Integration (Task 44)."""

from __future__ import annotations

import logging
from typing import Any

from app.agents.agent import Agent, AgentRole

logger = logging.getLogger("kairo.agents.routing")


class SpecialistRouter:
    """Routes subtasks to the most qualified specialist role and model profile (Specs 16, 17, 131)."""

    ROLE_KEYWORD_TAXONOMY: dict[AgentRole, list[str]] = {
        AgentRole.SECURITY_ANALYST: ["security", "cve", "auth", "permission", "vulnerability", "leak", "secret", "rbac"],
        AgentRole.CODER: ["code", "refactor", "function", "class", "bug", "implement", "ast", "syntax", "patch"],
        AgentRole.TESTER: ["test", "pytest", "unit test", "integration", "coverage", "assert", "benchmark"],
        AgentRole.VERIFIER: ["verify", "prove", "contract", "invariant", "validate", "ground truth"],
        AgentRole.RESEARCHER: ["research", "documentation", "search", "web", "fetch", "library", "api docs", "citations"],
        AgentRole.ANALYST: ["compare", "synthesize", "metrics", "tradeoff", "contradiction", "evaluate"],
        AgentRole.VISION_ANALYST: ["image", "screenshot", "ui layout", "visual", "diagram", "chart"],
        AgentRole.BROWSER_OPERATOR: ["browser", "navigate", "dom", "click", "web page", "scrape"],
        AgentRole.SYSTEM_OPERATOR: ["docker", "deploy", "server", "process", "infrastructure", "kubernetes"],
        AgentRole.REVIEWER: ["review", "critique", "diff review", "sanity check"],
    }

    @classmethod
    def classify_subtask_role(cls, task_objective: str, default_role: AgentRole = AgentRole.CODER) -> AgentRole:
        """Deterministically determine the most appropriate specialist role (Spec 17)."""
        clean = task_objective.lower()

        scores: dict[AgentRole, int] = {}
        for role, keywords in cls.ROLE_KEYWORD_TAXONOMY.items():
            score = sum(1 for kw in keywords if kw in clean)
            if score > 0:
                scores[role] = score

        if not scores:
            return default_role

        # Pick role with highest keyword relevance
        best_role = max(scores.items(), key=lambda item: item[1])[0]
        logger.info("Classified subtask '%s' -> specialist role '%s'", task_objective[:40], best_role.value)
        return best_role

    @classmethod
    def select_best_agent(
        cls,
        candidate_agents: list[Agent],
        target_role: AgentRole,
        policy_allowed_roles: list[str] | None = None,
    ) -> Agent | None:
        """Select optimal healthy agent satisfying policy constraints (Spec 16, 41, 131).
        
        PRINCIPLE: Policy dominates over routing preference.
        """
        eligible = [
            a for a in candidate_agents
            if a.role == target_role
            and a.health == "HEALTHY"
            and not a.trust_metadata.get("is_quarantined", False)
        ]

        if policy_allowed_roles is not None:
            eligible = [a for a in eligible if a.role.value in policy_allowed_roles]

        if not eligible:
            return None

        # Sort by verified tasks count descending
        eligible.sort(key=lambda a: a.trust_metadata.get("verified_tasks_count", 0), reverse=True)
        return eligible[0]
