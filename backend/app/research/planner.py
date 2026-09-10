"""Research planning, question decomposition, hypothesis formulation, and stop conditions (Task 63)."""

from __future__ import annotations

import logging

from app.research.schemas import (
    ResearchHypothesis,
    ResearchMode,
    ResearchPlan,
    ResearchRequest,
)

logger = logging.getLogger(__name__)


class ResearchPlanner:
    """Decomposes complex research inquiries into structured sub-questions, hypotheses, and stop conditions.

    Invariant 4: Before collecting large amounts of information, generate a disciplined research plan.
    Invariant 26 & 29: Enforces stop conditions (budget limits, evidence saturation, source exhaustion).
    """

    def generate_plan(self, request: ResearchRequest) -> ResearchPlan:
        """Decompose incoming research request into a prioritized research plan with stop conditions."""
        sub_questions = self._decompose_question(request.question, request.mode)
        hypotheses = self._formulate_initial_hypotheses(request.question)

        # Stop conditions based on research mode and budget limits
        stop_conditions = [
            f"max_budget_usd: {request.max_cost}",
            f"max_duration_seconds: {request.max_duration_seconds}",
            "evidence_saturation_reached",
            "confidence_threshold_exceeded",
        ]

        if request.mode == ResearchMode.QUICK:
            stop_conditions.append("max_sources: 3")
        elif request.mode == ResearchMode.STANDARD:
            stop_conditions.append("max_sources: 8")
        elif request.mode == ResearchMode.DEEP:
            stop_conditions.append("max_sources: 20")
        else:
            stop_conditions.append("max_sources: 50")

        evidence_requirements = [
            "Primary documentation or peer-reviewed empirical benchmarks",
            "Discrepancy reconciliation for conflicting quantitative measurements",
            "Direct evidence links for all factual assertions",
        ]

        plan = ResearchPlan(
            question=request.question,
            sub_questions=sub_questions,
            hypotheses=hypotheses,
            search_strategy="MULTI_DOMAIN" if len(request.domains) > 1 else "TARGETED_DOMAIN",
            source_strategy="PRIMARY_FIRST",
            evidence_requirements=evidence_requirements,
            verification_strategy="CROSS_SOURCE_CORRELATION",
            stop_conditions=stop_conditions,
            known_gaps=[],
            expected_cost=round(min(request.max_cost * 0.25, 1.25), 2),
        )

        logger.info(
            "RESEARCH_PLAN_GENERATED: plan=%s sub_questions=%d hypotheses=%d",
            plan.plan_id,
            len(sub_questions),
            len(hypotheses),
        )
        return plan

    create_plan = generate_plan

    def _decompose_question(self, question: str, mode: ResearchMode) -> list[str]:
        """Decompose question into sub-dimensions (requirements, candidate approaches, tradeoffs, costs)."""
        q_lower = question.lower()

        # Architecture and system evaluation questions
        if any(
            term in q_lower
            for term in ["architecture", "which database", "which framework", "system", "technology"]
        ):
            subs = [
                f"What are the baseline requirements and operational constraints for {question}?",
                "What are the existing authoritative standards and primary options?",
                "What are the measured reliability, availability, and failover characteristics?",
                "What are the latency, throughput, and compute resource tradeoffs?",
                "What are the security, privacy, and compliance implications?",
                "What are the long-term operational and licensing cost structures?",
            ]
            if mode in (ResearchMode.DEEP, ResearchMode.COMPREHENSIVE):
                subs.extend(
                    [
                        "What empirical failure modes and incident postmortems exist?",
                        "What counter-evidence or benchmark criticisms have been published?",
                    ]
                )
            return subs

        # General inquiry decomposition
        return [
            f"What primary empirical evidence directly addresses: {question}?",
            "What independent corroborations or secondary reports exist?",
            "Are there conflicting findings or disputed claims across sources?",
            "What assumptions or epistemic uncertainties remain unverified?",
        ]

    def _formulate_initial_hypotheses(self, question: str) -> list[ResearchHypothesis]:
        """Formulate working hypotheses to guide evidence gathering."""
        return [
            ResearchHypothesis(
                statement=f"Evidence supports a clear architectural or empirical preference for: {question}",
            )
        ]


research_planner = ResearchPlanner()
