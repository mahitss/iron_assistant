"""Skill Execution Engine with security evaluation, plan execution, and evidence collection."""

import logging
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from app.config.settings import get_settings
from app.context.resolver import ContextResolver
from app.knowledge.service import KnowledgeFabricService
from app.security.audit import AuditLogger
from app.security.center import SecurityCenter, get_security_center
from app.skills.permissions import SkillPermissionEnforcer
from app.skills.planner import SkillPlanner
from app.skills.registry import SkillRegistry
from app.skills.schemas import (
    SkillExecutionRecord,
    SkillExecutionState,
    SkillManifest,
    SkillPlan,
    SkillResult,
)
from app.tools.executor import ToolExecutor
from app.tools.schemas import ToolCall

logger = logging.getLogger("kairo.skills.executor")


class SkillExecutor:
    """Executes validated skills against tool registry, SecurityCenter, and context engine."""

    def __init__(
        self,
        registry: SkillRegistry,
        tool_executor: ToolExecutor,
        security_center: SecurityCenter | None = None,
        context_resolver: ContextResolver | None = None,
        knowledge_service: KnowledgeFabricService | None = None,
    ) -> None:
        self.registry = registry
        self.tool_executor = tool_executor
        self.security_center = security_center or get_security_center()
        self.permission_enforcer = SkillPermissionEnforcer(self.security_center)
        self.planner = SkillPlanner()
        self.context_resolver = context_resolver or ContextResolver()
        self.knowledge_service = knowledge_service
        self.settings = get_settings()

        # In-memory execution registry for fast status inspection and cancellation
        self._executions: dict[str, SkillExecutionRecord] = {}
        self._cancel_flags: dict[str, bool] = {}

    def get_execution(self, execution_id: str) -> SkillExecutionRecord | None:
        """Fetch the execution record by ID."""
        return self._executions.get(execution_id)

    def cancel_execution(self, execution_id: str) -> bool:
        """Flag an active skill execution for immediate cooperative cancellation."""
        if execution_id in self._executions:
            self._cancel_flags[execution_id] = True
            rec = self._executions[execution_id]
            if rec.status in (
                SkillExecutionState.PENDING,
                SkillExecutionState.PLANNING,
                SkillExecutionState.WAITING_APPROVAL,
                SkillExecutionState.RUNNING,
            ):
                rec.status = SkillExecutionState.CANCELLED
            logger.info("Flagged execution '%s' for cancellation", execution_id)
            return True
        return False

    def cancel(self, execution_id: str, reason: str = "") -> bool:
        """Alias for cancel_execution."""
        return self.cancel_execution(execution_id)

    async def execute(
        self,
        manifest: SkillManifest,
        inputs: dict[str, Any],
        user_id: str = "default_user",
        project_id: str | None = None,
        device_id: str | None = None,
        session_id: str | None = None,
        db_session: Any = None,
    ) -> SkillResult:
        """Execute a skill end-to-end through validation, planning, security gating, and tool dispatch."""
        execution_id = f"exec_{uuid.uuid4().hex[:12]}"
        start_time = datetime.now(UTC)
        start_ticks = time.perf_counter()

        record = SkillExecutionRecord(
            execution_id=execution_id,
            skill_id=manifest.id,
            skill_version=manifest.version,
            status=SkillExecutionState.PENDING,
            summary="Execution initiated",
            started_at=start_time,
            project_id=project_id,
            device_id=device_id,
        )
        self._executions[execution_id] = record

        # 1. Validate inputs against input_schema
        validation_err = self._validate_inputs(manifest, inputs)
        if validation_err:
            return await self._terminate_failure(
                record, validation_err, start_time, start_ticks, user_id, session_id, db_session
            )

        # 2. Context resolution
        try:
            if project_id and self.context_resolver:
                _context_data = await self.context_resolver.resolve(
                    user_id=user_id,
                    project_id=project_id,
                    user_message=inputs.get("query", inputs.get("goal", "")),
                    session=db_session,
                )
        except Exception as exc:
            logger.warning("Context resolution failed non-critically for skill '%s': %s", manifest.id, exc)

        # 3. Security Evaluation & Authorization Check
        record.status = SkillExecutionState.PLANNING
        allowed, denial_reason, approval_required = await self.permission_enforcer.authorize_skill_execution(
            manifest=manifest,
            user_id=user_id,
            inputs=inputs,
            project_id=project_id,
            device_id=device_id,
            session_id=session_id,
            db_session=db_session,
        )

        if not allowed:
            await AuditLogger.log_event(
                db_session=db_session,
                user_id=user_id,
                event_type="skill.blocked",
                decision="DENIED",
                success=False,
                metadata={"skill_id": manifest.id, "reason": denial_reason},
            )
            return await self._terminate_failure(
                record,
                denial_reason or "Skill execution denied by Security Center.",
                start_time,
                start_ticks,
                user_id,
                session_id,
                db_session,
            )

        # 4. Approval Checkpoint
        if approval_required:
            record.status = SkillExecutionState.WAITING_APPROVAL
            record.approval_id = f"appr_{uuid.uuid4().hex[:10]}"
            record.summary = denial_reason or "Explicit user approval required before proceeding."
            await AuditLogger.log_event(
                db_session=db_session,
                user_id=user_id,
                event_type="skill.approval_required",
                decision="REQUIRES_APPROVAL",
                success=True,
                metadata={"skill_id": manifest.id, "execution_id": execution_id},
            )
            elapsed = (time.perf_counter() - start_ticks) * 1000.0
            appr_res = SkillResult(
                execution_id=execution_id,
                skill_id=manifest.id,
                skill_version=manifest.version,
                status=SkillExecutionState.WAITING_APPROVAL,
                summary=record.summary,
                started_at=start_time,
                duration_ms=elapsed,
                project_id=project_id,
                device_id=device_id,
                provenance={
                    "skill_id": manifest.id,
                    "skill_version": manifest.version,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "project_id": project_id,
                },
            )
            record.result = appr_res
            return appr_res

        # 5. Plan Generation
        plan: SkillPlan = self.planner.create_plan(manifest, inputs)
        record.plan = plan
        record.status = SkillExecutionState.RUNNING

        # 6. Sequential Tool Execution Loop with Timeout & Cancellation Bounds
        timeout_sec = min(
            manifest.execution_limits.timeout_seconds,
            self.settings.KAIRO_SKILL_TIMEOUT_SECONDS,
        )
        evidence: list[dict[str, Any]] = []
        sources: list[str] = []
        step_outputs: list[str] = []

        try:
            for step in plan.steps:
                # Check cooperative cancellation
                if self._cancel_flags.get(execution_id):
                    record.status = SkillExecutionState.CANCELLED
                    record.summary = "Skill execution was cancelled by user."
                    elapsed = (time.perf_counter() - start_ticks) * 1000.0
                    return SkillResult(
                        execution_id=execution_id,
                        skill_id=manifest.id,
                        skill_version=manifest.version,
                        status=SkillExecutionState.CANCELLED,
                        summary=record.summary,
                        started_at=start_time,
                        duration_ms=elapsed,
                    )

                # Check timeout
                current_duration = time.perf_counter() - start_ticks
                if current_duration > timeout_sec:
                    record.status = SkillExecutionState.TIMED_OUT
                    record.summary = f"Skill execution exceeded maximum timeout of {timeout_sec}s."
                    elapsed = current_duration * 1000.0
                    return SkillResult(
                        execution_id=execution_id,
                        skill_id=manifest.id,
                        skill_version=manifest.version,
                        status=SkillExecutionState.TIMED_OUT,
                        summary=record.summary,
                        started_at=start_time,
                        duration_ms=elapsed,
                    )

                # Enforce Tool Allowlist (Section 29 & 80)
                if manifest.all_tools and step.tool_name not in manifest.all_tools:
                    step.status = "failed"
                    step.error = (
                        f"Security violation: Tool '{step.tool_name}' is not in the declared "
                        f"allowlist for skill '{manifest.id}'."
                    )
                    logger.warning(
                        "Tool allowlist violation in skill '%s': rejected '%s'",
                        manifest.id,
                        step.tool_name,
                    )
                    await AuditLogger.log_event(
                        db_session=db_session,
                        user_id=user_id,
                        session_id=session_id,
                        event_type="skill.tool_violation",
                        decision="DENIED",
                        success=False,
                        metadata={"skill_id": manifest.id, "tool_name": step.tool_name},
                    )
                    continue

                # Execute Tool Call
                step.status = "running"
                call = ToolCall(
                    id=f"call_{uuid.uuid4().hex[:8]}",
                    name=step.tool_name,
                    arguments=step.arguments,
                )
                tool_res = await self.tool_executor.execute(
                    tool_call=call,
                    user_id=user_id,
                    session_id=session_id,
                    db_session=db_session,
                )

                if tool_res.success:
                    step.status = "completed"
                    out_val = getattr(tool_res, "result", None) if getattr(tool_res, "result", None) is not None else getattr(tool_res, "output", None)
                    step.output = out_val
                    step_outputs.append(str(out_val)[:300])

                    # Collect evidence
                    evidence.append(
                        {
                            "step": step.step_number,
                            "tool": step.tool_name,
                            "output": out_val,
                        }
                    )
                    if isinstance(out_val, dict) and "url" in out_val:
                        sources.append(out_val["url"])
                else:
                    step.status = "failed"
                    step.error = tool_res.error
                    logger.warning(
                        "Step %d (%s) failed: %s", step.step_number, step.tool_name, tool_res.error
                    )

        except Exception as exc:
            logger.error("Unexpected error executing skill '%s': %s", manifest.id, exc, exc_info=True)
            return await self._terminate_failure(
                record,
                f"Internal execution error: {exc}",
                start_time,
                start_ticks,
                user_id,
                session_id,
                db_session,
            )

        # 7. Synthesize Summary Result
        elapsed_ms = (time.perf_counter() - start_ticks) * 1000.0
        record.status = SkillExecutionState.COMPLETED
        summary_text = (
            f"Skill '{manifest.name}' completed {len(plan.steps)} steps successfully."
            if not any(s.status == "failed" for s in plan.steps)
            else f"Skill '{manifest.name}' completed with partial warnings."
        )
        record.summary = summary_text

        result = SkillResult(
            execution_id=execution_id,
            skill_id=manifest.id,
            skill_version=manifest.version,
            status=SkillExecutionState.COMPLETED,
            summary=summary_text,
            evidence=evidence,
            sources=sources,
            plan=plan,
            started_at=start_time,
            completed_at=datetime.now(UTC),
            duration_ms=elapsed_ms,
            project_id=project_id,
            device_id=device_id,
            provenance={
                "skill_id": manifest.id,
                "skill_version": manifest.version,
                "timestamp": datetime.now(UTC).isoformat(),
                "project_id": project_id,
            },
        )

        # 8. Audit Event
        await AuditLogger.log_event(
            db_session=db_session,
            user_id=user_id,
            event_type="skill.executed",
            decision="ALLOWED",
            success=True,
            metadata={
                "skill_id": manifest.id,
                "execution_id": execution_id,
                "duration_ms": elapsed_ms,
                "steps_completed": len(plan.steps),
            },
        )

        record.result = result
        return result

    async def execute_request(self, request: Any, db_session: Any = None) -> SkillResult:
        """Execute a skill from a structured SkillExecutionRequest or dict."""
        if hasattr(request, "skill_id"):
            skill_id = request.skill_id
            inputs = request.inputs
            user_id = getattr(request, "user_id", "default_user")
            project_id = getattr(request, "project_id", None)
            device_id = getattr(request, "device_id", None)
            context = getattr(request, "context", None)
            if isinstance(context, dict):
                if not device_id:
                    device_id = context.get("device_id")
                if not project_id:
                    project_id = context.get("project_id")
            session_id = getattr(request, "session_id", None)
        elif isinstance(request, dict):
            skill_id = request.get("skill_id")
            inputs = request.get("inputs", {})
            user_id = request.get("user_id", "default_user")
            project_id = request.get("project_id")
            device_id = request.get("device_id")
            context = request.get("context")
            if isinstance(context, dict):
                if not device_id:
                    device_id = context.get("device_id")
                if not project_id:
                    project_id = context.get("project_id")
            session_id = request.get("session_id")
        else:
            skill_id = getattr(request, "skill_id", "unknown")
            inputs = getattr(request, "inputs", {})
            user_id = getattr(request, "user_id", "default_user")
            project_id = getattr(request, "project_id", None)
            device_id = getattr(request, "device_id", None)
            session_id = getattr(request, "session_id", None)

        manifest = self.registry.get(skill_id, user_id=user_id)
        if not manifest:
            exec_id = f"exec_{uuid.uuid4().hex[:12]}"
            failed_record = SkillExecutionRecord(
                execution_id=exec_id,
                skill_id=skill_id or "unknown",
                skill_version="0.0.0",
                status=SkillExecutionState.FAILED,
                error=f"Skill '{skill_id}' is not registered.",
            )
            self._executions[exec_id] = failed_record
            failed_res = SkillResult(
                execution_id=exec_id,
                skill_id=skill_id or "unknown",
                skill_version="0.0.0",
                status=SkillExecutionState.FAILED,
                summary=f"Skill '{skill_id}' not found.",
                error=failed_record.error,
                started_at=datetime.now(UTC),
            )
            failed_record.result = failed_res
            return failed_res

        if not manifest.enabled:
            exec_id = f"exec_{uuid.uuid4().hex[:12]}"
            failed_record = SkillExecutionRecord(
                execution_id=exec_id,
                skill_id=manifest.id,
                skill_version=manifest.version,
                status=SkillExecutionState.FAILED,
                error=f"Skill '{manifest.id}' is disabled.",
            )
            self._executions[exec_id] = failed_record
            failed_res = SkillResult(
                execution_id=exec_id,
                skill_id=manifest.id,
                skill_version=manifest.version,
                status=SkillExecutionState.FAILED,
                summary=f"Skill '{manifest.id}' is disabled.",
                error=failed_record.error,
                started_at=datetime.now(UTC),
            )
            failed_record.result = failed_res
            return failed_res

        return await self.execute(
            manifest=manifest,
            inputs=inputs,
            user_id=user_id,
            project_id=project_id,
            device_id=device_id,
            session_id=session_id,
            db_session=db_session,
        )

    def _validate_inputs(self, manifest: SkillManifest, inputs: dict[str, Any]) -> str | None:
        """Validate input arguments against declared input_schema properties."""
        schema = manifest.input_schema
        if not schema:
            return None

        required_props = schema.get("required", [])
        for req in required_props:
            if req not in inputs or inputs[req] is None or inputs[req] == "":
                return f"Missing required parameter '{req}' for skill '{manifest.id}'."

        return None

    async def _terminate_failure(
        self,
        record: SkillExecutionRecord,
        error_msg: str,
        start_time: datetime,
        start_ticks: float,
        user_id: str,
        session_id: str | None,
        db_session: Any,
    ) -> SkillResult:
        """Record and return failed execution result."""
        record.status = SkillExecutionState.FAILED
        record.error = error_msg
        record.summary = f"Execution failed: {error_msg}"
        elapsed = (time.perf_counter() - start_ticks) * 1000.0

        res = SkillResult(
            execution_id=record.execution_id,
            skill_id=record.skill_id,
            skill_version=record.skill_version,
            status=SkillExecutionState.FAILED,
            summary=record.summary,
            error=error_msg,
            started_at=start_time,
            completed_at=datetime.now(UTC),
            duration_ms=elapsed,
            project_id=record.project_id,
            device_id=record.device_id,
        )
        record.result = res
        return res
