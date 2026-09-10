"""Skill improvement, execution tracking, and parameter proposal engine (INVARIANTS 56-61)."""

from __future__ import annotations

from typing import Any


class SkillImprovementEngine:
    """Tracks skill execution telemetry and proposes safe parameter and heuristic refinements."""

    def __init__(self) -> None:
        # skill_id -> telemetry stats
        self._skill_telemetry: dict[str, dict[str, Any]] = {}
        # skill_id -> list of proposed improvements
        self._proposals: dict[str, list[dict[str, Any]]] = {}

    def record_skill_execution(
        self,
        skill_id: str,
        was_successful: bool,
        duration_ms: float = 0.0,
        error_type: str | None = None,
    ) -> dict[str, Any]:
        """INVARIANT 56: Tracks tool and skill execution telemetry."""
        stats = self._skill_telemetry.setdefault(
            skill_id,
            {"executions": 0, "successes": 0, "failures": 0, "avg_duration_ms": 0.0, "errors": []}
        )
        stats["executions"] += 1
        if was_successful:
            stats["successes"] += 1
        else:
            stats["failures"] += 1
            if error_type:
                stats["errors"].append(error_type)

        # Update average duration
        prev_avg = stats["avg_duration_ms"]
        stats["avg_duration_ms"] = round(
            ((prev_avg * (stats["executions"] - 1)) + duration_ms) / stats["executions"],
            2
        )
        return stats

    def propose_skill_improvement(
        self,
        skill_id: str,
        suggested_preconditions: list[str] | None = None,
        timeout_adjustment_ms: float | None = None,
        retry_policy_tweak: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """INVARIANT 61: Proposes safe operational refinements.
        Cannot modify permissions or security policies.
        """
        proposal = {
            "skill_id": skill_id,
            "suggested_preconditions": suggested_preconditions or [],
            "timeout_adjustment_ms": timeout_adjustment_ms,
            "retry_policy_tweak": retry_policy_tweak or {},
            "status": "PROPOSED",
            "security_policy_immutable": True,
        }
        self._proposals.setdefault(skill_id, []).append(proposal)
        return proposal

    def get_skill_stats(self, skill_id: str) -> dict[str, Any] | None:
        return self._skill_telemetry.get(skill_id)

    def list_proposals(self, skill_id: str | None = None) -> list[dict[str, Any]]:
        if skill_id:
            return self._proposals.get(skill_id, [])
        all_props = []
        for p_list in self._proposals.values():
            all_props.extend(p_list)
        return all_props
