"""Central Kairo Policy and Governance Decision Engine (Task 36).

Coordinates permissions, risk, environment, approvals, and autonomy constraints
into a single authoritative decision layer without replacing underlying domain systems.
"""

from datetime import UTC, datetime, timedelta
import logging
from typing import Any

from app.policy.approvals import PolicyApprovalBridge
from app.policy.authentication import AuthFreshnessChecker
from app.policy.autonomy import AutonomyGovernor
from app.policy.conflicts import ConflictResolver
from app.policy.data_access import DataAccessController
from app.policy.decisions import decision_provenance_manager
from app.policy.devices import DevicePolicyEnforcer
from app.policy.environments import environment_policy_manager
from app.policy.evaluator import RuleEvaluator
from app.policy.explain import PolicyExplainer
from app.policy.registry import policy_registry
from app.policy.risk import DeterministicRiskEngine
from app.policy.schemas import (
    PolicyContext,
    PolicyDecision,
    PolicyDecisionType,
    PolicyRule,
    PolicySimulationRequest,
    PolicySimulationResponse,
    RiskLevel,
    generate_eval_id,
)
from app.policy.scope import ScopeHierarchyEvaluator
from app.security.emergency_stop import get_emergency_stop_service

logger = logging.getLogger("kairo.policy.engine")


