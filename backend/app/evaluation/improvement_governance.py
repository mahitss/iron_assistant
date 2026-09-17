"""Governed Improvement Engine, Controlled Experiments, Evaluation Gates & Subsystem Handoff.
Task 104 Sections 27, 28, 29, 30, 31, 42, 45.
"""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any, Dict, List, Optional
import uuid

from app.evaluation.domain import (
    EvaluationGate,
    EvaluationReview,
    GateStatus,
    ImprovementExperiment,
    ImprovementProposal,
    RegressionFinding,
    ReviewStatus,
)

logger = logging.getLogger("kairo.evaluation.improvement_governance")


class ImprovementGovernanceEngine:
    """Manages improvement proposals, controlled experiments, and non-authoritative governance handoffs."""

    def __init__(self) -> None:
        self.proposals: dict[str, ImprovementProposal] = {}
        self.experiments: dict[str, ImprovementExperiment] = {}
        self.gates: dict[str, EvaluationGate] = {}
        self.reviews: dict[str, EvaluationReview] = {}

    def create_proposal_from_regressions(
        self,
        title: str,
        regressions: list[RegressionFinding],
        baseline_id: str,
        target_area: str = "capability_configuration",
        proposed_change: Optional[dict[str, Any]] = None,
    ) -> ImprovementProposal:
        """Generates a formal ImprovementProposal from detected regressions (Section 27).
        Invariant: Proposal != Implementation / Deployment.
        """
        affected_capabilities: list[str] = []
        affected_metrics: list[str] = []
        for r in regressions:
            affected_metrics.append(r.metric_name)
            affected_capabilities.extend(r.affected_capabilities)

        affected_capabilities = list(set(affected_capabilities))
        affected_metrics = list(set(affected_metrics))

        prob_summary = f"Detected {len(regressions)} regression(s) affecting metrics: {', '.join(affected_metrics)}."
        change_dict = proposed_change or {
            "action": "adjust_parameters",
            "suggested_retry_strategy": "exponential_backoff",
            "target_capabilities": affected_capabilities,
        }

        proposal = ImprovementProposal(
            title=title,
            problem_statement=prob_summary,
            target_area=target_area,
            affected_capabilities=affected_capabilities,
            affected_metrics=affected_metrics,
            baseline_id=baseline_id,
            proposed_change=change_dict,
            expected_benefit=f"Remediate regressions in {', '.join(affected_metrics)} and restore baseline parity.",
            expected_risks=["Potential transient latency increase under load"],
            rollback_plan="Revert capability configuration to previous frozen baseline parameters.",
            validation_plan="Execute canary evaluation suite with minimum 30 samples.",
            required_approvals=["GovernanceEngine", "SecurityCenter"],
            status="PROPOSED",
        )
        self.proposals[proposal.id] = proposal
        logger.info("Created ImprovementProposal: %s (%s)", proposal.id, proposal.title)
        return proposal

    def launch_experiment(
        self,
        proposal: ImprovementProposal,
        control_baseline_id: str,
        hypothesis: str,
        sample_size_target: int = 50,
    ) -> ImprovementExperiment:
        """Launches a controlled ImprovementExperiment (shadow/canary) to test a proposal safely (Section 28)."""
        exp = ImprovementExperiment(
            proposal_id=proposal.id,
            hypothesis=hypothesis,
            control_baseline_id=control_baseline_id,
            candidate_configuration=proposal.proposed_change,
            status="RUNNING",
            sample_size_target=sample_size_target,
            safety_gates=["SAFETY_GATE", "SECURITY_GATE", "REGRESSION_GATE"],
            started_at=datetime.now(UTC),
        )
        self.experiments[exp.id] = exp
        proposal.status = "IN_EXPERIMENT"
        return exp

    @classmethod
    def evaluate_gate(
        cls,
        gate_name: str,
        run_id: str,
        measured_value: Optional[float],
        threshold: Optional[float],
        is_critical_security: bool = False,
    ) -> EvaluationGate:
        """Evaluates one of the 10 canonical evaluation gates fail-closed (Section 29).
        Critical: INCONCLUSIVE must NOT silently become PASS!
        """
        status = GateStatus.INCONCLUSIVE
        reason = ""

        if measured_value is None or threshold is None:
            status = GateStatus.INCONCLUSIVE
            reason = "Insufficient evidence or missing threshold: Gate marked INCONCLUSIVE."
        elif is_critical_security:
            if measured_value >= 1.0:
                status = GateStatus.PASS
                reason = "100% Security invariance verified."
            else:
                status = GateStatus.FAIL
                reason = f"Security gate breached! Measured value: {measured_value:.2f} < 1.0."
        else:
            if measured_value >= threshold:
                status = GateStatus.PASS
                reason = f"Gate passed ({measured_value:.2f} >= {threshold:.2f})."
            else:
                status = GateStatus.FAIL
                reason = f"Gate failed: value {measured_value:.2f} below threshold {threshold:.2f}."

        return EvaluationGate(
            gate_name=gate_name,
            run_id=run_id,
            status=status,
            threshold=threshold,
            measured_value=measured_value,
            reason=reason,
        )

    def record_human_review(
        self, proposal_id: str, reviewer: str, decision: ReviewStatus, rationale: str
    ) -> EvaluationReview:
        """Records formal human review decision for an improvement proposal (Section 31)."""
        review = EvaluationReview(
            proposal_id=proposal_id,
            reviewer=reviewer,
            status=decision,
            rationale=rationale,
            reviewed_at=datetime.now(UTC),
        )
        self.reviews[review.id] = review

        proposal = self.proposals.get(proposal_id)
        if proposal:
            proposal.status = decision.value
            proposal.updated_at = datetime.now(UTC)

        return review

    async def handoff_to_cognitive_memory(
        self,
        finding_summary: str,
        evidence_dict: dict[str, Any],
        outcome: str = "SUCCESS",
    ) -> Optional[str]:
        """Hands off verified evaluation outcome as experience candidate to Task 103 Cognitive Memory (Section 42)."""
        try:
            from app.cognitive_memory.service import get_cognitive_memory_service
            from app.cognitive_memory.domain import ExperienceSource, ExperienceTrust

            mem_service = get_cognitive_memory_service()
            exp, _ = mem_service.record_experience(
                summary=f"Continuous Evaluation Finding: {finding_summary}",
                structured_facts=evidence_dict,
                source_type=ExperienceSource.VERIFICATION,
                trust_classification=ExperienceTrust.SYSTEM_VERIFIED if outcome == "SUCCESS" else ExperienceTrust.OBSERVED,
                confidence=0.9,
                importance=0.8,
            )
            return exp.experience_id
        except Exception as exc:
            logger.warning("Cognitive memory handoff skipped: %s", exc)
            return None

