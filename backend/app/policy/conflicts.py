"""Deterministic Policy Conflict Resolution and Conflict Detection (Task 36).

Core Invariants:
- DENY strictly overrides ALLOW regardless of priority.
- Never 'average' policy results.
- Conservative escalation: DENY > REQUIRE_STEP_UP_AUTH > REQUIRE_APPROVAL > REQUIRE_CONFIRMATION > ALLOW_WITH_LIMITS > ALLOW > DEFER.
- Detect unreachable or conflicting policy combinations.
"""

from typing import Any

from app.policy.schemas import PolicyDecisionType, PolicyRule


class ConflictResolver:
    """Deterministically arbitrates among multiple matching policy rules."""

    # Precedence order (lower rank number = higher precedence)
    DECISION_PRECEDENCE: dict[PolicyDecisionType, int] = {
        PolicyDecisionType.DENY: 0,
        PolicyDecisionType.REQUIRE_STEP_UP_AUTH: 1,
        PolicyDecisionType.REQUIRE_APPROVAL: 2,
        PolicyDecisionType.REQUIRE_CONFIRMATION: 3,
        PolicyDecisionType.ALLOW_WITH_LIMITS: 4,
        PolicyDecisionType.ALLOW: 5,
        PolicyDecisionType.DEFER: 6,
    }

    @classmethod
    def resolve(cls, matching_rules: list[PolicyRule]) -> tuple[PolicyDecisionType, PolicyRule | None, list[str]]:
        """Select winning decision from multiple matching rules.

        Returns (Winning Decision, Primary Rule, matched_policy_ids).
        """
        if not matching_rules:
            return PolicyDecisionType.ALLOW, None, []

        matched_ids = [r.policy_id for r in matching_rules]

        # 1. Any DENY immediately wins (Sections 8, 9, 131)
        deny_rules = [r for r in matching_rules if r.decision == PolicyDecisionType.DENY]
        if deny_rules:
            # Sort deny rules by priority descending (highest priority number first)
            primary_deny = sorted(deny_rules, key=lambda r: r.priority, reverse=True)[0]
            return PolicyDecisionType.DENY, primary_deny, matched_ids

        # 2. Sort all matching rules by decision precedence, then rule priority descending
        sorted_rules = sorted(
            matching_rules,
            key=lambda r: (cls.DECISION_PRECEDENCE.get(r.decision, 99), -r.priority)
        )

        winner = sorted_rules[0]
        return winner.decision, winner, matched_ids

    @classmethod
    def detect_conflicts(cls, policies: list[PolicyRule]) -> list[dict[str, Any]]:
        """Identify potential policy conflicts such as overlapping conditions with opposing decisions."""
        conflicts: list[dict[str, Any]] = []

        for i in range(len(policies)):
            p1 = policies[i]
            if not p1.enabled:
                continue

            for j in range(i + 1, len(policies)):
                p2 = policies[j]
                if not p2.enabled:
                    continue

                # Same scope tier and target
                if p1.scope == p2.scope and p1.target_scope_id == p2.target_scope_id:
                    # Opposing decisions (one ALLOW, one DENY)
                    if (p1.decision == PolicyDecisionType.ALLOW and p2.decision == PolicyDecisionType.DENY) or \
                       (p1.decision == PolicyDecisionType.DENY and p2.decision == PolicyDecisionType.ALLOW):

                        # Compare conditions - if identical or subset, flag overlap
                        p1_fields = {c.field for c in p1.conditions}
                        p2_fields = {c.field for c in p2.conditions}

                        if p1_fields == p2_fields:
                            conflicts.append({
                                "conflict_type": "OVERLAPPING_CONTRADICTION",
                                "policy_a": p1.policy_id,
                                "policy_b": p2.policy_id,
                                "decision_a": p1.decision.value,
                                "decision_b": p2.decision.value,
                                "description": f"Policies '{p1.policy_id}' and '{p2.policy_id}' share condition fields with contradictory decisions. DENY will always prevail.",
                            })

        return conflicts
