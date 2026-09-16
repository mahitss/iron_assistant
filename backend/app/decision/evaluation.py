"""Multi-criteria evaluation, Pareto frontier, and trade-off analysis engine (Task 94 Phases 7 & 8).

Invariants:
- Never collapse multidimensional trade-offs into a single fake universal scalar.
- Hard constraints are strictly non-compensable (violation = infeasible).
- NO_ACTION is a first-class citizen and must always be considered.
- Explicitly computes non-dominated Pareto frontiers and tension pairs.
"""

from __future__ import annotations

from typing import Any

from app.decision.domain import (
    ConstraintCategory,
    DecisionConstraint,
    DecisionOption,
    DecisionType,
)


class DecisionEvaluationEngine:
    """Evaluates candidate options across multi-criteria dimensions and computes Pareto dominance."""

    def evaluate_options(
        self,
        options: list[DecisionOption],
        constraints: list[DecisionConstraint] | None = None,
        objective: str = "",
    ) -> list[DecisionOption]:
        """Alias for evaluate_candidates matching high-level evaluation calls."""
        return self.evaluate_candidates(options, constraints or [])

    def compute_pareto_frontier(self, options: list[DecisionOption]) -> list[DecisionOption]:
        """Compute and return the non-dominated Pareto frontier."""
        evaluated = self.evaluate_candidates(options, [])
        return [o for o in evaluated if o.is_feasible and not o.is_dominated]

    def evaluate_candidates(
        self,
        options: list[DecisionOption],
        constraints: list[DecisionConstraint],
    ) -> list[DecisionOption]:
        """Score each option across individual criteria, check constraints, and compute Pareto frontier."""
        # 1. Ensure at least one NO_ACTION or baseline option exists (Phase 5)
        has_no_action = any(opt.option_type == DecisionType.NO_ACTION or opt.id == "opt_no_action" for opt in options)
        evaluated_options = list(options)
        if not has_no_action:
            evaluated_options.append(
                DecisionOption(
                    option_id="opt_no_action",
                    name="NO_ACTION (Status Quo)",
                    description="Preserve current system state without active intervention.",
                    option_type=DecisionType.NO_ACTION,
                    reversibility="REVERSIBLE",
                    confidence=1.0,
                    expected_outcome="Maintain status quo. Incur zero operational risk or execution cost.",
                )
            )

        # 2. Score individual criteria and evaluate constraints for each candidate
        for opt in evaluated_options:
            self._evaluate_option_constraints(opt, constraints)
            self._calculate_multicriteria_scores(opt)

        # 3. Compute Pareto Dominance (Phase 8)
        self._compute_pareto_dominance(evaluated_options)

        return evaluated_options

    def _evaluate_option_constraints(
        self, option: DecisionOption, constraints: list[DecisionConstraint]
    ) -> None:
        """Check hard and soft constraints against the candidate option."""
        for c in constraints:
            is_hard = getattr(c, "is_hard", True) or c.category in (
                ConstraintCategory.HARD_CONSTRAINT,
                ConstraintCategory.RESOURCE_BUDGET,
            )
            if is_hard:
                # Cost / Budget constraint check
                if c.threshold is not None:
                    if option.projected_cost is not None and option.projected_cost > c.threshold:
                        option.is_feasible = False
                        msg = f"Projected cost {option.projected_cost} exceeds limit {c.threshold}"
                        option.rejection_reason = msg
                        option.constraint_violations.append(msg)
                        return

                if "no_destructive" in c.name.lower() and option.reversibility == "IRREVERSIBLE":
                    option.is_feasible = False
                    msg = f"Violates hard constraint: {c.statement}"
                    option.rejection_reason = msg
                    option.constraint_violations.append(msg)
                    return

    def _calculate_multicriteria_scores(self, option: DecisionOption) -> None:
        """Compute distinct multidimensional criteria scores (0.0 to 1.0)."""
        scores: dict[str, float] = {}

        # 1. Objective Alignment
        if option.alignment_score is not None:
            scores["objective_alignment"] = option.alignment_score
        elif option.option_type == DecisionType.NO_ACTION:
            scores["objective_alignment"] = 0.5
        elif not option.is_feasible:
            scores["objective_alignment"] = 0.0
        else:
            scores["objective_alignment"] = round(option.confidence * 0.9, 2)

        # 2. Risk (higher score = lower risk / safer)
        if option.risk_score is not None:
            # lower risk -> higher safety score
            scores["risk_score"] = round(max(0.0, 1.0 - option.risk_score), 2)
        elif option.option_type == DecisionType.NO_ACTION:
            scores["risk_score"] = 1.0  # Zero active execution risk
        elif option.reversibility == "IRREVERSIBLE":
            scores["risk_score"] = 0.2
        else:
            scores["risk_score"] = 0.8

        # 3. Reversibility
        if option.reversibility_score is not None:
            scores["reversibility_score"] = option.reversibility_score
        elif option.reversibility == "REVERSIBLE" or option.option_type == DecisionType.NO_ACTION:
            scores["reversibility_score"] = 1.0
        elif option.reversibility == "PARTIAL":
            scores["reversibility_score"] = 0.6
        else:
            scores["reversibility_score"] = 0.1

        # 4. Resource Efficiency (lower cost = higher efficiency)
        if option.resource_efficiency is not None:
            scores["resource_efficiency"] = option.resource_efficiency
        else:
            profile = option.estimated_resource_profile
            cost = profile.get("cost_score", 0.1 if option.option_type == DecisionType.NO_ACTION else 0.4)
            scores["resource_efficiency"] = round(max(0.0, 1.0 - cost), 2)

        # 5. Confidence
        scores["confidence_score"] = round(float(option.confidence), 2)

        option.scores = scores

        # Identify key trade-offs
        tradeoffs = []
        if scores["objective_alignment"] > 0.8 and scores["risk_score"] < 0.4:
            tradeoffs.append({
                "dimension_a": "Objective Alignment (High)",
                "dimension_b": "Risk (Elevated)",
                "explanation": "Option aggressively advances the objective but introduces significant operational risk.",
            })
        if option.option_type == DecisionType.NO_ACTION:
            tradeoffs.append({
                "dimension_a": "Zero Risk & Cost",
                "dimension_b": "Zero Objective Advancement",
                "explanation": "Doing nothing avoids errors but makes no active progress toward the goal.",
            })

        option.tradeoffs = tradeoffs

    def _compute_pareto_dominance(self, options: list[DecisionOption]) -> None:
        """Mark dominated options across the multi-criteria vector space."""
        criteria_keys = ["objective_alignment", "risk_score", "reversibility_score", "resource_efficiency"]

        feasible_options = [o for o in options if o.is_feasible]

        for i, opt_a in enumerate(feasible_options):
            for j, opt_b in enumerate(feasible_options):
                if i == j:
                    continue

                # Check if opt_b strictly dominates opt_a
                b_better_or_equal_all = True
                b_strictly_better_any = False

                for key in criteria_keys:
                    val_a = opt_a.scores.get(key, 0.0)
                    val_b = opt_b.scores.get(key, 0.0)
                    if val_b < val_a:
                        b_better_or_equal_all = False
                        break
                    if val_b > val_a:
                        b_strictly_better_any = True

                if b_better_or_equal_all and b_strictly_better_any:
                    opt_a.is_dominated = True
                    break
