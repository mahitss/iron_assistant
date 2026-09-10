"""Kairo Real-Time Situational Awareness & Event Correlation Engine (Task 60)."""

from app.situational_awareness.engine import (
    SituationalAwarenessEngine,
    situational_awareness_engine,
)
from app.situational_awareness.router import router as situations_router
from app.situational_awareness.safety import (
    SituationalAwarenessExecutionBoundaryError,
    SituationalAwarenessSafetyError,
    block_direct_situation_action,
    protect_baseline_from_incident,
    sanitize_situation_directive,
    scrub_situation_secrets,
    verify_replay_safety,
)
from app.situational_awareness.schemas import (
    AnomalySignal,
    AttentionItem,
    AutomationLevel,
    BlastRadiusImpact,
    CausalConfidence,
    CausalHypothesis,
    EventCluster,
    EventIngestRequest,
    NormalizedEvent,
    SignalBaseline,
    Situation,
    SituationSeverity,
    SituationStatus,
    SituationTimelineEntry,
    SourceTrustLevel,
    TaskImpactState,
)
from app.situational_awareness.service import (
    SituationalAwarenessService,
    situational_awareness_service,
)

__all__ = [
    "SituationalAwarenessEngine",
    "situational_awareness_engine",
    "SituationalAwarenessService",
    "situational_awareness_service",
    "situations_router",
    "SituationStatus",
    "SituationSeverity",
    "SourceTrustLevel",
    "CausalConfidence",
    "TaskImpactState",
    "AutomationLevel",
    "NormalizedEvent",
    "EventIngestRequest",
    "SignalBaseline",
    "AnomalySignal",
    "EventCluster",
    "CausalHypothesis",
    "BlastRadiusImpact",
    "SituationTimelineEntry",
    "AttentionItem",
    "Situation",
    "SituationalAwarenessSafetyError",
    "SituationalAwarenessExecutionBoundaryError",
    "block_direct_situation_action",
    "sanitize_situation_directive",
    "scrub_situation_secrets",
    "protect_baseline_from_incident",
    "verify_replay_safety",
]
