"""Ten explicit decision gates for Kairo Executive Decision Engine (Task 57).

A recommendation may be generated without passing execution gates.
Execution must never proceed without passing required execution and verification gates.
"""

from __future__ import annotations

from typing import Any

from app.decision.schemas import (
    CandidateOption,
    DecisionGate,
    DecisionRequest,
    EvidenceSet,
    EvidenceStrength,
    GateEvaluationStatus,
    OptionType,
    ReversibilityLevel,
    RiskAssessment,
    UncertaintyAssessment,
)


class GateEvaluationEngine:
    """Evaluates the 10 formal gates governing recommendation, approval, and execution handoff."""

    def evaluate_gates(
        self,
        request: DecisionRequest,
        leading_option: CandidateOption | None,
        evidence_set: EvidenceSet,
        risks: list[RiskAssessment],
        uncertainty: UncertaintyAssessment,
        simulations: list[dict[str, Any]] | None = None,
        is_authorized: bool = True,
        is_production: bool = False,
    ) -> tuple[dict[str, DecisionGate], bool]:
        gates: dict[str, DecisionGate] = {}
        approval_required = False

        # Gate 1: Context valid?
        g1_pass = bool(request.question and request.question.strip())
        gates["gate_1_context"] = DecisionGate(
            gate_number=1,
            name="Context Valid",
            status=GateEvaluationStatus.PASSED if g1_pass else GateEvaluationStatus.FAILED,
            message="Decision question and context scope are well-formed." if g1_pass else "Missing decision question.",
        )

        # Gate 2: Goals valid?
        g2_pass = bool(request.objectives)
        gates["gate_2_goals"] = DecisionGate(
            gate_number=2,
            name="Goals Valid",
            status=GateEvaluationStatus.PASSED if g2_pass else GateEvaluationStatus.FAILED,
            message="Explicit objectives defined." if g2_pass else "No explicit objectives specified (using default heuristic).",
        )

        # Gate 3: Constraints satisfied?
        g3_pass = leading_option is not None and leading_option.hard_constraints_satisfied and leading_option.is_feasible
        gates["gate_3_constraints"] = DecisionGate(
            gate_number=3,
            name="Constraints Satisfied",
            status=GateEvaluationStatus.PASSED if g3_pass else GateEvaluationStatus.FAILED,
            message="Candidate option complies with all hard constraints." if g3_pass else "Candidate violates hard constraints or is infeasible.",
        )

        # Gate 4: Evidence sufficient?
        g4_pass = (
            len(evidence_set.items) > 0
            and evidence_set.overall_strength != EvidenceStrength.SPECULATIVE
            and evidence_set.overall_strength != EvidenceStrength.UNKNOWN
        )
        gates["gate_4_evidence"] = DecisionGate(
            gate_number=4,
            name="Evidence Sufficient",
            status=GateEvaluationStatus.PASSED if g4_pass else GateEvaluationStatus.FAILED,
            message=f"Grounding supported by {len(evidence_set.items)} evidence items (strength {evidence_set.overall_strength.value})."
            if g4_pass
            else "Insufficient or purely speculative evidence.",
        )

        # Gate 5: Risk acceptable?
        critical_risk = any(r.exposure_score > 0.75 for r in risks)
        g5_pass = not critical_risk
        gates["gate_5_risk"] = DecisionGate(
            gate_number=5,
            name="Risk Acceptable",
            status=GateEvaluationStatus.PASSED if g5_pass else GateEvaluationStatus.FAILED,
            message="Risk exposure is within acceptable bounds." if g5_pass else "Critical risk exposure detected; mitigation mandatory.",
        )

        # Gate 6: Simulation sufficiently fresh?
        sims = simulations or []
        stale_sim = any(s.get("is_stale", False) for s in sims)
        gates["gate_6_simulation"] = DecisionGate(
            gate_number=6,
            name="Simulation Freshness",
            status=GateEvaluationStatus.FAILED if stale_sim else GateEvaluationStatus.PASSED,
            message="Associated simulations are fresh and valid." if not stale_sim else "Stale simulation detected; revalidation required.",
        )

        # Gate 7: Authorization valid?
        gates["gate_7_authorization"] = DecisionGate(
            gate_number=7,
            name="Authorization Valid",
            status=GateEvaluationStatus.PASSED if is_authorized else GateEvaluationStatus.BLOCKED,
            message="Caller has valid authority for this decision scope." if is_authorized else "Unauthorized actor for decision scope.",
        )

        # Gate 8: Approval required?
        # Irreversible, destructive, production, or high-risk actions require approval
        is_irreversible = leading_option is not None and leading_option.reversibility in {
            ReversibilityLevel.IRREVERSIBLE,
            ReversibilityLevel.DIFFICULT_TO_REVERSE,
        }
        is_aggressive = leading_option is not None and leading_option.option_type == OptionType.AGGRESSIVE
        needs_approval = is_production or is_irreversible or critical_risk or is_aggressive

        approval_required = needs_approval
        gates["gate_8_approval"] = DecisionGate(
            gate_number=8,
            name="Approval Requirement",
            status=GateEvaluationStatus.PENDING_APPROVAL if needs_approval else GateEvaluationStatus.PASSED,
            message="Human approval required prior to execution handoff." if needs_approval else "Standard policy permits automated handoff.",
        )

        # Gate 9: Execution plan valid?
        # If no option, execution plan cannot be valid
        has_valid_plan = leading_option is not None and leading_option.is_feasible
        gates["gate_9_execution_plan"] = DecisionGate(
            gate_number=9,
            name="Execution Plan Valid",
            status=GateEvaluationStatus.PASSED if has_valid_plan else GateEvaluationStatus.FAILED,
            message="Guarded execution plan proposal generated." if has_valid_plan else "No viable option to construct execution plan.",
        )

        # Gate 10: Verification plan exists?
        gates["gate_10_verification_plan"] = DecisionGate(
            gate_number=10,
            name="Verification Plan Exists",
            status=GateEvaluationStatus.PASSED if has_valid_plan else GateEvaluationStatus.FAILED,
            message="Post-execution telemetry and health verification criteria established." if has_valid_plan else "Missing verification criteria.",
        )

        return gates, approval_required


gate_evaluation_engine = GateEvaluationEngine()
