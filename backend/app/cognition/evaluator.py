"""Plan feasibility evaluation, quality scoring, safety critique, and validation for Kairo Cognitive Planning (Task 41)."""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from app.cognition.dependencies import DependencyCycleError, DependencyGraph
from app.cognition.plans import Plan, PlanRiskLevel
from app.cognition.steps import StepRiskLevel


class PlanValidationReport(BaseModel):
    """Authoritative validation and safety assessment of a proposed plan."""

    model_config = ConfigDict(extra="ignore")

    is_valid: bool = True
    is_feasible: bool = True
    quality_score: float = Field(default=1.0, ge=0.0, le=1.0)
    blocking_reasons: list[str] = Field(default_factory=list)
    missing_capabilities: list[str] = Field(default_factory=list)
    required_user_actions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    second_pass_required: bool = Field(default=False)
    critique_findings: list[str] = Field(default_factory=list)


class PlanEvaluator:
    """Evaluates plan feasibility, structural validity, policy adherence, and safety criteria."""

    KNOWN_SAFE_ACTIONS = {
        "inspect_state", "direct_query", "inspect_logs", "code_inspect",
        "code_patch", "test_runner", "verify_health", "knowledge_search",
        "cross_reference", "synthesize_report", "inspect_environment",
        "execute_operation", "verify_outcome", "git_status", "git_diff",
        "git_log", "git_commit", "web_search", "web_fetch"
    }

    FORBIDDEN_ACTIONS = {
        "shell.execute", "raw_bash", "cmd_exec", "eval", "system_override",
        "format_disk", "rm_rf_root", "disable_security", "bypass_auth"
    }

    @classmethod
    def evaluate_plan(
        cls,
        plan: Plan,
        available_tools: set[str] | None = None,
        available_permissions: set[str] | None = None,
        environment: str = "development",
    ) -> PlanValidationReport:
        """Run comprehensive multi-layer plan evaluation and safety verification."""
        report = PlanValidationReport()
        available_tools = available_tools or cls.KNOWN_SAFE_ACTIONS

        # 1. Step Completeness Check
        if not plan.steps:
            report.is_valid = False
            report.is_feasible = False
            report.blocking_reasons.append("Plan contains zero steps.")
            report.quality_score = 0.0
            return report

        # 2. Dependency Graph & Cycle Detection Check
        try:
            graph = DependencyGraph(plan.steps)
            graph.validate_acyclic()
        except DependencyCycleError as e:
            report.is_valid = False
            report.is_feasible = False
            report.blocking_reasons.append(f"Dependency cycle detected: {str(e)}")

        # 3. Step Action Validity & Security Check
        for s in plan.steps:
            # Reject forbidden actions
            if s.action in cls.FORBIDDEN_ACTIONS:
                report.is_valid = False
                report.is_feasible = False
                report.blocking_reasons.append(f"Forbidden action '{s.action}' in step '{s.step_id}' violates security policy.")

            # Check tool availability
            if s.action not in available_tools and s.action not in cls.KNOWN_SAFE_ACTIONS:
                report.missing_capabilities.append(s.action)
                report.is_feasible = False
                report.blocking_reasons.append(f"Action '{s.action}' in step '{s.step_id}' is not in available tools allowlist.")

            # High-risk actions MUST have explicit verification postconditions
            if s.risk in {StepRiskLevel.WRITE, StepRiskLevel.DESTRUCTIVE}:
                if not s.verification.postconditions and not s.verification.expected:
                    report.is_valid = False
                    report.blocking_reasons.append(
                        f"High-risk step '{s.step_id}' ({s.action}) lacks postcondition verification requirements."
                    )

        # 4. Scope Lock Verification
        scope = plan.scope_lock
        if scope.allowed_environments and environment not in scope.allowed_environments:
            report.is_feasible = False
            report.blocking_reasons.append(
                f"Target environment '{environment}' is not permitted by scope lock ({scope.allowed_environments})."
            )

        # 5. Success Criteria Check (Spec 4, 143)
        if not plan.success_criteria:
            report.is_valid = False
            report.blocking_reasons.append("Plan lacks defined measurable success criteria.")

        # 6. High-Risk Second-Pass Flag (Spec 40, 105)
        if plan.risk in {PlanRiskLevel.HIGH, PlanRiskLevel.CRITICAL}:
            report.second_pass_required = True
            report.warnings.append("High-risk plan flagged for mandatory second-pass security authorization.")

        # 7. Compute Deterministic Quality Score (Spec 103)
        # Score = 0.35 * completeness + 0.35 * feasibility + 0.30 * verification_coverage
        step_count = len(plan.steps)
        verified_steps = sum(1 for s in plan.steps if s.verification.postconditions or s.verification.expected is not None)
        v_coverage = verified_steps / max(1, step_count)

        completeness = 1.0 if not report.blocking_reasons else 0.0
        feasibility = 1.0 if report.is_feasible else 0.0
        quality = 0.35 * completeness + 0.35 * feasibility + 0.30 * v_coverage

        report.quality_score = round(max(0.0, min(1.0, quality)), 2)

        if not report.is_feasible:
            report.required_user_actions.append(
                "Resolve missing capabilities or environment restrictions before executing plan."
            )

        return report
