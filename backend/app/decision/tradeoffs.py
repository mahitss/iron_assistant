"""Multi-objective Pareto frontier identification and human-readable trade-off explanations."""

from __future__ import annotations

from typing import Any

from app.decision.schemas import CandidateOption, Objective, Tradeoff


class TradeoffEngine:
    """Analyzes multi-objective tensions and identifies Pareto-optimal vs dominated options."""

    def find_pareto_options(
        self,
        options: list[CandidateOption],
        objectives: list[Objective],
    ) -> tuple[list[str], list[str]]:
        """Identifies non-dominated (Pareto optimal) vs dominated candidate options.

        Returns (pareto_optimal_ids, dominated_ids).
        """
        feasible = [o for o in options if o.is_feasible]
        if not feasible:
            return [], []

        dominated: set[str] = set()

        for a in feasible:
            for b in feasible:
                if a.option_id == b.option_id:
                    continue

                # Check if A strictly dominates B
                better_or_equal = True
                strictly_better = False

                for obj in objectives:
                    k = obj.name.lower()
                    val_a = a.metrics.get(k, 0.0)
                    val_b = b.metrics.get(k, 0.0)

                    if "MINIMIZE" in obj.direction.upper():
                        if val_a > val_b:
                            better_or_equal = False
                            break
                        elif val_a < val_b:
                            strictly_better = True
                    else:  # MAXIMIZE
                        if val_a < val_b:
                            better_or_equal = False
                            break
                        elif val_a > val_b:
                            strictly_better = True

                if better_or_equal and strictly_better:
                    dominated.add(b.option_id)

        pareto = [o.option_id for o in feasible if o.option_id not in dominated]
        return pareto, list(dominated)

    def explain_tradeoffs(
        self,
        option_a: CandidateOption,
        option_b: CandidateOption,
    ) -> list[Tradeoff]:
        """Generates structured trade-off explanations comparing two candidate options."""
        tradeoffs: list[Tradeoff] = []

        cost_a = option_a.metrics.get("cost", 0.0)
        cost_b = option_b.metrics.get("cost", 0.0)
        lat_a = option_a.metrics.get("latency", 0.0)
        lat_b = option_b.metrics.get("latency", 0.0)
        rel_a = option_a.metrics.get("reliability", 0.0)
        rel_b = option_b.metrics.get("reliability", 0.0)

        # 1. Cost vs Latency
        if cost_a > cost_b and lat_a < lat_b:
            tradeoffs.append(
                Tradeoff(
                    dimension_a="Cost",
                    dimension_b="Latency",
                    explanation=f"'{option_a.name}' offers lower latency ({lat_a}ms vs {lat_b}ms) at higher cost (${cost_a} vs ${cost_b}).",
                    tension_level="HIGH",
                )
            )

        # 2. Reliability vs Cost
        if rel_a > rel_b and cost_a > cost_b:
            tradeoffs.append(
                Tradeoff(
                    dimension_a="Reliability",
                    dimension_b="Cost",
                    explanation=f"'{option_a.name}' delivers higher reliability ({rel_a:.2f} vs {rel_b:.2f}) but incurs additional expenditure.",
                    tension_level="MEDIUM",
                )
            )

        return tradeoffs

    def analyze_tradeoffs(
        self,
        options: list[CandidateOption],
        evaluations: list[Any],
        objectives: list[Objective],
    ) -> tuple[list[Tradeoff], list[str]]:
        """Identifies Pareto frontier and derives structured trade-off explanations."""
        pareto_ids, dominated_ids = self.find_pareto_options(options, objectives)
        tradeoffs: list[Tradeoff] = []
        feasible = [o for o in options if o.is_feasible]
        if len(feasible) >= 2:
            tradeoffs = self.explain_tradeoffs(feasible[0], feasible[1])
        return tradeoffs, dominated_ids


tradeoff_engine = TradeoffEngine()

