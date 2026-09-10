"""Failure recovery, agent health mitigation, and resilient task reassignment (Task 64)."""

from __future__ import annotations

import logging

from app.swarm.agents import SwarmAgentRegistry
from app.swarm.schemas import AgentHealthState, SwarmAgentSpec, SwarmTaskNode, TaskStatus

logger = logging.getLogger(__name__)


class FailureRecoveryManager:
    """Detects agent failures, manages retries, and coordinates healthy reassignments (Spec 45 & 46)."""

    def handle_task_failure(
        self,
        task: SwarmTaskNode,
        failing_agent: SwarmAgentSpec,
        registry: SwarmAgentRegistry,
        error_message: str,
    ) -> tuple[bool, str, SwarmAgentSpec | None]:
        """Handle an agent task failure gracefully.

        Invariants:
        - UNKNOWN != SUCCESS.
        - Do not blindly repeat expensive or non-idempotent operations.
        - Reassign to an alternate healthy agent with compatible capabilities.
        """
        task.retry_count += 1
        logger.warning(
            "AGENT_TASK_FAILED: task_id=%s agent_id=%s retry=%d/%d err='%s'",
            task.task_id,
            failing_agent.agent_id,
            task.retry_count,
            task.max_retries,
            error_message,
        )

        # 1. Update failing agent's health if severe or repeated
        if task.retry_count >= task.max_retries:
            registry.update_health(failing_agent.agent_id, AgentHealthState.DEGRADED)

        # 2. If under retry limit, retry with same agent if still healthy
        if task.retry_count < task.max_retries and failing_agent.health == AgentHealthState.HEALTHY:
            task.status = TaskStatus.RETRYABLE
            return True, f"Retrying task with agent {failing_agent.agent_id}", failing_agent

        # 3. Find alternate healthy agent
        role_needed = task.role_needed.upper()
        healthy_candidates = [
            a
            for a in registry.list_agents(role=role_needed, health=AgentHealthState.HEALTHY)
            if a.agent_id != failing_agent.agent_id
        ]

        if not healthy_candidates:
            # Fallback to capability matching
            healthy_candidates = [
                a
                for a in registry.list_agents(health=AgentHealthState.HEALTHY)
                if any(role_needed.lower() in c.lower() for c in a.capabilities)
                and a.agent_id != failing_agent.agent_id
            ]

        if healthy_candidates:
            replacement = max(healthy_candidates, key=lambda a: a.trust_level)
            task.assigned_agent_id = replacement.agent_id
            task.status = TaskStatus.PENDING
            logger.info(
                "TASK_REASSIGNED: task_id=%s old=%s new=%s",
                task.task_id,
                failing_agent.agent_id,
                replacement.agent_id,
            )
            return True, f"Reassigned task to alternate healthy agent {replacement.agent_id}", replacement

        task.status = TaskStatus.FAILED
        task.error = error_message
        logger.error("TASK_RECOVERY_EXHAUSTED: task_id=%s no healthy alternate agents found", task.task_id)
        return False, "Failed to recover: no healthy alternate agents found for role", None
