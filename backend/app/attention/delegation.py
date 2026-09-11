"""Agent Delegation and Attention Handoff Engine (Task 70).

Supports:
- Capability and availability-aware agent selection (never blindly picking the first agent)
- Explicit delegation with orchestrator oversight
- Safe handoff between agents when an agent becomes unavailable
- Context and provenance preservation across transitions
"""

from datetime import UTC, datetime
from typing import Any

from app.attention.lifecycle import AttentionLifecycleStateMachine
from app.attention.schemas import AttentionCandidate, AttentionState


def utc_now() -> datetime:
    return datetime.now(UTC)


class AttentionDelegationEngine:
    """Manages attention item delegation, agent competition, and safe handoffs."""

    @classmethod
    def select_best_agent(
        cls,
        *,
        candidate: AttentionCandidate,
        available_agents: list[dict[str, Any]],
    ) -> tuple[str | None, str]:
        """Select the most suitable agent based on capabilities, specialization, and load.

        available_agents format:
        [{"agent_id": "sec-agent-1", "capabilities": ["security", "investigation"], "load": 0.2, "success_rate": 0.95}, ...]
        """
        if not available_agents:
            return None, "No agents available for delegation."

        required_caps = set(candidate.required_capabilities)
        scored_candidates: list[tuple[float, str, str]] = []

        for agent in available_agents:
            aid = agent.get("agent_id", "unknown")
            caps = set(agent.get("capabilities", []))
            load = float(agent.get("load", 0.5))
            success = float(agent.get("success_rate", 0.8))

            # Capability match
            if required_caps:
                match_ratio = len(caps.intersection(required_caps)) / max(1, len(required_caps))
            else:
                match_ratio = 0.5

            # Higher success, lower load, higher capability match
            suitability = (match_ratio * 0.5) + (success * 0.3) + ((1.0 - load) * 0.2)
            scored_candidates.append((suitability, aid, f"match={match_ratio:.2f}, success={success:.2f}"))

        # Sort descending
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        best_score, best_id, breakdown = scored_candidates[0]

        if best_score < 0.3:
            return None, f"No agent meets minimum suitability threshold (best={best_score:.2f})."

        return best_id, f"Selected agent '{best_id}' (suitability={best_score:.2f}, {breakdown})"

    @classmethod
    def delegate(
        cls,
        *,
        candidate: AttentionCandidate,
        target_agent_id: str,
        reason: str,
        scope: str = "full_investigation",
    ) -> AttentionCandidate:
        """Delegate candidate to target agent while preserving orchestrator oversight."""
        candidate.current_state = AttentionLifecycleStateMachine.transition(
            candidate.current_state,
            AttentionState.DELEGATED,
        )
        candidate.delegated_to = target_agent_id
        entry = {
            "delegated_to": target_agent_id,
            "delegated_at": utc_now().isoformat(),
            "reason": reason,
            "scope": scope,
            "status": "in_progress",
        }
        candidate.delegation_history.append(entry)
        return candidate

    @classmethod
    def handoff(
        cls,
        *,
        candidate: AttentionCandidate,
        from_agent_id: str,
        to_agent_id: str,
        reason: str,
        interim_findings: dict[str, Any] | None = None,
    ) -> AttentionCandidate:
        """Hand off candidate from an unavailable or failing agent to another agent."""
        if candidate.delegated_to != from_agent_id:
            # Still allow handoff if reassigning
            pass

        candidate.delegated_to = to_agent_id
        entry = {
            "from_agent": from_agent_id,
            "to_agent": to_agent_id,
            "handed_off_at": utc_now().isoformat(),
            "reason": reason,
            "interim_findings": interim_findings or {},
            "status": "handed_off",
        }
        candidate.delegation_history.append(entry)
        return candidate

    @classmethod
    def reclaim(
        cls,
        *,
        candidate: AttentionCandidate,
        reason: str,
    ) -> AttentionCandidate:
        """Reclaim attention from a delegated agent back to the orchestrator."""
        candidate.current_state = AttentionLifecycleStateMachine.transition(
            candidate.current_state,
            AttentionState.ATTENDING,
        )
        entry = {
            "reclaimed_from": candidate.delegated_to,
            "reclaimed_at": utc_now().isoformat(),
            "reason": reason,
            "status": "reclaimed",
        }
        candidate.delegation_history.append(entry)
        candidate.delegated_to = None
        return candidate
