"""Policy Hierarchy Engine: 6-tier policy precedence and deterministic conflict resolution (Task 78)."""

from __future__ import annotations

import logging
from typing import Any

from app.policy.governance_schemas import GovernanceDecisionType, PolicyTier

logger = logging.getLogger(__name__)


class PolicyHierarchyEngine:
    """Enforces explicit multi-tier policy precedence: SYSTEM > SECURITY > TENANT > PROJECT > WORKFLOW > TASK."""

    # Precedence of decision outcomes at the same tier
    OUTCOME_PRECEDENCE: dict[GovernanceDecisionType, int] = {
        GovernanceDecisionType.DENIED: 0,
        GovernanceDecisionType.REQUIRES_HUMAN: 1,
        GovernanceDecisionType.REQUIRES_APPROVAL: 2,
        GovernanceDecisionType.ALLOWED: 3,
        GovernanceDecisionType.CONFLICTING_POLICY: 4,
        GovernanceDecisionType.UNKNOWN: 5,
    }

    @classmethod
    def resolve_conflicting_policies(
        cls,
        candidate_decisions: list[dict[str, Any]],
    ) -> tuple[GovernanceDecisionType, dict[str, Any] | None, list[dict[str, Any]]]:
        """Arbitrate among multiple matching policies across different hierarchy tiers.

        Each entry in candidate_decisions should have:
        - "policy_id": str
        - "tier": PolicyTier
        - "decision": GovernanceDecisionType
        - "reason": str

        Resolution Invariant:
        1. Higher tier strictly overrides lower tier (rank 0 beats rank 1..5).
        2. Within the same highest tier, DENY beats REQUIRES_HUMAN > REQUIRES_APPROVAL > ALLOWED.
        """
        if not candidate_decisions:
            return GovernanceDecisionType.ALLOWED, None, []

        # Group by tier rank
        sorted_by_tier = sorted(
            candidate_decisions,
            key=lambda d: d.get("tier", PolicyTier.TASK).rank,
        )

        highest_rank = sorted_by_tier[0]["tier"].rank
        top_tier_candidates = [d for d in sorted_by_tier if d["tier"].rank == highest_rank]

        # Identify conflicts (different outcomes at same or lower tiers)
        conflicts = []
        distinct_decisions = {d["decision"] for d in candidate_decisions}
        if len(distinct_decisions) > 1:
            conflicts.append({
                "tiers_involved": [d["tier"].value for d in candidate_decisions],
                "policies": [d["policy_id"] for d in candidate_decisions],
                "opposing_decisions": [d["decision"].value for d in candidate_decisions],
                "resolution_principle": "Higher tier strictly overrides lower tier; DENY wins on ties.",
            })

        # Resolve at top tier using outcome precedence
        winning_candidate = sorted(
            top_tier_candidates,
            key=lambda d: cls.OUTCOME_PRECEDENCE.get(d["decision"], 99),
        )[0]

        logger.info(
            "Hierarchy resolution: winner=%s (tier=%s, decision=%s)",
            winning_candidate["policy_id"],
            winning_candidate["tier"].value,
            winning_candidate["decision"].value,
        )

        return winning_candidate["decision"], winning_candidate, conflicts

    @classmethod
    def detect_hierarchy_conflicts(
        cls,
        policies: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Identify potential structural conflicts across policy tiers."""
        conflicts = []
        # Group policies by target action
        action_map: dict[str, list[dict[str, Any]]] = {}
        for p in policies:
            action = p.get("action", "*")
            if action not in action_map:
                action_map[action] = []
            action_map[action].append(p)

        for action, matched in action_map.items():
            if len(matched) > 1:
                decisions = {p.get("decision") for p in matched}
                if len(decisions) > 1:
                    conflicts.append({
                        "action": action,
                        "policies": [p.get("policy_id") for p in matched],
                        "tiers": [p.get("tier", PolicyTier.TASK).value for p in matched],
                        "decisions": [str(d) for d in decisions],
                    })

        return conflicts


default_hierarchy_engine = PolicyHierarchyEngine()
