"""
Central Event Registry defining event types, schema contracts, replay safety, and retention (Section 74).
"""

from dataclasses import dataclass
from enum import Enum
import logging
from typing import Any
from app.events.schemas import ReplaySafety

logger = logging.getLogger("kairo.events.registry")


class EventSecurityClass(str, Enum):
    """Data classification level for events."""

    SYSTEM_PUBLIC = "SYSTEM_PUBLIC"
    INTERNAL_OPERATIONAL = "INTERNAL_OPERATIONAL"
    SENSITIVE_USER = "SENSITIVE_USER"
    AUDIT_CRITICAL = "AUDIT_CRITICAL"


@dataclass
class EventRegistration:
    """Metadata contract defining an event type in the registry."""

    event_type: str
    version: str
    description: str
    replay_safety: ReplaySafety
    security_class: EventSecurityClass
    retention_days: int = 30
    payload_schema: Any = None


class EventRegistry:
    """Thread-safe catalog of registered system events."""

    def __init__(self) -> None:
        self._registrations: dict[str, EventRegistration] = {}
        self._register_default_events()

    def register(self, reg: EventRegistration) -> None:
        """Register or update an event type definition."""
        self._registrations[reg.event_type] = reg

    def get(self, event_type: str) -> EventRegistration | None:
        """Retrieve registration for event type."""
        return self._registrations.get(event_type)

    def list_all(self) -> list[EventRegistration]:
        """Return all registered event contracts."""
        return list(self._registrations.values())

    def is_replay_safe(self, event_type: str) -> bool:
        """Check if an event type can be replayed safely."""
        reg = self.get(event_type)
        if not reg:
            return False
        return reg.replay_safety == ReplaySafety.REPLAY_SAFE

    def _register_default_events(self) -> None:
        """Initialize the canonical 18 namespaces of Kairo events."""
        defaults = [
            # Chat events
            EventRegistration("chat.message.created", "v1", "User message ingested", ReplaySafety.REPLAY_REQUIRES_REVIEW, EventSecurityClass.SENSITIVE_USER),
            EventRegistration("chat.request.started", "v1", "Chat orchestration started", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("chat.response.started", "v1", "Streaming response began", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("chat.response.completed", "v1", "Assistant response finalized", ReplaySafety.REPLAY_REQUIRES_REVIEW, EventSecurityClass.SENSITIVE_USER),
            EventRegistration("chat.request.failed", "v1", "Chat request encountered error", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),

            # Multi-Agent events
            EventRegistration("agent.started", "v1", "Agent task initiated", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("agent.step.started", "v1", "Agent step started", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("agent.step.completed", "v1", "Agent step completed", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("agent.completed", "v1", "Agent plan succeeded", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("agent.failed", "v1", "Agent task failed", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("agent.cancelled", "v1", "Agent task cancelled", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),

            # Skill events
            EventRegistration("skill.resolution.started", "v1", "Skill resolution started", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("skill.resolved", "v1", "Skill matched to intent", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("skill.started", "v1", "Skill execution begun", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("skill.completed", "v1", "Skill execution completed", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("skill.failed", "v1", "Skill execution failed", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),

            # Tool events
            EventRegistration("tool.started", "v1", "Tool execution started", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("tool.completed", "v1", "Tool execution completed", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("tool.failed", "v1", "Tool execution failed", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("tool.blocked", "v1", "Tool blocked by security", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),

            # Security & Approval events
            EventRegistration("security.blocked", "v1", "Action blocked by SecurityCenter", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL, retention_days=365),
            EventRegistration("security.allowed", "v1", "Action permitted by SecurityCenter", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL, retention_days=365),
            EventRegistration("approval.requested", "v1", "Human approval required", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL, retention_days=365),
            EventRegistration("approval.granted", "v1", "User granted approval", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL, retention_days=365),
            EventRegistration("approval.denied", "v1", "User denied approval", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL, retention_days=365),
            EventRegistration("emergency_stop.activated", "v1", "Emergency stop triggered", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL, retention_days=365),

            # Knowledge events
            EventRegistration("knowledge.created", "v1", "Knowledge node created", ReplaySafety.REPLAY_SAFE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("knowledge.updated", "v1", "Knowledge node updated", ReplaySafety.REPLAY_SAFE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("knowledge.deleted", "v1", "Knowledge node deleted", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("knowledge.index.requested", "v1", "Trigger knowledge re-index", ReplaySafety.REPLAY_SAFE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("knowledge.index.completed", "v1", "Knowledge index completed", ReplaySafety.REPLAY_SAFE, EventSecurityClass.INTERNAL_OPERATIONAL),

            # Memory events
            EventRegistration("memory.candidate.created", "v1", "Memory candidate detected", ReplaySafety.REPLAY_SAFE, EventSecurityClass.SENSITIVE_USER),
            EventRegistration("memory.created", "v1", "Durable memory saved", ReplaySafety.REPLAY_SAFE, EventSecurityClass.SENSITIVE_USER),
            EventRegistration("memory.updated", "v1", "Memory item updated", ReplaySafety.REPLAY_SAFE, EventSecurityClass.SENSITIVE_USER),
            EventRegistration("memory.deleted", "v1", "Memory item deleted", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.SENSITIVE_USER),

            # Project events
            EventRegistration("project.created", "v1", "Project created", ReplaySafety.REPLAY_SAFE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("project.updated", "v1", "Project context updated", ReplaySafety.REPLAY_SAFE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("project.archived", "v1", "Project archived", ReplaySafety.REPLAY_SAFE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("project.deleted", "v1", "Project deleted", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),

            # GitHub events
            EventRegistration("github.sync.started", "v1", "GitHub repository sync begun", ReplaySafety.REPLAY_SAFE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("github.sync.completed", "v1", "GitHub repository sync finished", ReplaySafety.REPLAY_SAFE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("github.ci.failed", "v1", "GitHub CI check run failed", ReplaySafety.REPLAY_SAFE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("github.ci.recovered", "v1", "GitHub CI check run recovered", ReplaySafety.REPLAY_SAFE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("github.pull_request.updated", "v1", "Pull request updated", ReplaySafety.REPLAY_SAFE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("github.pr.merged", "v1", "Pull request merged", ReplaySafety.REPLAY_REQUIRES_REVIEW, EventSecurityClass.INTERNAL_OPERATIONAL),

            # Research events
            EventRegistration("research.started", "v1", "Web research started", ReplaySafety.REPLAY_SAFE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("research.source.found", "v1", "Primary source discovered", ReplaySafety.REPLAY_SAFE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("research.completed", "v1", "Web research completed", ReplaySafety.REPLAY_SAFE, EventSecurityClass.INTERNAL_OPERATIONAL),

            # Evaluation events
            EventRegistration("evaluation.started", "v1", "Evaluation suite run started", ReplaySafety.REPLAY_SAFE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("evaluation.completed", "v1", "Evaluation suite run completed", ReplaySafety.REPLAY_SAFE, EventSecurityClass.INTERNAL_OPERATIONAL),

            # Automation events
            EventRegistration("workflow.started", "v1", "Automation workflow started", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("workflow.step.completed", "v1", "Workflow step succeeded", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("workflow.completed", "v1", "Automation workflow completed", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("workflow.failed", "v1", "Automation workflow failed", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),

            # Proactive & Notification events
            EventRegistration("insight.detected", "v1", "Proactive insight detected", ReplaySafety.REPLAY_REQUIRES_REVIEW, EventSecurityClass.SENSITIVE_USER),
            EventRegistration("notification.created", "v1", "User notification dispatched", ReplaySafety.REPLAY_REQUIRES_REVIEW, EventSecurityClass.SENSITIVE_USER),
            EventRegistration("notification.read", "v1", "Notification marked read", ReplaySafety.REPLAY_SAFE, EventSecurityClass.SENSITIVE_USER),
            EventRegistration("notification.dismissed", "v1", "Notification dismissed", ReplaySafety.REPLAY_SAFE, EventSecurityClass.SENSITIVE_USER),
            EventRegistration("notification.action_executed", "v1", "Notification action executed", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("notification.expired", "v1", "Notification marked expired", ReplaySafety.REPLAY_SAFE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("notification.storm_detected", "v1", "Notification storm detected and throttled", ReplaySafety.REPLAY_SAFE, EventSecurityClass.INTERNAL_OPERATIONAL),

            # Device events
            EventRegistration("device.registered", "v1", "Companion device registered", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("device.connected", "v1", "Companion device connected", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("device.disconnected", "v1", "Companion device disconnected", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("device.revoked", "v1", "Companion device revoked", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),

            # Voice, Vision, Computer events
            EventRegistration("voice.session.started", "v1", "Voice audio session started", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("vision.requested", "v1", "Vision inspection requested", ReplaySafety.REPLAY_SAFE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("computer.action.requested", "v1", "Computer control requested", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("computer.action.blocked", "v1", "Computer action blocked", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),

            # Multimodal Intelligence events (Spec 66)
            EventRegistration("multimodal.requested", "v1", "Unified multimodal request queued", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("multimodal.processing", "v1", "Multimodal media transformation active", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("multimodal.completed", "v1", "Multimodal reasoning concluded", ReplaySafety.REPLAY_REQUIRES_REVIEW, EventSecurityClass.SENSITIVE_USER),
            EventRegistration("multimodal.failed", "v1", "Multimodal processing error", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("image.processed", "v1", "Image inspected or OCR extracted", ReplaySafety.REPLAY_SAFE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("audio.transcribed", "v1", "Audio transcribed into segments", ReplaySafety.REPLAY_SAFE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("video.processed", "v1", "Video keyframes sampled and analyzed", ReplaySafety.REPLAY_SAFE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("document.processed", "v1", "Document parsed into page evidence", ReplaySafety.REPLAY_SAFE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("screen.captured", "v1", "Authorized screen capture observed", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),

            # Autonomous Task Engine events (Spec 68)
            EventRegistration("task.created", "v1", "Autonomous task created", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("task.planning", "v1", "Task planning initiated", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("task.started", "v1", "Task execution started", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("task.step.started", "v1", "Task step started", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("task.step.completed", "v1", "Task step completed", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("task.step.failed", "v1", "Task step failed", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("task.replanned", "v1", "Task replanned to new plan version", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("task.waiting_approval", "v1", "Task step waiting for user approval", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL, retention_days=365),
            EventRegistration("task.waiting_user", "v1", "Task waiting for user clarification", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("task.paused", "v1", "Task execution paused", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("task.resumed", "v1", "Task execution resumed", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("task.completed", "v1", "Task completed and verified", ReplaySafety.REPLAY_REQUIRES_REVIEW, EventSecurityClass.SENSITIVE_USER),
            EventRegistration("task.failed", "v1", "Task failed", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("task.cancelled", "v1", "Task cancelled by user", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("task.timed_out", "v1", "Task exceeded deadline or timeout", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),

            # World Model & Environment State events (Spec 56)
            EventRegistration("world.entity.created", "v1", "World entity created", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("world.entity.updated", "v1", "World entity updated", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("world.entity.deleted", "v1", "World entity deleted", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("world.state.changed", "v1", "World entity state changed", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("world.state.stale", "v1", "World entity state marked stale", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("world.conflict.detected", "v1", "World entity state conflict detected", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("world.snapshot.created", "v1", "World model point-in-time snapshot created", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),

            # Identity, Session, Device Trust, Presence & Handoff events (Task 33, Spec 56)
            EventRegistration("session.created", "v1", "Interactive identity session created", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("session.revoked", "v1", "Identity session revoked", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("session.expired", "v1", "Identity session expired", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("device.trusted", "v1", "Device explicitly marked trusted", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("presence.active", "v1", "Interface presence active", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("presence.idle", "v1", "Interface presence idle", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("presence.disconnected", "v1", "Interface presence disconnected", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("handoff.created", "v1", "Cross-interface context handoff ticket created", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("handoff.completed", "v1", "Cross-interface context handoff completed", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("handoff.expired", "v1", "Cross-interface handoff ticket expired", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),

            # Command & Intent events (Task 35)
            EventRegistration("command.received", "v1", "User natural language command received", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("intent.resolved", "v1", "Structured intent resolved from command", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("intent.clarification_requested", "v1", "Ambiguity encountered, clarification requested", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("intent.routed", "v1", "Intent dispatched to execution subsystem", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),

            # Policy & Governance events (Task 36, Spec 103)
            EventRegistration("policy.evaluated", "v1", "Policy evaluated for action", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("policy.denied", "v1", "Policy denied requested action", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("policy.approval_required", "v1", "Policy determined human approval is required", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("policy.confirmation_required", "v1", "Policy determined confirmation is required", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("policy.step_up_required", "v1", "Policy determined step-up authentication is required", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("policy.scope_violation", "v1", "Policy scope boundary violation detected", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("policy.conflict_detected", "v1", "Contradictory policy overlap detected", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),

            # Autonomous Forecasting & Early-Warning events (Task 74, Spec 50)
            EventRegistration("forecast.created", "v1", "Temporal forecast formulated and published", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("forecast.updated", "v1", "Forecast revised with new evidence or version", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("forecast.refreshed", "v1", "Forecast updated with refreshed inputs", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("forecast.outcome_observed", "v1", "Ground truth observed for active forecast", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("forecast.evaluated", "v1", "Forecast scored against realized outcome", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("forecast.drift_detected", "v1", "Process or residual error drift detected", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("forecast.calibration_degraded", "v1", "Statistical probability calibration degraded", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("forecast.invalidated", "v1", "Forecast invalidated due to assumption failure", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("early_warning.created", "v1", "Proactive early warning issued", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("early_warning.escalated", "v1", "Early warning severity escalated", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("early_warning.resolved", "v1", "Early warning resolved with explicit reason", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("propagation.analysis_created", "v1", "Systemic risk propagation analysis generated", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("propagation.cascade_detected", "v1", "Downstream cascade chain detected", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("propagation.cascade_updated", "v1", "Existing cascade updated with new downstream path", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("propagation.cascade_confirmed", "v1", "Projected cascade confirmed by empirical evidence", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("propagation.cascade_contained", "v1", "Cascade contained by isolation boundary", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("propagation.cascade_resolved", "v1", "Cascade resolved following component recovery", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("propagation.bottleneck_detected", "v1", "Critical topological bottleneck identified", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("propagation.spof_detected", "v1", "Single point of failure identified", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("propagation.forecast_created", "v1", "Forecast candidate generated from cascade path", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("propagation.drift_detected", "v1", "Structural propagation drift or regime shift detected", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),

            # Autonomous Resilience, Recovery, Containment & Adaptive Defense events (Task 76)
            EventRegistration("resilience.assessment_created", "v1", "Resilience assessment and scorecard generated", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("resilience.gap_detected", "v1", "Resilience gap or single point of failure identified", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("resilience.recovery_plan_created", "v1", "Structured recovery and containment plan formulated", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("resilience.containment_started", "v1", "Containment barrier execution initiated", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("resilience.containment_completed", "v1", "Containment barrier successfully engaged", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("resilience.recovery_started", "v1", "Recovery execution steps started", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("resilience.recovery_verification_started", "v1", "Deterministic recovery verification initiated", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("resilience.recovery_verification_failed", "v1", "Deterministic recovery verification checks failed", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("resilience.recovery_completed", "v1", "Recovery deterministically verified and completed", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("resilience.recovery_failed", "v1", "Recovery execution failed", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("resilience.recovery_rolled_back", "v1", "Recovery actions rolled back to previous state", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("resilience.residual_risk_detected", "v1", "Post-recovery residual risk report formulated", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("resilience.human_handoff_required", "v1", "Safe autonomous bounds exceeded, human handoff escalated", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),

            # Autonomous Governance, Constitutional Reasoning & Authority Engine events (Task 78)
            EventRegistration("governance.policy.evaluated", "v1", "Governance review and constitutional evaluation conducted", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("governance.policy.denied", "v1", "Autonomous action denied by governance policy or constitution", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("governance.policy.approved", "v1", "Autonomous action approved and verified authorized", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("governance.authority.conflict", "v1", "Authority discrepancy or policy tier conflict identified", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("governance.approval.required", "v1", "Action requires elevated approval per policy hierarchy", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("governance.human_review.required", "v1", "High uncertainty or irreversible action requires human judgment", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("governance.override.attempt", "v1", "Privilege escalation or control weakening attempt detected", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),

            # Native Runtime Substrate & Security Boundary events (Task 80)
            EventRegistration("runtime.started", "v1", "Native runtime daemon process initialized", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("runtime.ready", "v1", "Native runtime substrate transitioned to READY", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("runtime.degraded", "v1", "Native runtime substrate entered DEGRADED state", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("runtime.draining", "v1", "Native runtime entered DRAINING state", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("runtime.stopped", "v1", "Native runtime substrate stopped", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("runtime.request.dispatched", "v1", "Native operation dispatched to runtime socket", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("runtime.request.completed", "v1", "Native operation completed execution", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("runtime.request.cancelled", "v1", "Native operation cancelled via cancellation token", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("runtime.security.blocked_by_emergency_stop", "v1", "Native request blocked by active EmergencyStop", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("runtime.security.authorization_denied", "v1", "Native request denied by SecurityCenter policy", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),

            # Native Secure Execution Sandbox events (Task 81)
            EventRegistration("runtime.sandbox.requested", "v1", "Native sandbox execution requested", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("runtime.sandbox.accepted", "v1", "Native sandbox execution validated and accepted", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("runtime.sandbox.rejected", "v1", "Native sandbox execution rejected by admission control or preflight", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("runtime.sandbox.started", "v1", "Native sandbox execution process initiated", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("runtime.sandbox.completed", "v1", "Native sandbox execution completed within bounds", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("runtime.sandbox.failed", "v1", "Native sandbox execution process failed or exited with error", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("runtime.sandbox.cancelled", "v1", "Native sandbox execution cancelled and terminated", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("runtime.sandbox.timed_out", "v1", "Native sandbox execution exceeded deadline and was killed", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("runtime.sandbox.killed", "v1", "Native sandbox execution forcefully terminated", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("runtime.sandbox.resource_exceeded", "v1", "Native sandbox execution violated resource constraints", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("runtime.sandbox.cleanup_failed", "v1", "Native sandbox post-execution workspace or process cleanup failed", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),

            # Native Resource Enforcement & Execution Economy events (Task 82)
            EventRegistration("runtime.economy.reserved", "v1", "Native resource capacity atomically reserved prior to execution", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("runtime.economy.released", "v1", "Native resource capacity reservation released upon terminal state", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("runtime.economy.reconciled", "v1", "Execution telemetry reconciled against reserved bounds with estimation learning", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("runtime.economy.violation", "v1", "Native resource violation detected and enforced", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("runtime.economy.backpressure", "v1", "Workload rejected due to resource capacity exhaustion or pressure", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("runtime.economy.pressure_changed", "v1", "System resource pressure transitioned to new tier", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),

            # Native Tool Execution Fabric events (Task 83)
            EventRegistration("tool.native.routed", "v1", "Native tool execution routed to target substrate", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("tool.native.dispatched", "v1", "Native tool execution dispatched to Rust runtime", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("tool.native.completed", "v1", "Native tool execution completed successfully within sandbox", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("tool.native.fallback", "v1", "Native tool execution safely fell back to verified Python implementation", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("tool.native.rejected", "v1", "Native tool execution rejected by governance or admission control", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("tool.native.conformance_failed", "v1", "Native tool output verification or conformance check failed", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),

            # Native Computer Interaction Substrate events (Task 84)
            EventRegistration("computer.action.requested", "v1", "Computer interaction action requested", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("computer.action.authorized", "v1", "Computer interaction action authorized by security/governance", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("computer.action.rejected", "v1", "Computer interaction action rejected by security/governance", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("computer.action.started", "v1", "Native computer control primitive execution started", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("computer.action.completed", "v1", "Native computer control primitive completed successfully", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("computer.action.cancelled", "v1", "Native computer control action cancelled and input state released", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("computer.action.failed", "v1", "Native computer control primitive execution failed", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("computer.action.unverified", "v1", "Native computer action executed but target state unverified", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("computer.target.changed", "v1", "Target window/process mismatch detected; action safely aborted", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("computer.emergency_stop", "v1", "EmergencyStop invoked; all active input operations aborted and keys/buttons released", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),

            # Native Network Execution & Connection Fabric events (Task 85)
            EventRegistration("network.request.accepted", "v1", "Native network request accepted by policy & rate limiter", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("network.request.started", "v1", "Native network request dispatch initiated", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("network.dns.resolved", "v1", "Hostname successfully resolved to pre-validated IP", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("network.connection.opened", "v1", "Connection opened from client socket pool", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("network.ssrf.blocked", "v1", "SSRF block triggered on private/metadata IP or forbidden host", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL, retention_days=365),
            EventRegistration("network.request.completed", "v1", "HTTP request completed successfully within byte limits", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("network.request.failed", "v1", "Network request failed with connection or protocol error", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("network.request.cancelled", "v1", "Network request cancelled via cancellation registry", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("network.request.timed_out", "v1", "Network request exceeded deadline", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("network.retry.attempted", "v1", "Typed retry attempted for transient network failure", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("network.circuit_breaker.opened", "v1", "Circuit breaker opened after consecutive failures", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("network.circuit_breaker.half_open", "v1", "Circuit breaker entered probe state", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("network.circuit_breaker.closed", "v1", "Circuit breaker recovered to normal operation", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("network.rate_limit.exceeded", "v1", "Request rejected by rate limiter (RPM limit)", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("network.body.truncated", "v1", "Response body exceeded size limit and was truncated", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("network.emergency_stop", "v1", "EmergencyStop invoked; active sockets aborted", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL, retention_days=365),

            # Observability & Native Telemetry Fabric events (Task 86)
            EventRegistration("runtime.started", "v1", "Native or Python runtime substrate initialized", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("runtime.ready", "v1", "Subsystem reached READY state and accepts execution workloads", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("runtime.degraded", "v1", "Runtime entered DEGRADED state with operational warning", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("runtime.stopping", "v1", "Runtime graceful drain initiated", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("runtime.stopped", "v1", "Runtime successfully stopped and resources cleaned", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("runtime.crashed", "v1", "Subsystem failure or unhandled panic contained", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL, retention_days=365),

            EventRegistration("execution.queued", "v1", "Workload queued for execution admission", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("execution.started", "v1", "Workload execution initiated", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("execution.completed", "v1", "Workload execution terminated successfully", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("execution.failed", "v1", "Workload execution encountered error or failure", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("execution.cancelled", "v1", "Workload cancelled cooperatively or by token", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("execution.timed_out", "v1", "Workload terminated due to deadline expiration", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),

            EventRegistration("resource.reserved", "v1", "Resource capacity reserved for execution", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("resource.released", "v1", "Reserved resource capacity released", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("resource.pressure", "v1", "Resource pressure warning detected", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("resource.violation", "v1", "Resource limit violation enforced", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL, retention_days=365),

            EventRegistration("security.authorized", "v1", "Operation authorized by policy engine", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL, retention_days=365),
            EventRegistration("security.denied", "v1", "Operation denied by security policy", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL, retention_days=365),
            EventRegistration("security.policy_evaluated", "v1", "Security policy evaluation completed", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),

            EventRegistration("governance.evaluated", "v1", "Governance checks completed", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("governance.approval_required", "v1", "Action requires human approval token", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL, retention_days=365),
            EventRegistration("governance.approval_granted", "v1", "Approval granted by operator", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL, retention_days=365),
            EventRegistration("governance.approval_denied", "v1", "Approval rejected by operator", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL, retention_days=365),

            EventRegistration("learning.outcome_recorded", "v1", "Execution outcome recorded for calibration", ReplaySafety.REPLAY_SAFE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("learning.verification_failed", "v1", "Outcome verification check failed", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("learning.calibration_drift_detected", "v1", "Metacognitive calibration drift detected", ReplaySafety.REPLAY_SAFE, EventSecurityClass.INTERNAL_OPERATIONAL),

            EventRegistration("health.subsystem_degraded", "v1", "Subsystem health reported degraded", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("health.subsystem_recovered", "v1", "Subsystem health restored to healthy", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("health.subsystem_failed", "v1", "Subsystem entered failed state", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL, retention_days=365),

            EventRegistration("observability.queue_saturated", "v1", "Event queue saturated; shedding low-priority diagnostic telemetry", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),

            # Native Runtime Protocol & Distributed Execution Contract events (Task 87)
            EventRegistration("protocol.handshake.started", "v1", "Protocol negotiation handshake initiated", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("protocol.handshake.completed", "v1", "Protocol negotiation handshake completed successfully", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("protocol.handshake.failed", "v1", "Protocol negotiation handshake failed or rejected", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("protocol.session.created", "v1", "Authenticated runtime session established with attestation", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("protocol.session.invalidated", "v1", "Runtime session closed, invalidated, or expired", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("protocol.message.accepted", "v1", "Contract envelope accepted for execution", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("protocol.message.rejected", "v1", "Contract envelope rejected by validation or policy", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("protocol.message.replay_blocked", "v1", "Replayed or expired message blocked by ReplayGuard", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL, retention_days=365),
            EventRegistration("protocol.message.duplicate", "v1", "Idempotent duplicate request deduplicated or served from cache", ReplaySafety.REPLAY_SAFE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("protocol.message.timeout", "v1", "Message deadline expired prior to or during execution", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("protocol.message.cancelled", "v1", "Message execution cancelled via cooperative cancellation token", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("protocol.runtime.draining", "v1", "Runtime entered draining state for graceful shutdown or emergency stop", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("protocol.runtime.restarted", "v1", "Runtime restarted and fresh session bound", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("protocol.orphan.detected", "v1", "Orphaned in-flight execution detected following connection loss", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL, retention_days=365),
            EventRegistration("protocol.orphan.cleaned", "v1", "Orphaned execution state and resources successfully reclaimed", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("protocol.backpressure", "v1", "Runtime backpressure applied due to queue or resource saturation", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("protocol.error", "v1", "Protocol envelope format or invariant violation error", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL, retention_days=365),

            # Autonomous Runtime Reliability, Fault Injection & Self-Healing events (Task 88)
            EventRegistration("reliability.failure.detected", "v1", "Subsystem failure detected and ingested", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL, retention_days=365),
            EventRegistration("reliability.failure.classified", "v1", "Failure deterministically classified with severity and sanitized payload", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("reliability.failure.correlated", "v1", "Failure correlated with root-cause incident in causal graph", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("reliability.blast_radius.calculated", "v1", "Systemic impact and blast radius evaluated across subsystems", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("reliability.storm.detected", "v1", "High-frequency failure or retry storm detected", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("reliability.crash_loop.detected", "v1", "Component uncontainable crash loop detected; auto-restart halted", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL, retention_days=365),
            EventRegistration("reliability.recovery.selected", "v1", "Autonomous recovery strategy selected according to policy", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("reliability.recovery.authorization_requested", "v1", "Recovery action submitted for governance or security authorization", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("reliability.recovery.started", "v1", "Recovery execution started with reserved resource budget", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("reliability.recovery.progress", "v1", "Recovery action execution step progress update", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("reliability.recovery.verification_started", "v1", "Deterministic non-LLM health verification started", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("reliability.recovery.verified", "v1", "Recovery execution successfully verified against synthetic probe", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("reliability.recovery.failed", "v1", "Recovery execution attempt failed or timed out", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("reliability.recovery.escalated", "v1", "Recovery escalated to human administrator or containment", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL, retention_days=365),
            EventRegistration("reliability.capability.degraded", "v1", "Subsystem capability gracefully degraded to preserve core execution", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("reliability.capability.restored", "v1", "Gracefully degraded capability restored to full capacity", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("reliability.orphan.detected", "v1", "Orphaned process or stale resource allocation detected", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("reliability.orphan.cleaned", "v1", "Orphaned process or resource allocation successfully cleaned", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("reliability.fault_injection.triggered", "v1", "Controlled fault scenario injected for resilience verification", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL, retention_days=365),

            # Task 89: Autonomous Recovery Simulation, Digital Twin & Chaos Drills
            EventRegistration("simulation.started", "v1", "Pre-recovery digital twin simulation initialized", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("simulation.completed", "v1", "Pre-recovery simulation completed with Pareto candidate ranking", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("simulation.stale_detected", "v1", "Simulation invalidated due to state drift or TTL expiration", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("simulation.firewall_blocked", "v1", "Simulation firewall blocked mutating capability during drill", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("simulation.calibrated", "v1", "Prediction vs reality calibrated against actual recovery execution", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("simulation.chaos_injected", "v1", "Isolated chaos drill scenario executed in digital twin", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("simulation.recovery_simulated", "v1", "Target subsystem recovery counterfactual simulated", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("simulation.regression_detected", "v1", "Recovery strategy effectiveness degraded below threshold", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),

            # Task 92: Autonomous Knowledge Consolidation, Memory Reconstruction & Context Evolution
            EventRegistration("memory.candidate_created", "v1", "New candidate memory ingested and awaiting validation", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("memory.activated", "v1", "Memory validated and activated into operational context", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("memory.updated", "v1", "Memory content or structured payload updated to new version", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("memory.merged", "v1", "Repeated observation or duplicate merged into existing memory with preserved provenance", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("memory.superseded", "v1", "Memory superseded by newer verified authoritative truth", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("memory.conflicted", "v1", "Contradiction detected between competing assertions; CONFLICTED state recorded", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("memory.conflict_resolved", "v1", "Contradiction resolved through decisive evidence or authoritative correction", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("memory.marked_stale", "v1", "Memory exceeded volatility decay threshold; marked stale", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("memory.invalidated", "v1", "Memory invalidated following parent disproval or cascade", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("memory.archived", "v1", "Memory archived under retention policy", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("memory.forgotten", "v1", "Memory safely deleted or tombstoned under compliance forgetting", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL, retention_days=365),
            EventRegistration("memory.revalidated", "v1", "Autonomous revalidation scan or empirical test executed", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("memory.consolidated", "v1", "Episodic memories clustered and abstracted into semantic knowledge", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("memory.hypothesis_created", "v1", "Empirical hypothesis registered under tentative validation", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("memory.hypothesis_verified", "v1", "Hypothesis confirmed by empirical evidence and promoted", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("memory.hypothesis_rejected", "v1", "Hypothesis disproven by empirical evidence and rejected", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),

            # Task 93: Autonomous System State Graph, Self-Modeling & Operational Digital Twin
            EventRegistration("system_state.snapshot_created", "v1", "Immutable operational state snapshot captured with deterministic hash", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("system_state.delta_detected", "v1", "Operational state delta detected between consecutive snapshots", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("system_state.component_changed", "v1", "Operational component status, health score, or metadata updated", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("system_state.health_changed", "v1", "System composite health or degraded component status changed", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("system_state.dependency_changed", "v1", "Operational dependency topology or reachability modified", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("system_state.incident_impact_changed", "v1", "Active incident cascade or affected objectives updated", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("system_state.goal_blocked", "v1", "Active strategic goal blocked by degraded capability or resource constraint", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("system_state.goal_unblocked", "v1", "Strategic goal unblocked following dependency or resource recovery", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("system_state.reconciliation_started", "v1", "Startup or on-demand state reconciliation initiated", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("system_state.reconciliation_completed", "v1", "State reconciliation completed with repaired/orphaned entity audit", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("system_state.reconciliation_failed", "v1", "State reconciliation failed or encountered irreconcilable drift", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),

            # Task 94: Autonomous Decision Intelligence, Option Evaluation & Decision Memory
            EventRegistration("decision.created", "v1", "Decision request initialized under deliberate tracking", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("decision.evaluation_started", "v1", "Multi-criteria candidate evaluation initiated", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("decision.evaluation_completed", "v1", "Candidate evaluation and Pareto analysis completed", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("decision.option_added", "v1", "Candidate option registered in decision context", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("decision.option_blocked", "v1", "Candidate option blocked by hard constraint, security or governance", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("decision.constraint_detected", "v1", "Active hard/soft constraint evaluated against option", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("decision.risk_evaluated", "v1", "Risk exposure and worst-case blast radius evaluated", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("decision.simulation_required", "v1", "Pre-execution digital twin simulation mandated by policy", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("decision.simulation_completed", "v1", "Digital twin simulation completed and verified", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("decision.awaiting_approval", "v1", "Decision suspended pending formal authorization from ApprovalRegistry", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("decision.approved", "v1", "Formal approval granted by authorized actor", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("decision.rejected", "v1", "Decision rejected by approving authority", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("decision.selected", "v1", "Option selected for guarded execution handoff", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("decision.execution_started", "v1", "Action dispatched to ToolExecutor", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("decision.execution_completed", "v1", "Guarded action completed by execution substrate", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("decision.verification_started", "v1", "Post-execution telemetry and invariant verification initiated", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("decision.verified", "v1", "Action verified successful against predicted outcomes", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("decision.failed", "v1", "Execution or verification failed", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("decision.rolled_back", "v1", "Rollback procedure executed to restore safe state", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.AUDIT_CRITICAL),
            EventRegistration("decision.deferred", "v1", "Decision deferred by operator or system policy", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("decision.superseded", "v1", "Decision superseded by newer context or objective", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("decision.re_evaluation_required", "v1", "Decision invalidated by assumption or context drift", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
            EventRegistration("decision.expired", "v1", "Decision validity TTL expired; marked stale", ReplaySafety.NON_REPLAYABLE, EventSecurityClass.INTERNAL_OPERATIONAL),
        ]
        for reg in defaults:
            self.register(reg)


# Global singleton instance
_registry_instance: EventRegistry | None = None


def get_event_registry() -> EventRegistry:
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = EventRegistry()
    return _registry_instance


event_registry: EventRegistry = get_event_registry()
