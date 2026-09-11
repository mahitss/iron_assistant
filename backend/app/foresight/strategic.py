"""Strategic risk and opportunity registers, decision impact analysis, reversibility, and monitoring plans (Task 65, Spec 38-41, 50-56)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.foresight.schemas import (
    ForesightHorizon,
    MonitoringPlan,
    ReversibilityClass,
    StrategicOpportunity,
    StrategicRisk,
)

logger = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class StrategicForesightManager:
    """Manages strategic risks, opportunities, decision impacts, and bounded monitoring plans (Spec 50-56)."""

    def __init__(self) -> None:
        self._risks: dict[str, StrategicRisk] = {}
        self._opportunities: dict[str, StrategicOpportunity] = {}
        self._monitoring_plans: dict[str, MonitoringPlan] = {}

    # --- Risk Register ---

    def register_risk(
        self,
        title: str,
        description: str,
        probability: float = 0.5,
        impact: float = 0.7,
        time_horizon: ForesightHorizon = ForesightHorizon.MID_FUTURE_1M,
        dependencies: list[str] | None = None,
        mitigations: list[str] | None = None,
        evidence: list[str] | None = None,
    ) -> StrategicRisk:
        """Add an entry to the Strategic Risk Register (Spec 50)."""
        risk = StrategicRisk(
            title=title,
            description=description,
            probability=min(1.0, max(0.0, probability)),
            impact=min(1.0, max(0.0, impact)),
            time_horizon=time_horizon,
            dependencies=dependencies or [],
            mitigations=mitigations or ["Monitor leading indicators and configure fallback routes"],
            evidence=evidence or ["Extrapolated from architectural coupling"],
            status="OPEN",
        )
        self._risks[risk.risk_id] = risk
        logger.info("STRATEGIC_RISK_REGISTERED: id=%s title='%s' impact=%.2f", risk.risk_id, title, impact)
        return risk

    # --- Opportunity Register ---

    def register_opportunity(
        self,
        title: str,
        description: str,
        potential_value: float = 0.7,
        time_horizon: ForesightHorizon = ForesightHorizon.MID_FUTURE_1M,
        dependencies: list[str] | None = None,
        risks: list[str] | None = None,
        optionality_score: float = 0.8,
    ) -> StrategicOpportunity:
        """Add an entry to the Strategic Opportunity Register (Spec 51, 53).

        Invariant: RISK VS REWARD (Spec 52). Kairo models optionality and value, not purely defensive behavior.
        """
        opp = StrategicOpportunity(
            title=title,
            description=description,
            potential_value=min(1.0, max(0.0, potential_value)),
            time_horizon=time_horizon,
            dependencies=dependencies or [],
            risks=risks or [],
            optionality_score=min(1.0, max(0.0, optionality_score)),
            status="IDENTIFIED",
        )
        self._opportunities[opp.opportunity_id] = opp
        logger.info(
            "STRATEGIC_OPPORTUNITY_REGISTERED: id=%s title='%s' optionality=%.2f",
            opp.opportunity_id,
            title,
            optionality_score,
        )
        return opp

    # --- Decision Impact & Reversibility Analysis ---

    def analyze_decision_impact(
        self,
        decision_title: str,
        reversibility: ReversibilityClass = ReversibilityClass.REVERSIBLE,
        target_entities: list[str] | None = None,
    ) -> dict[str, Any]:
        """Analyze multi-order effects, feedback loops, and reversibility for a decision (Spec 38-40, 54)."""
        entities = target_entities or []

        # 1. Second and third-order effects
        second_order_effects = [
            f"Altered resource contention on {e} under peak shifts" for e in entities[:2]
        ] or ["Downstream dependent services observe altered latency distribution"]
        third_order_effects = [
            "User traffic volume expands in response to improved response times (Jevons Paradox)",
            "Maintenance cadence adjusts as operational dependencies shift",
        ]

        # 2. Feedback loop detection (Spec 40)
        feedback_loops = [
            {
                "loop_type": "BALANCING_OR_REINFORCING",
                "description": "Decision -> lower latency -> higher user request volume -> increased memory utilization -> latency rebounds",
                "stabilizing_factor": "Auto-scaling concurrency throttling limits resource exhaustion",
            }
        ]

        return {
            "decision": decision_title,
            "reversibility": reversibility.value,
            "direct_impact": f"Primary modification targeted at {len(entities)} entities",
            "second_order_effects": second_order_effects,
            "third_order_effects": third_order_effects,
            "feedback_loops": feedback_loops,
            "requires_human_approval": reversibility == ReversibilityClass.IRREVERSIBLE,
        }

    # --- Foresight Question Generation ---

    def generate_foresight_questions(
        self,
        context_goal: str,
        assumptions: list[str] | None = None,
    ) -> list[str]:
        """Generate probing strategic foresight questions (Spec 55)."""
        assump = assumptions or ["Workload remains stable", "Upstream API contracts remain unchanged"]
        questions = [
            f"What could make '{context_goal}' fail if external conditions deteriorate?",
            f"Which assumption is most fragile: '{assump[0]}' or underlying dependency availability?",
            "What critical dependency could become a throughput bottleneck over a 6-month horizon?",
            "What external architectural change could invalidate this strategy?",
            "Which early signal should Kairo monitor to detect assumption breakdown 7 days in advance?",
            "What decision today preserves the most future architectural optionality?",
        ]
        return questions

    # --- Bounded Monitoring Plans ---

    def create_monitoring_plan(
        self,
        target_id: str,
        target_type: str = "risk",
        signals: list[str] | None = None,
        thresholds: dict[str, float] | None = None,
        frequency_seconds: int = 300,
        ttl_days: int = 30,
    ) -> MonitoringPlan:
        """Create a bounded, expiring monitoring plan (Spec 56: Do not monitor everything forever)."""
        now = _now_utc()
        plan = MonitoringPlan(
            target_id=target_id,
            target_type=target_type,
            signals=signals or ["latency_p99", "error_rate", "memory_headroom_pct"],
            thresholds=thresholds or {"latency_p99": 500.0, "error_rate": 0.02},
            frequency_seconds=frequency_seconds,
            expiry=now + timedelta(days=ttl_days),
            is_active=True,
        )
        self._monitoring_plans[plan.plan_id] = plan
        logger.info(
            "MONITORING_PLAN_CREATED: id=%s target=%s expiry=%s", plan.plan_id, target_id, plan.expiry
        )
        return plan

    def list_risks(self, status: str = "OPEN") -> list[StrategicRisk]:
        """List open strategic risks."""
        return [r for r in self._risks.values() if r.status == status or not status]

    def list_opportunities(self, status: str = "IDENTIFIED") -> list[StrategicOpportunity]:
        """List strategic opportunities."""
        return [o for o in self._opportunities.values() if o.status == status or not status]

    def clear(self) -> None:
        """Clear cache (for tests)."""
        self._risks.clear()
        self._opportunities.clear()
        self._monitoring_plans.clear()


strategic_foresight_manager = StrategicForesightManager()
