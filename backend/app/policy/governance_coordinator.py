"""Governance Intelligence Coordinator: master orchestrator integrating constitutional reasoning,
authority boundaries, multi-tier policy hierarchy, goal alignment, and emergency protections (Task 78).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.policy.authority import AuthorityManagerEngine, default_authority_manager
from app.policy.constitution import ConstitutionalEngine
from app.policy.escalation_detector import (
    AuthorityEscalationDetector,
    default_escalation_detector,
)
from app.policy.goal_alignment import GoalAlignmentEngine, default_goal_alignment_engine
from app.policy.governance_schemas import (
    AuthorityLevel,
    GovernanceDashboardSummary,
    GovernanceDecisionResult,
    GovernanceDecisionType,
    GovernanceReviewRequest,
    GovernanceState,
    PolicyTier,
    PrincipleStrictness,
)
from app.policy.governance_state_machine import GovernanceStateMachine
from app.policy.hierarchy import PolicyHierarchyEngine
from app.security.emergency_stop import get_emergency_stop_service

logger = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class GovernanceIntelligenceCoordinator:
    """Master governance reasoning engine enforcing the foundational invariant:

    CAPABILITY != AUTHORITY != PERMISSION != APPROVAL != POLICY != CONSTITUTION != GOAL != OVERSIGHT != ETHICS
    """

    def __init__(
        self,
        constitutional_engine: ConstitutionalEngine | None = None,
        authority_manager: AuthorityManagerEngine | None = None,
        hierarchy_engine: type[PolicyHierarchyEngine] | None = None,
        goal_alignment_engine: GoalAlignmentEngine | None = None,
        escalation_detector: AuthorityEscalationDetector | None = None,
    ) -> None:
        self.constitutional_engine = constitutional_engine or ConstitutionalEngine()
        self.authority_manager = authority_manager or default_authority_manager
        self.hierarchy_engine = hierarchy_engine or PolicyHierarchyEngine
        self.goal_alignment_engine = goal_alignment_engine or default_goal_alignment_engine
        self.escalation_detector = escalation_detector or default_escalation_detector

        # Registered explicit policies: list of dicts for hierarchy resolution
        self._registered_policies: list[dict[str, Any]] = []
        # In-memory storage for evaluated governance decisions
        self._decisions: dict[str, GovernanceDecisionResult] = {}
        # Pending human review index: review_id -> GovernanceDecisionResult
        self._pending_human_reviews: dict[str, GovernanceDecisionResult] = {}

        self._init_default_system_policies()

    def _init_default_system_policies(self) -> None:
        """Register fundamental baseline policies across hierarchy tiers."""
        self.register_policy(
            policy_id="sys_pol_emergency_protection",
            tier=PolicyTier.SYSTEM,
            action="*",
            decision=GovernanceDecisionType.DENIED,
            condition_fn=lambda req: get_emergency_stop_service().is_stopped(),
            reason="SYSTEM Tier: Emergency stop is active across system.",
        )
        self.register_policy(
            policy_id="sys_pol_destructive_guard",
            tier=PolicyTier.SECURITY,
            action="delete_*",
            decision=GovernanceDecisionType.REQUIRES_HUMAN,
            condition_fn=lambda req: req.is_destructive or req.is_irreversible,
            reason="SECURITY Tier: Destructive or irreversible operations require explicit human oversight.",
        )
        self.register_policy(
            policy_id="sec_pol_root_tampering",
            tier=PolicyTier.SECURITY,
            action="modify_*_policy",
            decision=GovernanceDecisionType.REQUIRES_HUMAN,
            condition_fn=lambda req: req.caller_authority.rank < AuthorityLevel.ADMIN.rank,
            reason="SECURITY Tier: Modifying governance policies requires ADMIN authority and human verification.",
        )

    def register_policy(
        self,
        policy_id: str,
        tier: PolicyTier,
        action: str,
        decision: GovernanceDecisionType,
        reason: str,
        condition_fn: Any = None,
    ) -> None:
        """Register an explicit policy rule into the multi-tier hierarchy."""
        self._registered_policies.append({
            "policy_id": policy_id,
            "tier": tier,
            "action": action,
            "decision": decision,
            "reason": reason,
            "condition_fn": condition_fn,
        })
        logger.info("Governance policy registered: %s (Tier: %s)", policy_id, tier.value)

    async def evaluate_review(
        self,
        request: GovernanceReviewRequest,
        db_session: AsyncSession | None = None,
    ) -> GovernanceDecisionResult:
        """Perform authoritative governance reasoning over a candidate autonomous action."""
        evidence: list[str] = []
        now = _now_utc()

        # ----------------------------------------------------------------------
        # Step 0: Emergency Stop Check (Absolute Safety Boundary)
        # ----------------------------------------------------------------------
        emergency_service = get_emergency_stop_service()
        if emergency_service.is_stopped():
            evidence.append("EMERGENCY_STOP: System-wide emergency stop is ACTIVE.")
            explanation = (
                f"Action '{request.action}' DENIED immediately. System-wide Emergency Stop is active. "
                "All consequential and autonomous operations are halted."
            )
            decision_res = GovernanceDecisionResult(
                review_id=request.review_id,
                decision=GovernanceDecisionType.DENIED,
                state=GovernanceState.ABORTED,
                authority_level_granted=AuthorityLevel.NONE,
                authority_check_passed=False,
                policy_tier_applied=PolicyTier.SYSTEM,
                policy_id_applied="sys_pol_emergency_protection",
                constitutional_score=0.0,
                evidence=evidence,
                explanation=explanation,
                evaluated_at=now,
            )
            self._decisions[request.review_id] = decision_res
            self.escalation_detector.record_attempt(request.caller_id, request, denied=True)
            return decision_res

        # ----------------------------------------------------------------------
        # Step 1: Privilege Escalation & Bypass Detection
        # ----------------------------------------------------------------------
        escalation_report = self.escalation_detector.detect_escalation(
            request=request,
            current_authority=request.caller_authority,
        )
        if escalation_report.is_escalation_attempt:
            evidence.append(
                f"ESCALATION_DETECTED: Technique={escalation_report.bypass_technique}, Severity={escalation_report.severity}"
            )

        # ----------------------------------------------------------------------
        # Step 2: Authority Check (Authority != Capability)
        # ----------------------------------------------------------------------
        # Required authority calculation based on risk and destructiveness
        if request.risk_level in ("R4_CRITICAL", "R3_HIGH") or request.is_destructive:
            req_authority = AuthorityLevel.PROJECT
        elif request.risk_level == "R2_MODERATE":
            req_authority = AuthorityLevel.LIMITED
        else:
            req_authority = AuthorityLevel.LIMITED

        auth_passed, auth_reason, granted_level = self.authority_manager.check_authority(
            subject_id=request.caller_id,
            action=request.action,
            scope=request.project_id or request.tenant_id,
            required_level=req_authority,
            risk_level=request.risk_level,
        )
        evidence.append(f"AUTHORITY_EVALUATION: {auth_reason} (Level: {granted_level.value})")

        # Least Privilege Analysis
        least_priv = self.authority_manager.analyze_least_privilege(
            requested_permissions=request.required_permissions,
            action=request.action,
            risk_level=request.risk_level,
        )
        if least_priv.reduction_possible:
            evidence.append(
                f"LEAST_PRIVILEGE_ADVICE: Excess permissions requested: {least_priv.excess_permissions_requested}. "
                f"Recommended authority level: {least_priv.recommended_authority_level.value}"
            )

        # ----------------------------------------------------------------------
        # Step 3: Constitutional Reasoning (11 Principles)
        # ----------------------------------------------------------------------
        c_score, p_evals, mand_viols = self.constitutional_engine.evaluate_action(
            action=request.action,
            resource=request.resource,
            risk_level=request.risk_level,
            is_irreversible=request.is_irreversible,
            is_destructive=request.is_destructive,
            uncertainty_score=request.uncertainty_score,
            metadata=request.context_metadata,
        )
        evidence.append(f"CONSTITUTIONAL_SCORE: {c_score:.2f}/1.00 (Mandatory Violations: {len(mand_viols)})")
        for mv in mand_viols:
            evidence.append(f"CONSTITUTIONAL_MANDATORY_VIOLATION: {mv}")

        # Check for STRICT violations that mandate human oversight
        strict_violations = [
            ev.principle.value
            for ev in p_evals
            if not ev.compliant
            and (p := self.constitutional_engine.get_principle(ev.principle))
            and p.strictness == PrincipleStrictness.STRICT
        ]

        # ----------------------------------------------------------------------
        # Step 4: Policy Hierarchy Precedence & Conflict Resolution
        # ----------------------------------------------------------------------
        candidate_matches: list[dict[str, Any]] = []
        for pol in self._registered_policies:
            # Check action pattern match
            import fnmatch
            if fnmatch.fnmatch(request.action.lower(), pol["action"].lower()):
                cond = pol.get("condition_fn")
                if cond is None or cond(request):
                    candidate_matches.append(pol)

        winning_decision, winning_policy, conflicts = self.hierarchy_engine.resolve_conflicting_policies(
            candidate_matches
        )
        if conflicts:
            for conf in conflicts:
                evidence.append(
                    f"POLICY_CONFLICT_RESOLVED: Tiers {conf['tiers_involved']} resolved via tier rank hierarchy."
                )

        # ----------------------------------------------------------------------
        # Step 5: Goal Alignment & Ethical Constraints (Possible != Permissible)
        # ----------------------------------------------------------------------
        goal_report = self.goal_alignment_engine.evaluate_alignment(
            goal=request.goal,
            action=request.action,
            resource=request.resource,
            user_intent=request.context_metadata.get("user_intent"),
            is_destructive=request.is_destructive,
            is_irreversible=request.is_irreversible,
            context=request.context_metadata,
        )
        if goal_report.conflicts_detected:
            for gc in goal_report.conflicts_detected:
                evidence.append(f"GOAL_DIVERGENCE: {gc}")

        # ----------------------------------------------------------------------
        # Step 6: Synthesis & Decision Determination
        # ----------------------------------------------------------------------
        final_decision: GovernanceDecisionType
        applied_tier: PolicyTier | None = winning_policy.get("tier") if winning_policy else None
        applied_policy_id: str | None = winning_policy.get("policy_id") if winning_policy else None
        requires_human = False
        explanation_parts: list[str] = []

        # Rule A: Critical escalation attempt or mandatory constitutional violation -> DENIED
        if escalation_report.severity == "CRITICAL" or len(mand_viols) > 0:
            final_decision = GovernanceDecisionType.DENIED
            explanation_parts.append(
                f"Action '{request.action}' DENIED. Violates critical governance safeguards: "
                + ("; ".join(mand_viols) if mand_viols else escalation_report.rationale)
            )
        # Rule B: Unresolvable conflicting policy or strict constitutional violations -> REQUIRES_HUMAN
        elif (
            winning_decision == GovernanceDecisionType.REQUIRES_HUMAN
            or len(strict_violations) > 0
            or request.uncertainty_score >= 0.70
            or (request.is_irreversible and request.is_destructive)
            or escalation_report.severity == "HIGH"
        ):
            final_decision = GovernanceDecisionType.REQUIRES_HUMAN
            requires_human = True
            reasons = []
            if winning_decision == GovernanceDecisionType.REQUIRES_HUMAN and winning_policy:
                reasons.append(winning_policy.get("reason", "Policy hierarchy requires human review."))
            if strict_violations:
                reasons.append(f"Constitutional principles require oversight: {', '.join(strict_violations)}.")
            if request.uncertainty_score >= 0.70:
                reasons.append(f"High operational uncertainty ({request.uncertainty_score:.2f}).")
            if request.is_irreversible and request.is_destructive:
                reasons.append("Irreversible destructive action.")
            explanation_parts.append(
                f"Action '{request.action}' requires HUMAN REVIEW. Rationale: " + " ".join(reasons)
            )
        # Rule C: Authority check failed
        elif not auth_passed:
            # If explicit denial -> DENIED
            if "explicitly denied" in auth_reason:
                final_decision = GovernanceDecisionType.DENIED
                explanation_parts.append(f"Action '{request.action}' DENIED. Explicit authority restriction: {auth_reason}")
            else:
                # Insufficient authority level -> REQUIRES_APPROVAL (cannot self-approve)
                final_decision = GovernanceDecisionType.REQUIRES_APPROVAL
                explanation_parts.append(
                    f"Action '{request.action}' requires APPROVAL. Insufficient authority: {auth_reason}. "
                    "Autonomous agent cannot self-approve."
                )
        # Rule D: Hierarchy winning decision check
        elif winning_decision == GovernanceDecisionType.DENIED:
            final_decision = GovernanceDecisionType.DENIED
            explanation_parts.append(
                f"Action '{request.action}' DENIED by {applied_tier.value if applied_tier else 'SYSTEM'} policy: "
                f"{winning_policy.get('reason', 'Denied by hierarchy policy')}"
            )
        elif winning_decision == GovernanceDecisionType.REQUIRES_APPROVAL:
            final_decision = GovernanceDecisionType.REQUIRES_APPROVAL
            explanation_parts.append(
                f"Action '{request.action}' requires APPROVAL per policy: "
                f"{winning_policy.get('reason', 'Approval required.')}"
            )
        # Rule E: Goal divergence check
        elif not goal_report.safety_aligned or not goal_report.constitutional_aligned:
            final_decision = GovernanceDecisionType.REQUIRES_HUMAN
            requires_human = True
            explanation_parts.append(
                f"Action '{request.action}' requires HUMAN REVIEW due to ethical divergence: "
                + "; ".join(goal_report.conflicts_detected)
            )
        # Rule F: Everything compliant
        else:
            final_decision = GovernanceDecisionType.ALLOWED
            explanation_parts.append(
                f"Action '{request.action}' ALLOWED. Fully authorized at {granted_level.value} level, "
                f"aligned with constitution (score {c_score:.2f}) and policy hierarchy."
            )

        # ----------------------------------------------------------------------
        # Step 7: State Machine Lifecycle Transition
        # ----------------------------------------------------------------------
        initial_state = GovernanceStateMachine.determine_initial_state(final_decision)

        # Human handoff packet if required
        handoff_packet = None
        if requires_human or final_decision == GovernanceDecisionType.REQUIRES_HUMAN:
            handoff_packet = GovernanceStateMachine.build_human_handoff_packet(
                review_id=request.review_id,
                action=request.action,
                resource=request.resource,
                risk_level=request.risk_level,
                constitutional_score=c_score,
                evidence=evidence,
                suggested_decision=final_decision,
            )

        explanation = " ".join(explanation_parts)

        result = GovernanceDecisionResult(
            review_id=request.review_id,
            decision=final_decision,
            state=initial_state,
            authority_level_granted=granted_level,
            authority_check_passed=auth_passed,
            policy_tier_applied=applied_tier,
            policy_id_applied=applied_policy_id,
            constitutional_score=c_score,
            principle_evaluations=p_evals,
            goal_alignment=goal_report,
            least_privilege=least_priv,
            escalation_report=escalation_report,
            requires_human=requires_human or (final_decision == GovernanceDecisionType.REQUIRES_HUMAN),
            human_handoff_packet=handoff_packet,
            evidence=evidence,
            explanation=explanation,
            evaluated_at=now,
        )

        self._decisions[request.review_id] = result
        if result.requires_human:
            self._pending_human_reviews[request.review_id] = result

        # Record attempt in escalation detector
        self.escalation_detector.record_attempt(
            caller_id=request.caller_id,
            request=request,
            denied=(final_decision == GovernanceDecisionType.DENIED),
        )

        logger.info(
            "Governance review %s evaluated: decision=%s, state=%s, score=%.2f",
            request.review_id,
            final_decision.value,
            initial_state.value,
            c_score,
        )

        return result

    def resolve_human_review(
        self,
        review_id: str,
        reviewer_id: str,
        approved: bool,
        rationale: str = "",
        db_session: AsyncSession | None = None,
    ) -> GovernanceDecisionResult:
        """Process verified human judgment on a pending review.

        Crucial Rule:
        The reviewer MUST NOT be the autonomous agent itself.
        """
        if reviewer_id in ("kairo", "autonomous_agent", "default_agent", "self"):
            raise ValueError("Governance Invariant Violated: Autonomous agent cannot self-approve.")

        if review_id not in self._decisions:
            raise KeyError(f"Governance review '{review_id}' not found.")

        current = self._decisions[review_id]
        if current.state != GovernanceState.REQUIRES_HUMAN:
            raise ValueError(
                f"Review '{review_id}' is in state {current.state.value}, not REQUIRES_HUMAN."
            )

        now = _now_utc()
        if approved:
            # Transition: REQUIRES_HUMAN -> APPROVED -> EXECUTABLE
            s1 = GovernanceStateMachine.transition(current.state, GovernanceState.APPROVED)
            s2 = GovernanceStateMachine.transition(s1, GovernanceState.EXECUTABLE)
            current.state = s2
            current.decision = GovernanceDecisionType.ALLOWED
            current.requires_human = False
            current.evidence.append(
                f"HUMAN_APPROVAL_GRANTED: Reviewer '{reviewer_id}' approved action. Rationale: {rationale}"
            )
            current.explanation += f" [Approved by human reviewer '{reviewer_id}': {rationale}]"
        else:
            # Transition: REQUIRES_HUMAN -> DENIED
            current.state = GovernanceStateMachine.transition(current.state, GovernanceState.DENIED)
            current.decision = GovernanceDecisionType.DENIED
            current.evidence.append(
                f"HUMAN_REJECTION: Reviewer '{reviewer_id}' rejected action. Rationale: {rationale}"
            )
            current.explanation += f" [Rejected by human reviewer '{reviewer_id}': {rationale}]"

        self._pending_human_reviews.pop(review_id, None)
        logger.info(
            "Human review %s resolved: approved=%s, new_state=%s",
            review_id,
            approved,
            current.state.value,
        )
        return current

    def get_decision(self, review_id: str) -> GovernanceDecisionResult | None:
        """Fetch decision record by review_id."""
        return self._decisions.get(review_id)

    def list_pending_human_reviews(self) -> list[GovernanceDecisionResult]:
        """Return all reviews currently waiting for human judgment."""
        return list(self._pending_human_reviews.values())

    def get_dashboard_summary(self) -> GovernanceDashboardSummary:
        """Produce consolidated real-time governance metrics for Command Center."""
        tier_counts: dict[str, int] = {}
        for pol in self._registered_policies:
            tier_val = pol["tier"].value
            tier_counts[tier_val] = tier_counts.get(tier_val, 0) + 1

        active_grants_count = sum(
            len(grants) for grants in self.authority_manager._grants.values()
        )
        recent_escalations = len(self.escalation_detector.get_recent_incidents())
        avg_score = (
            sum(d.constitutional_score for d in self._decisions.values()) / len(self._decisions)
            if self._decisions
            else 1.0
        )

        return GovernanceDashboardSummary(
            active_policies_by_tier=tier_counts,
            active_authority_grants_count=active_grants_count,
            pending_human_reviews_count=len(self._pending_human_reviews),
            recent_escalations_count=recent_escalations,
            constitutional_compliance_index=round(avg_score, 3),
            timestamp=_now_utc(),
        )


default_governance_coordinator = GovernanceIntelligenceCoordinator()
