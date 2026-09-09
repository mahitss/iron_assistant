"""Goal decomposition into atomic, observable, verifiable, and recoverable steps for Kairo Cognitive Planning (Task 41)."""

import uuid
from typing import Any

from app.cognition.goals import Goal, GoalType
from app.cognition.reasoning import ReasoningMode
from app.cognition.steps import PlanStep, StepRiskLevel, StepStatus, VerificationSpec


class PlanDecomposer:
    """Decomposes high-level goals into structured PlanStep DAG nodes."""

    @staticmethod
    def decompose_goal(
        goal: Goal,
        plan_id: str,
        reasoning_mode: ReasoningMode,
        context: dict[str, Any] | None = None,
    ) -> list[PlanStep]:
        """Produce an initial ordered sequence of atomic PlanSteps based on goal and reasoning mode."""
        context = context or {}
        steps: list[PlanStep] = []
        desc = goal.description.lower()

        # 1. DIRECT MODE: Single atomic step
        if reasoning_mode == ReasoningMode.DIRECT:
            step = PlanStep(
                plan_id=plan_id,
                sequence=1,
                objective=goal.description,
                action="inspect_state" if "status" in desc else "direct_query",
                inputs={"target": goal.description},
                expected_output={"status": "success"},
                success_criteria=["Direct query returns valid response."],
                risk=StepRiskLevel.READ,
                reversible=True,
                verification=VerificationSpec(
                    check_type="OUTPUT_MATCH",
                    target="result",
                    postconditions=["Output is non-empty and well-formed."],
                ),
                status=StepStatus.READY,
            )
            return [step]

        # 2. DIAGNOSTIC MODE: Inspect -> Retrieve Logs -> Hypothesize -> Inspect Code -> Minimal Patch -> Test -> Verify
        if reasoning_mode == ReasoningMode.DIAGNOSTIC or "ci" in desc or "fix" in desc:
            s1_id = f"step_{uuid.uuid4().hex[:10]}"
            s2_id = f"step_{uuid.uuid4().hex[:10]}"
            s3_id = f"step_{uuid.uuid4().hex[:10]}"
            s4_id = f"step_{uuid.uuid4().hex[:10]}"
            s5_id = f"step_{uuid.uuid4().hex[:10]}"

            s1 = PlanStep(
                step_id=s1_id,
                plan_id=plan_id,
                sequence=1,
                objective="Inspect failing system status and retrieve error logs (Read-First).",
                action="inspect_logs",
                inputs={"scope": goal.scope.project_id or "default"},
                expected_output={"logs": "list"},
                success_criteria=["Failure logs retrieved without error."],
                risk=StepRiskLevel.READ,
                reversible=True,
                verification=VerificationSpec(
                    check_type="OUTPUT_MATCH",
                    target="logs",
                    postconditions=["Retrieved error logs are non-empty."],
                ),
                status=StepStatus.READY,
            )
            s2 = PlanStep(
                step_id=s2_id,
                plan_id=plan_id,
                sequence=2,
                objective="Inspect affected source files and identify root cause hypothesis.",
                action="code_inspect",
                dependencies=[s1_id],
                inputs={"target": "affected_files"},
                expected_output={"diagnostic_summary": "str"},
                success_criteria=["Root cause identified and distinguished."],
                risk=StepRiskLevel.READ,
                reversible=True,
                verification=VerificationSpec(
                    check_type="STATE_CHECK",
                    target="diagnostic_summary",
                    preconditions=["Failure logs have been parsed."],
                    postconditions=["Root cause hypothesis is established."],
                ),
                status=StepStatus.PENDING,
            )
            s3 = PlanStep(
                step_id=s3_id,
                plan_id=plan_id,
                sequence=3,
                objective="Apply minimal targeted patch to resolve identified root cause.",
                action="code_patch",
                dependencies=[s2_id],
                inputs={"patch_type": "minimal"},
                expected_output={"patch_applied": "bool"},
                success_criteria=["Code patch cleanly applied without syntax errors."],
                risk=StepRiskLevel.WRITE,
                reversible=True,
                verification=VerificationSpec(
                    check_type="DIFF_CHECK",
                    target="git_diff",
                    preconditions=["Affected files exist and are writable."],
                    postconditions=["Working directory contains clean expected diff."],
                ),
                status=StepStatus.PENDING,
            )
            s4 = PlanStep(
                step_id=s4_id,
                plan_id=plan_id,
                sequence=4,
                objective="Execute automated regression and unit test suite.",
                action="test_runner",
                dependencies=[s3_id],
                inputs={"test_scope": "targeted"},
                expected_output={"tests_passed": "bool", "failures": 0},
                success_criteria=["All relevant test suites pass with 0 failures."],
                risk=StepRiskLevel.READ,
                reversible=True,
                verification=VerificationSpec(
                    check_type="OUTPUT_MATCH",
                    target="failures",
                    expected=0,
                    preconditions=["Patch applied cleanly."],
                    postconditions=["Test execution completes with zero failures."],
                ),
                status=StepStatus.PENDING,
            )
            s5 = PlanStep(
                step_id=s5_id,
                plan_id=plan_id,
                sequence=5,
                objective="Final operational verification of system health.",
                action="verify_health",
                dependencies=[s4_id],
                inputs={"endpoints": ["/health/live", "/health/ready"]},
                expected_output={"healthy": True},
                success_criteria=["All health probes report 200 OK."],
                risk=StepRiskLevel.READ,
                reversible=True,
                verification=VerificationSpec(
                    check_type="HEALTH_CHECK",
                    target="/health/ready",
                    expected="healthy",
                    invariants=["System must remain operational with zero critical alerts."],
                ),
                status=StepStatus.PENDING,
            )
            return [s1, s2, s3, s4, s5]

        # 3. RESEARCH MODE: Retrieve -> Compare -> Synthesize -> Verify Freshness
        if reasoning_mode == ReasoningMode.RESEARCH:
            s1_id = f"step_{uuid.uuid4().hex[:10]}"
            s2_id = f"step_{uuid.uuid4().hex[:10]}"
            s3_id = f"step_{uuid.uuid4().hex[:10]}"

            s1 = PlanStep(
                step_id=s1_id,
                plan_id=plan_id,
                sequence=1,
                objective="Retrieve relevant knowledge and verified documentation sources.",
                action="knowledge_search",
                inputs={"query": goal.description},
                expected_output={"sources": "list"},
                success_criteria=["At least one authoritative source retrieved."],
                risk=StepRiskLevel.READ,
                reversible=True,
                verification=VerificationSpec(check_type="SOURCE_QUERY", target="sources"),
                status=StepStatus.READY,
            )
            s2 = PlanStep(
                step_id=s2_id,
                plan_id=plan_id,
                sequence=2,
                objective="Cross-reference findings and identify any conflicting evidence.",
                action="cross_reference",
                dependencies=[s1_id],
                inputs={"sources": "sources"},
                expected_output={"consensus": "dict"},
                success_criteria=["Evidence analyzed with citations preserved."],
                risk=StepRiskLevel.READ,
                reversible=True,
                verification=VerificationSpec(check_type="OUTPUT_MATCH", target="consensus"),
                status=StepStatus.PENDING,
            )
            s3 = PlanStep(
                step_id=s3_id,
                plan_id=plan_id,
                sequence=3,
                objective="Synthesize final research report with grounded citations.",
                action="synthesize_report",
                dependencies=[s2_id],
                inputs={"format": "markdown"},
                expected_output={"report": "str"},
                success_criteria=["Report produced with bracketed citation references."],
                risk=StepRiskLevel.READ,
                reversible=True,
                verification=VerificationSpec(check_type="OUTPUT_MATCH", target="report"),
                status=StepStatus.PENDING,
            )
            return [s1, s2, s3]

        # 4. DEFAULT DECOMPOSITION: Inspect Environment -> Execute Action -> Verify
        s1_id = f"step_{uuid.uuid4().hex[:10]}"
        s2_id = f"step_{uuid.uuid4().hex[:10]}"
        s3_id = f"step_{uuid.uuid4().hex[:10]}"

        s1 = PlanStep(
            step_id=s1_id,
            plan_id=plan_id,
            sequence=1,
            objective=f"Inspect current environment state for objective: {goal.description}",
            action="inspect_environment",
            inputs={"scope": goal.scope.allowed_resources},
            expected_output={"environment_ready": True},
            success_criteria=["Environment parameters verified."],
            risk=StepRiskLevel.READ,
            reversible=True,
            verification=VerificationSpec(check_type="STATE_CHECK", target="environment_ready", expected=True),
            status=StepStatus.READY,
        )
        s2 = PlanStep(
            step_id=s2_id,
            plan_id=plan_id,
            sequence=2,
            objective=f"Execute core operation for: {goal.description}",
            action="execute_operation",
            dependencies=[s1_id],
            inputs={"goal_id": goal.goal_id, "params": goal.constraints},
            expected_output={"status": "completed"},
            success_criteria=["Operation finishes with status completed."],
            risk=StepRiskLevel.WRITE if goal.goal_type in {GoalType.OPERATIONAL, GoalType.DEVELOPMENT} else StepRiskLevel.READ,
            reversible=True,
            verification=VerificationSpec(check_type="OUTPUT_MATCH", target="status", expected="completed"),
            status=StepStatus.PENDING,
        )
        s3 = PlanStep(
            step_id=s3_id,
            plan_id=plan_id,
            sequence=3,
            objective="Verify postconditions and measurable success criteria.",
            action="verify_outcome",
            dependencies=[s2_id],
            inputs={"criteria": goal.success_criteria},
            expected_output={"criteria_met": True},
            success_criteria=["All success criteria evaluated to true."],
            risk=StepRiskLevel.READ,
            reversible=True,
            verification=VerificationSpec(
                check_type="HEALTH_CHECK",
                target="criteria_met",
                expected=True,
                postconditions=goal.success_criteria,
            ),
            status=StepStatus.PENDING,
        )
        return [s1, s2, s3]
