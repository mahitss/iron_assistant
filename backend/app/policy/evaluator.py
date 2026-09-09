"""Core Policy Rule Evaluator for Kairo Governance Engine (Task 36).

Iterates through scoped governance rules, evaluates condition trees deterministically,
segregates shadow policies, and delegates conflict resolution.
"""

from typing import Any

from app.policy.conditions import ConditionEvaluator
from app.policy.conflicts import ConflictResolver
from app.policy.schemas import (
    PolicyContext,
    PolicyDecisionType,
    PolicyRule,
    RiskLevel,
)
from app.policy.scope import ScopeHierarchyEvaluator


class RuleEvaluator:
    """Evaluates candidate policies against an incoming PolicyContext."""

    @classmethod
    def evaluate_rules(
        cls,
        context: PolicyContext,
        policies: list[PolicyRule],
        assessed_risk: RiskLevel
    ) -> tuple[PolicyDecisionType, PolicyRule | None, list[str], list[dict[str, Any]], list[dict[str, Any]]]:
        """Evaluate a set of candidate policies against the context.

        Returns:
            - winning_decision: Final winning decision type
            - winning_rule: Primary rule responsible for winning decision (if any)
            - matched_policy_ids: IDs of all matching active rules
            - shadow_decisions: Results from matching shadow rules
            - trace: Detailed step-by-step evaluation trace
        """
        active_matches: list[PolicyRule] = []
        shadow_decisions: list[dict[str, Any]] = []
        trace: list[dict[str, Any]] = []

        for rule in policies:
            if not rule.enabled:
                trace.append({"policy_id": rule.policy_id, "status": "SKIPPED_DISABLED"})
                continue

            # 1. Scope check
            scope_matches = ScopeHierarchyEvaluator.matches_scope(rule, context)
            if not scope_matches:
                trace.append({"policy_id": rule.policy_id, "status": "SCOPE_MISMATCH"})
                continue

            # 2. Conditions check
            conditions_match = ConditionEvaluator.evaluate_all(rule.conditions, context)
            if not conditions_match:
                trace.append({"policy_id": rule.policy_id, "status": "CONDITIONS_NOT_MET"})
                continue

            # Matched!
            trace.append({
                "policy_id": rule.policy_id,
                "version": rule.version,
                "decision": rule.decision.value,
                "priority": rule.priority,
                "shadow_mode": rule.shadow_mode,
                "status": "MATCHED",
            })

            if rule.shadow_mode:
                shadow_decisions.append({
                    "policy_id": rule.policy_id,
                    "version": rule.version,
                    "decision": rule.decision.value,
                    "reason_code": rule.reason_code,
                })
            else:
                active_matches.append(rule)

        # Arbitrate conflicts among matching active policies
        winning_decision, winning_rule, matched_ids = ConflictResolver.resolve(active_matches)

        return winning_decision, winning_rule, matched_ids, shadow_decisions, trace