class PolicyEngine:
    """The central Policy & Governance Decision Engine for Kairo."""

    def __init__(self) -> None:
        self.registry = policy_registry
        self.environments = environment_policy_manager
        self.provenance = decision_provenance_manager

    async def evaluate(self, context: PolicyContext, simulate: bool = False) -> PolicyDecision:
        """Evaluate full policy decision pipeline for the given context."""
        eval_id = generate_eval_id()
        now = datetime.now(UTC)

        # 1. Check Safe Read-only Cache (Sections 92, 93)
        if not simulate:
            cached = self.registry.get_cached_decision(context)
            if cached:
                return cached
        elif not context.session:
            # For hypothetical simulation without explicit session context
            context = context.model_copy(update={"session": {"id": "sim_session", "is_active": True, "mfa_verified": True}})

        # 2. Emergency Stop Check (Section 107, 108, 139)
        es_service = get_emergency_stop_service()
        es_active = es_service.is_emergency_stop_active() or (context.world_state or {}).get("emergency_stop") is True
        if es_active:
            decision = PolicyDecision(
                decision=PolicyDecisionType.DENY,
                policy_id="sys-emergency-stop",
                policy_version=1,
                reason_code="EMERGENCY_STOP_ACTIVE",
                safe_explanation="System Emergency Stop is active. All privileged and mutating actions are blocked.",
                risk_level=RiskLevel.R4_CRITICAL,
                evaluation_id=eval_id,
                matched_policies=["sys-emergency-stop"],
                simulated=simulate,
                timestamp=now,
            )
            if not simulate:
                self.provenance.record_evaluation(context, decision)
                await self.provenance.emit_decision_events(context, decision)
            return decision

        # 3. Deterministic Risk Assessment (Sections 33-42)
        assessed_risk, risk_factors = DeterministicRiskEngine.evaluate_risk(context)

        # 4. Cross-Boundary Scope Verification (Sections 74, 75, 124)
        cross_ok, cross_err = ScopeHierarchyEvaluator.validate_cross_boundary_access(context)
        if not cross_ok:
            reason_code = "CROSS_USER_DENIED" if "Cross-user" in (cross_err or "") else "CROSS_PROJECT_DENIED"
            decision = PolicyDecision(
                decision=PolicyDecisionType.DENY,
                reason_code=reason_code,
                safe_explanation=cross_err or "Cross-boundary access denied.",
                risk_level=assessed_risk,
                evaluation_id=eval_id,
                simulated=simulate,
                timestamp=now,
            )
            if not simulate:
                self.provenance.record_evaluation(context, decision)
                await self.provenance.emit_decision_events(context, decision)
            return decision

        # 5. Task Scope Expansion Verification (Sections 53, 54, 129)
        task_scope_ok, task_scope_err = ScopeHierarchyEvaluator.validate_task_scope_expansion(context)
        if not task_scope_ok:
            decision = PolicyDecision(
                decision=PolicyDecisionType.DENY,
                reason_code="SCOPE_EXPANSION_VIOLATION",
                safe_explanation=task_scope_err or "Autonomous task scope boundary violated.",
                risk_level=assessed_risk,
                evaluation_id=eval_id,
                simulated=simulate,
                timestamp=now,
            )
            if not simulate:
                self.provenance.record_evaluation(context, decision)
                await self.provenance.emit_decision_events(context, decision)
            return decision

        # 6. Environment Invariants (Sections 16, 17, 109-113, 130, 131)
        env_dec, env_reason = self.environments.evaluate_environment_constraints(context)

        # 7. Device Invariants (Sections 18, 64, 65, 125, 126, 140)
        dev_dec, dev_reason = DevicePolicyEnforcer.evaluate_device(context, assessed_risk)

        # 8. Data Access & Model Routing (Sections 25-28, 77-79, 145, 146)
        data_dec, data_reason, allowed_scope = DataAccessController.evaluate_data_access(context)

        # 9. Authentication Freshness & MFA (Sections 19, 62, 63, 127)
        auth_dec, auth_reason = AuthFreshnessChecker.evaluate_authentication(context, assessed_risk)

        # 10. Autonomy Budgets & Limits (Sections 48-55, 143, 144)
        auto_dec, auto_reason, auto_constraints = AutonomyGovernor.evaluate_task_limits(context)

        # Collect hard gate decisions from structural subsystems
        structural_decisions: list[tuple[PolicyDecisionType, str | None]] = []
        for dec, r in [(dev_dec, dev_reason), (data_dec, data_reason), (auth_dec, auth_reason), (auto_dec, auto_reason), (env_dec, env_reason)]:
            if dec is not None:
                structural_decisions.append((dec, r))

        # Check for immediate structural DENY
        structural_denies = [d for d in structural_decisions if d[0] == PolicyDecisionType.DENY]
        if structural_denies:
            target_deny = structural_denies[0]
            decision = PolicyDecision(
                decision=PolicyDecisionType.DENY,
                reason_code="GOVERNANCE_INVARIANT_DENY",
                safe_explanation=target_deny[1] or "Action blocked by governance invariant.",
                constraints=auto_constraints,
                allowed_scope=allowed_scope,
                risk_level=assessed_risk,
                evaluation_id=eval_id,
                simulated=simulate,
                timestamp=now,
            )
            if not simulate:
                self.provenance.record_evaluation(context, decision)
                await self.provenance.emit_decision_events(context, decision)
            return decision

        # 11. Declarative Policy Evaluation
        candidate_rules = self.registry.list_policies(include_disabled=False)
        win_decision, win_rule, matched_ids, shadow_decs, trace = RuleEvaluator.evaluate_rules(
            context, candidate_rules, assessed_risk
        )

        # 12. Arbitrate between Declarative Policy and Structural Checks
        # Priority: DENY > REQUIRE_STEP_UP_AUTH > REQUIRE_APPROVAL > REQUIRE_CONFIRMATION > ALLOW_WITH_LIMITS > ALLOW > DEFER
        final_decision_type = win_decision
        final_rule = win_rule
        primary_reason = win_rule.safe_explanation if win_rule else None
        reason_code = win_rule.reason_code if win_rule else None

        # Check if any structural gate requires step-up, approval, or defer
        for s_dec, s_reason in structural_decisions:
            if ConflictResolver.DECISION_PRECEDENCE.get(s_dec, 99) < ConflictResolver.DECISION_PRECEDENCE.get(final_decision_type, 99):
                final_decision_type = s_dec
                primary_reason = s_reason
                reason_code = s_dec.value

        # 13. Default Deny for High Risk / Default Allow for Low Risk (Sections 10, 11)
        if not matched_ids and not structural_decisions:
            if assessed_risk in (RiskLevel.R3_HIGH, RiskLevel.R4_CRITICAL) or context.environment == "production":
                final_decision_type = PolicyDecisionType.REQUIRE_APPROVAL if context.environment == "production" else PolicyDecisionType.DENY
                primary_reason = "Privileged or production action lacks explicit governing allowance; failing closed."
                reason_code = "DEFAULT_DENY_FAIL_CLOSED"
            else:
                final_decision_type = PolicyDecisionType.ALLOW
                primary_reason = "Standard low-risk operation permitted under default baseline."
                reason_code = "DEFAULT_LOW_RISK_ALLOW"

        # 14. Construct Final Decision
        final_explanation = PolicyExplainer.get_safe_explanation(
            final_decision_type, final_rule, reason_code, primary_reason
        )

        decision = PolicyDecision(
            decision=final_decision_type,
            policy_id=final_rule.policy_id if final_rule else None,
            policy_version=final_rule.version if final_rule else None,
            reason_code=reason_code,
            safe_explanation=final_explanation,
            constraints={**auto_constraints, **(final_rule.constraints if final_rule else {})},
            required_approval={"required": True, "reason": final_explanation} if final_decision_type == PolicyDecisionType.REQUIRE_APPROVAL else None,
            required_authentication={"required": True, "type": "MFA"} if final_decision_type == PolicyDecisionType.REQUIRE_STEP_UP_AUTH else None,
            allowed_scope=allowed_scope,
            risk_level=assessed_risk,
            expires_at=now + timedelta(minutes=15) if final_decision_type == PolicyDecisionType.ALLOW else None,
            evaluation_id=eval_id,
            matched_policies=matched_ids,
            shadow_decisions=shadow_decs,
            simulated=simulate,
            timestamp=now,
        )

        # 15. Record Provenance, Cache, and Broadcast
        if not simulate:
            self.provenance.record_evaluation(context, decision)
            if decision.decision == PolicyDecisionType.ALLOW and assessed_risk in (RiskLevel.R0_READ_ONLY, RiskLevel.R1_LOW):
                self.registry.cache_decision(context, decision)
            await self.provenance.emit_decision_events(context, decision)

        return decision

    async def simulate(self, request: PolicySimulationRequest) -> PolicySimulationResponse:
        """Simulate policy evaluation without enforcing, caching, or publishing events (Section 88, 133)."""
        rules = list(self.registry.list_policies(include_disabled=False))
        if request.candidate_policy:
            rules.append(request.candidate_policy)

        # Compute risk
        assessed_risk, _ = DeterministicRiskEngine.evaluate_risk(request.context)

        # Evaluate rules and capture trace
        win_decision, win_rule, matched_ids, shadow_decs, trace = RuleEvaluator.evaluate_rules(
            request.context, rules, assessed_risk
        )

        # Run full simulate evaluation
        decision = await self.evaluate(request.context, simulate=True)

        return PolicySimulationResponse(
            decision=decision,
            evaluated_policies_count=len(rules),
            trace=trace,
        )

    # ==========================================
    # Integration Hooks for Defense in Depth
    # ==========================================

    async def check_tool_execution(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        user_id: str,
        session_id: str | None = None,
        environment: str = "development",
        device: dict[str, Any] | None = None
    ) -> PolicyDecision:
        """Defense in depth check called before ToolExecutor runs a tool (Section 99, 136)."""
        context = PolicyContext(
            user={"id": user_id, "user_id": user_id},
            session={"id": session_id} if session_id else None,
            device=device,
            environment=environment,
            action=tool_name,
            tool=tool_name,
            target=arguments,
        )
        return await self.evaluate(context)

    async def check_task_step(
        self,
        task_id: str,
        action: str,
        target: Any,
        user_id: str,
        environment: str = "development",
        budget: dict[str, Any] | None = None,
        tool_calls_count: int = 0
    ) -> PolicyDecision:
        """Defense in depth check called before TaskEngine runs an autonomous step (Section 98, 137)."""
        context = PolicyContext(
            user={"id": user_id, "user_id": user_id},
            environment=environment,
            action=action,
            target=target,
            task={
                "id": task_id,
                "tool_calls_count": tool_calls_count,
                "budget": budget or {},
            },
        )
        return await self.evaluate(context)


# Global PolicyEngine singleton instance
policy_engine = PolicyEngine()
