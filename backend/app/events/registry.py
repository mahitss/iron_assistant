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
