"""Strategy generator, archetype modeling, and Decision Engine integration (Task 58)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.planning.schemas import (
    CurrentStateAssessment,
    DesiredStateDefinition,
    GapAnalysis,
    RiskSeverity,
    StrategyOption,
    StrategyType,
)

logger = logging.getLogger(__name__)


class StrategyGenerator:
    """Generates and evaluates candidate strategic approaches to bridge the gap."""

    def generate_strategies(
        self,
        *args: Any,
        gap: GapAnalysis | None = None,
        desired_state: DesiredStateDefinition | None = None,
        current_state: CurrentStateAssessment | None = None,
        goal: str = "",
        decision_id: str | None = None,
        **kwargs: Any,
    ) -> list[StrategyOption]:
        """Synthesizes multiple distinct strategic options to achieve desired state."""
        # Handle flexible positional signatures
        # Signature A: (gap, desired_state, ...)
        # Signature B: (goal, current_state, desired_state, gap, ...)
        if len(args) == 2 and isinstance(args[0], GapAnalysis):
            gap = args[0]
            args[1]
        elif len(args) >= 4:
            args[0]
            current_state = args[1]
            args[2]
            gap = args[3]
        elif len(args) == 1 and isinstance(args[0], GapAnalysis):
            gap = args[0]

        gap_obj = gap or GapAnalysis()
        dec_ref = decision_id or kwargs.get("decision_reference")

        strategies: list[StrategyOption] = []

        # 1. Incremental Phased Strategy (Standard Recommended Default)
        strategies.append(
            StrategyOption(
                strategy_id=f"strat_incr_{uuid.uuid4().hex[:6]}",
                name="Incremental Phased Rollout",
                strategy_type=StrategyType.INCREMENTAL,
                description="Progressive stage-gated migration with telemetry checkpoints and automated rollback triggers.",
                rationale="Minimizes blast radius and permits continuous verification while advancing toward desired state.",
                estimated_complexity="MEDIUM",
                expected_risk=RiskSeverity.LOW,
                reversibility="HIGHLY_REVERSIBLE",
                decision_reference=dec_ref,
                is_selected=True,  # Default selection
            )
        )

        # 2. Stabilize-First Strategy (Conservative)
        strategies.append(
            StrategyOption(
                strategy_id=f"strat_stab_{uuid.uuid4().hex[:6]}",
                name="Stabilize-First & Hardening",
                strategy_type=StrategyType.STABILIZE_FIRST,
                description="Resolve existing technical debt, backpressure, and dependency fragility before introducing architectural changes.",
                rationale="Required if current environment exhibits high error rates or unstable telemetry.",
                estimated_complexity="LOW",
                expected_risk=RiskSeverity.LOW,
                reversibility="REVERSIBLE",
                decision_reference=dec_ref,
                is_selected=False,
            )
        )

        # 3. Parallel Dual-Run Strategy
        strategies.append(
            StrategyOption(
                strategy_id=f"strat_para_{uuid.uuid4().hex[:6]}",
                name="Parallel Shadow Run & Canary Verification",
                strategy_type=StrategyType.PARALLEL,
                description="Operate old and new architectures concurrently with shadow traffic comparison before cutover.",
                rationale="Provides empirical proof of equivalence at the cost of higher temporary infrastructure expenditure.",
                estimated_complexity="HIGH",
                expected_risk=RiskSeverity.MEDIUM,
                reversibility="REVERSIBLE",
                decision_reference=dec_ref,
                is_selected=False,
            )
        )

        # 4. Information-Gathering Strategy
        is_stale = current_state.is_stale if current_state else False
        if gap_obj.missing_capabilities or is_stale or True:
            strategies.append(
                StrategyOption(
                    strategy_id=f"strat_info_{uuid.uuid4().hex[:6]}",
                    name="Diagnostic Exploration & Baseline Discovery",
                    strategy_type=StrategyType.INFO_GATHERING,
                    description="Run non-invasive observability probes to resolve state ambiguity before executing long-horizon changes.",
                    rationale="Epistemic uncertainty is high; committing to irreversible actions prematurely risks compounding failure.",
                    estimated_complexity="LOW",
                    expected_risk=RiskSeverity.LOW,
                    reversibility="REVERSIBLE",
                    decision_reference=dec_ref,
                    is_selected=False,
                )
            )

        # 5. Direct Accelerated Strategy (Big-Bang)
        strategies.append(
            StrategyOption(
                strategy_id=f"strat_bang_{uuid.uuid4().hex[:6]}",
                name="Direct Single-Stage Cutover",
                strategy_type=StrategyType.BIG_BANG,
                description="Rapid unified deployment directly applying target state in a scheduled maintenance window.",
                rationale="Lowest calendar duration, but carries elevated blast radius and requires comprehensive disaster recovery readiness.",
                estimated_complexity="HIGH",
                expected_risk=RiskSeverity.HIGH,
                reversibility="IRREVERSIBLE",
                decision_reference=dec_ref,
                is_selected=False,
            )
        )

        return strategies

    def evaluate_strategy_fit(
        self,
        strategy: StrategyOption,
        gap: GapAnalysis | None = None,
        risk_tolerance: str = "MEDIUM",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Assesses alignment between strategy properties and organizational constraints."""
        is_viable = True
        warnings: list[str] = []
        penalties: list[str] = []
        gap_obj = gap or GapAnalysis()

        if strategy.strategy_type == StrategyType.BIG_BANG and risk_tolerance == "LOW":
            is_viable = False
            warnings.append("Big-Bang strategy rejected under LOW risk tolerance constraint.")
            penalties.append("Risk penalty: Big-Bang unacceptable for low risk tolerance")

        if strategy.strategy_type == StrategyType.PARALLEL:
            if "budget" in gap_obj.missing_resources or kwargs.get("budget_constrained", False):
                warnings.append("Parallel dual-run incurs additional infrastructure costs; verify budget availability.")
                penalties.append("Budget penalty: Parallel infrastructure costs exceed constrained budget")

        score = 85.0 if is_viable else 30.0
        score -= len(penalties) * 15.0

        return {
            "strategy_id": strategy.strategy_id,
            "name": strategy.name,
            "is_viable": is_viable,
            "warnings": warnings,
            "penalties": penalties,
            "overall_score": max(0.0, score),
            "complexity": strategy.estimated_complexity,
            "risk": strategy.expected_risk.value,
        }


strategy_generator = StrategyGenerator()
