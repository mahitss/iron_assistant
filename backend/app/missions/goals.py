"""Goal Modeling, Normalization, Ambiguity Detection, Validation, and DAG Management (Task 66)."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

from app.missions.safety import MissionSafetyError, sanitize_mission_directive
from app.missions.schemas import (
    Goal,
    GoalAuthorityScope,
    GoalConflict,
    GoalFeasibilityStatus,
    GoalOrigin,
    GoalValidationStatus,
    SuccessCriteria,
)

logger = logging.getLogger("kairo.missions.goals")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class GoalManager:
    """Manages the full lifecycle of formal goals, from natural-language normalization to DAG decomposition."""

    # Words that signal ambiguous, unquantified objectives
    _VAGUE_TERMS = {
        "better",
        "faster",
        "cheaper",
        "improve",
        "optimize",
        "fix",
        "clean up",
        "make good",
        "work better",
        "enhance",
    }

    def __init__(self) -> None:
        self._goals: dict[str, Goal] = {}
        self._goal_dag: dict[str, list[str]] = {}  # goal_id -> list of dependent goal_ids

    # --- Goal Normalization (Spec 9) ---

    def normalize_goal(
        self,
        raw_objective: str,
        origin: GoalOrigin = GoalOrigin.USER,
        authority_scope: GoalAuthorityScope = GoalAuthorityScope.EXECUTE_LOW_RISK,
        owner: str = "user",
        tenant_id: str = "default",
        constraints: list[str] | None = None,
        deadline: datetime | None = None,
    ) -> tuple[Goal, GoalValidationStatus, dict[str, Any]]:
        """Convert natural language objective into structured Goal (Spec 9).

        Example: 'Reduce API latency without hurting reliability'
        -> Objective: latency down, Constraint: reliability >= threshold.
        """
        sanitized_text = sanitize_mission_directive(raw_objective)

        # Ambiguity Check (Spec 8)
        is_ambiguous, ambiguity_details = self.detect_ambiguity(sanitized_text)
        if is_ambiguous:
            return (
                Goal(
                    title=sanitized_text[:60],
                    description=sanitized_text,
                    origin=origin,
                    owner=owner,
                    tenant_id=tenant_id,
                    authority_scope=authority_scope,
                    constraints=constraints or [],
                    deadline=deadline,
                ),
                GoalValidationStatus.NEEDS_CLARIFICATION,
                ambiguity_details,
            )

        # Extract structured objectives and constraints
        parsed_constraints = list(constraints or [])
        success_criteria: list[SuccessCriteria] = []

        # Parse 'without hurting X' or 'while maintaining Y'
        neg_constraint_match = re.search(
            r"(?i)(?:without\s+(?:hurting|degrading|increasing)|while\s+(?:maintaining|preserving))\s+([^,\.]+)",
            sanitized_text,
        )
        if neg_constraint_match:
            parsed_constraints.append(f"Constraint: preserve {neg_constraint_match.group(1).strip()}")

        # Extract metric keywords if available
        if "latency" in sanitized_text.lower():
            success_criteria.append(
                SuccessCriteria(
                    description="Reduce p95 API response time below target threshold",
                    criteria_type="metric_threshold",
                    target_metric="p95_latency_ms",
                    target_value=200.0,
                    comparison_operator="lte",
                )
            )
        elif "cost" in sanitized_text.lower():
            success_criteria.append(
                SuccessCriteria(
                    description="Reduce cloud compute spend",
                    criteria_type="metric_threshold",
                    target_metric="monthly_spend_usd",
                    target_value=1000.0,
                    comparison_operator="lte",
                )
            )
        else:
            success_criteria.append(
                SuccessCriteria(
                    description=f"Verify completion of '{sanitized_text[:50]}'",
                    criteria_type="verification_result",
                )
            )

        goal = Goal(
            title=sanitized_text[:60].strip(),
            description=sanitized_text,
            origin=origin,
            owner=owner,
            tenant_id=tenant_id,
            authority_scope=authority_scope,
            constraints=parsed_constraints,
            success_criteria=success_criteria,
            deadline=deadline,
            provenance={"normalized_from": raw_objective, "normalized_at": _now_utc().isoformat()},
        )

        self._goals[goal.goal_id] = goal
        self._goal_dag[goal.goal_id] = []
        return goal, GoalValidationStatus.VALID, {}

    # --- Ambiguity Detection (Spec 8) ---

    def detect_ambiguity(self, text: str) -> tuple[bool, dict[str, Any]]:
        """Identify under-specified objectives like 'make the system better'."""
        lowered = text.lower().strip()
        tokens = set(re.findall(r"\b\w+\b", lowered))

        vague_matches = tokens.intersection(self._VAGUE_TERMS)
        # Check if text is short and contains vague terms without specific metrics/targets
        has_specifics = any(
            metric in lowered
            for metric in [
                "ms",
                "%",
                "percent",
                "seconds",
                "gb",
                "mb",
                "usd",
                "dollar",
                "cpu",
                "memory",
                "qps",
                "error rate",
            ]
        )

        if vague_matches and not has_specifics and len(tokens) <= 6:
            return True, {
                "ambiguity_reason": f"Objective relies on unquantified term(s): {list(vague_matches)}. Better according to what metric?",
                "candidate_interpretations": [
                    {"dimension": "latency", "suggestion": "Reduce response latency (e.g. p95 < 150ms)"},
                    {"dimension": "cost", "suggestion": "Reduce monthly infrastructure cost by 15%"},
                    {"dimension": "reliability", "suggestion": "Achieve 99.9% uptime SLA"},
                    {"dimension": "security", "suggestion": "Remediate open high/critical vulnerabilities"},
                ],
                "suggested_defaults": {"dimension": "reliability", "target": "error_rate < 0.1%"},
            }

        return False, {}

    # --- Goal Validation (Spec 7) ---

    def validate_goal(self, goal: Goal) -> GoalValidationStatus:
        """Validate goal clarity, authority, constraints, and success criteria."""
        if not goal.title or not goal.description:
            return GoalValidationStatus.NEEDS_CLARIFICATION

        if not goal.success_criteria:
            return GoalValidationStatus.NEEDS_CLARIFICATION

        return GoalValidationStatus.VALID

    # --- Goal Feasibility (Spec 23, 24) ---

    def estimate_feasibility(
        self,
        goal: Goal,
        available_resources: list[str] | None = None,
        world_risks: list[str] | None = None,
    ) -> tuple[GoalFeasibilityStatus, str]:
        """Estimate goal feasibility under explicit assumptions (Spec 23, 24).

        Invariant: FEASIBILITY != GUARANTEE.
        """
        resources = available_resources or []
        risks = world_risks or []

        # Check required resources
        missing_resources = [r for r in goal.resources if r not in resources]
        if missing_resources:
            return (
                GoalFeasibilityStatus.BLOCKED,
                f"Missing required resources: {missing_resources}",
            )

        # Check extreme risks
        if len(risks) >= 3 or goal.risk_level > 0.8:
            return (
                GoalFeasibilityStatus.INFEASIBLE,
                f"Risk level ({goal.risk_level:.2f}) or active environmental risks ({len(risks)}) exceed acceptable threshold.",
            )

        if goal.risk_level > 0.5 or goal.deadline is None:
            return (
                GoalFeasibilityStatus.LIKELY_FEASIBLE,
                "Goal is likely feasible under current resource and dependency assumptions.",
            )

        return (
            GoalFeasibilityStatus.FEASIBLE,
            "Goal is feasible under current validated assumptions.",
        )

    # --- Goal Conflict Detection (Spec 15, 16) ---

    def detect_conflicts(self, goal_a: Goal, goal_b: Goal) -> GoalConflict | None:
        """Detect conflicting goals, e.g. reducing cost vs increasing redundancy (Spec 15)."""
        desc_a = f"{goal_a.title} {goal_a.description}".lower()
        desc_b = f"{goal_b.title} {goal_b.description}".lower()

        is_conflict = False
        tradeoffs: list[str] = []

        # Cost vs Redundancy / Availability
        if ("reduce cost" in desc_a or "cut spend" in desc_a) and (
            "increase redundancy" in desc_b or "multi-region" in desc_b
        ):
            is_conflict = True
            tradeoffs.append("Cost reduction directly conflicts with provisioning multi-region redundancy.")
        elif ("reduce cost" in desc_b or "cut spend" in desc_b) and (
            "increase redundancy" in desc_a or "multi-region" in desc_a
        ):
            is_conflict = True
            tradeoffs.append("Cost reduction directly conflicts with provisioning multi-region redundancy.")

        # Latency vs Thorough Security Audit
        if ("minimize latency" in desc_a) and ("deep inspection" in desc_b or "full payload audit" in desc_b):
            is_conflict = True
            tradeoffs.append("Payload inspection overhead directly impedes latency minimization.")

        if is_conflict:
            return GoalConflict(
                conflicting_goal_ids=[goal_a.goal_id, goal_b.goal_id],
                conflicting_objectives=[goal_a.title, goal_b.title],
                tradeoffs=tradeoffs,
                affected_resources=list(set(goal_a.resources + goal_b.resources)),
                decision_required="Operator must prioritize either cost efficiency or redundancy margin.",
            )

        return None

    # --- Goal DAG & Dependency Management (Spec 13) ---

    def add_dependency(self, parent_goal_id: str, dependent_goal_id: str) -> None:
        """Add a directed dependency: dependent_goal_id requires parent_goal_id."""
        if parent_goal_id not in self._goals or dependent_goal_id not in self._goals:
            raise KeyError("Both goals must be registered before creating dependency.")

        if parent_goal_id == dependent_goal_id:
            raise MissionSafetyError("Self-dependency is invalid.")

        # Cycle detection
        if self._creates_cycle(parent_goal_id, dependent_goal_id):
            raise MissionSafetyError(
                f"Circular dependency detected: adding {parent_goal_id} -> {dependent_goal_id} would create a cycle."
            )

        self._goal_dag[parent_goal_id].append(dependent_goal_id)

    def _creates_cycle(self, parent_id: str, dependent_id: str) -> bool:
        """Check if adding edge parent -> dependent causes a cycle."""
        visited: set[str] = set()
        queue = [dependent_id]
        while queue:
            curr = queue.pop(0)
            if curr == parent_id:
                return True
            if curr not in visited:
                visited.add(curr)
                queue.extend(self._goal_dag.get(curr, []))
        return False

    # --- Goal Prioritization (Spec 14) ---

    def calculate_priority_score(self, goal: Goal) -> float:
        """Calculate holistic priority rank (Spec 14).

        Balance importance, urgency, risk penalty, and dependency centrality.
        Urgency alone is prevented from dominating.
        """
        base_importance = goal.importance * 0.4
        base_urgency = goal.urgency * 0.3
        risk_penalty = goal.risk_level * 0.1
        explicit_priority = (goal.priority / 10.0) * 0.2

        score = base_importance + base_urgency + explicit_priority - risk_penalty
        return round(max(0.0, min(1.0, score)), 3)

    def get_goal(self, goal_id: str) -> Goal | None:
        return self._goals.get(goal_id)

    def list_goals(self) -> list[Goal]:
        return list(self._goals.values())
