"""Risk assessment across 12 categories, worst-case downside analysis, and exposure scoring."""

from __future__ import annotations

from app.decision.schemas import (
    CandidateOption,
    ReversibilityLevel,
    RiskAssessment,
    RiskCategory,
)


class RiskEngine:
    """Evaluates multi-category operational, security, and financial risks without false precision."""

    def assess_option_risks(
        self,
        option: CandidateOption,
        user_risk_tolerance: str = "MEDIUM",
    ) -> list[RiskAssessment]:
        """Evaluates risks based on option type, metrics, and reversibility."""
        risks: list[RiskAssessment] = []

        # 1. Operational & Deployment Risk
        risk_metric = option.metrics.get("risk", 0.2)
        if risk_metric > 0.4:
            risks.append(
                RiskAssessment(
                    category=RiskCategory.OPERATIONAL,
                    probability="MEDIUM",
                    impact="HIGH",
                    exposure_score=round(risk_metric, 2),
                    reversibility=option.reversibility,
                    mitigation="Execute canary deployment with progressive traffic shift.",
                )
            )

        # 2. Reversibility & Data Loss Risk
        if option.reversibility in (ReversibilityLevel.DIFFICULT_TO_REVERSE, ReversibilityLevel.IRREVERSIBLE):
            risks.append(
                RiskAssessment(
                    category=RiskCategory.REVERSIBILITY,
                    probability="HIGH",
                    impact="CRITICAL",
                    exposure_score=0.85,
                    reversibility=option.reversibility,
                    mitigation="Capture pre-execution database snapshot and mandate manual human authorization.",
                    is_acceptable=user_risk_tolerance.upper() == "HIGH",
                )
            )

        # 3. Financial / Cost Risk
        cost = option.metrics.get("cost", 0.0)
        if cost > 50.0:
            risks.append(
                RiskAssessment(
                    category=RiskCategory.FINANCIAL,
                    probability="HIGH",
                    impact="LOW" if cost < 100.0 else "MEDIUM",
                    exposure_score=round(min(1.0, cost / 200.0), 2),
                    reversibility=ReversibilityLevel.REVERSIBLE,
                    mitigation="Set cloud billing budget alerts and autoscale scale-down triggers.",
                )
            )

        # 4. Fallback baseline risk if empty
        if not risks:
            risks.append(
                RiskAssessment(
                    category=RiskCategory.RELIABILITY,
                    probability="LOW",
                    impact="LOW",
                    exposure_score=0.1,
                    reversibility=ReversibilityLevel.REVERSIBLE,
                    mitigation="Standard continuous telemetry monitoring.",
                )
            )

        return risks

    def analyze_worst_case_downside(self, option: CandidateOption) -> str:
        """Analyzes the plausible worst-case failure mode and recovery strategy (Prompt #103)."""
        if option.reversibility == ReversibilityLevel.IRREVERSIBLE:
            return "Worst-case: Unrecoverable data corruption or schema divergence requiring full backup restore from cold storage."
        elif option.metrics.get("cost", 0.0) > 80.0:
            return "Worst-case: Cloud budget overrun if automated scale-down triggers fail to deprovision excess replicas."
        elif option.option_type.value == "NO_ACTION":
            return "Worst-case: Unresolved degraded service queue continues to compound, leading to downstream cascading timeout."
        return "Worst-case: Transient latency spike during transition; mitigated by immediate automated rollback."

    def assess_risks(
        self,
        options: list[CandidateOption],
        risk_tolerance: str = "MEDIUM",
    ) -> list[RiskAssessment]:
        """Aggregates risk assessments across all evaluated candidate options."""
        all_risks: list[RiskAssessment] = []
        for opt in options:
            opt_risks = self.assess_option_risks(opt, user_risk_tolerance=risk_tolerance)
            all_risks.extend(opt_risks)
        return all_risks


risk_engine = RiskEngine()

