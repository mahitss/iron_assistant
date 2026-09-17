"""Pydantic v2 schemas and domain models for Kairo Situational Awareness & Signal Fusion Engine (Task 99)."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.situational_awareness.domain import (
    CausalStatus,
    ProactivePolicyCapability,
    SignalRecord,
    SituationContextRecord,
    SituationInterventionRecord,
    SituationLifecycleState,
    SituationPatternRecord,
    SituationRecord,
    SituationSeverity,
    SituationStatus,
    SituationSuppressionRecord,
    SituationTimelineEntry,
    SituationType,
    SourceTrustLevel,
    utc_now,
)

# Backward-compatibility alias
Situation = SituationRecord


class NormalizedEvent(BaseModel):
    """Normalized operational event for Task 60 backward compatibility."""
    model_config = ConfigDict(extra="ignore")

    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:10]}")
    situation_id: Optional[str] = None
    event_type: str
    source: str
    source_trust: SourceTrustLevel = SourceTrustLevel.TRUSTED_SYSTEM
    environment: str = "development"
    resource: Optional[str] = None
    subject: str
    actor: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)
    severity: SituationSeverity = SituationSeverity.INFO
    confidence: float = 1.0
    provenance: dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    is_anomaly: bool = False
    original_source: Optional[str] = None
    is_sanitized: bool = True
    occurred_at: datetime = Field(default_factory=utc_now)
    received_at: datetime = Field(default_factory=utc_now)

    def to_signal(self) -> SignalRecord:
        keys = [self.subject] if self.subject else []
        if self.resource and self.resource not in keys:
            keys.append(self.resource)
        return SignalRecord(
            signal_id=self.event_id,
            source_type="EVENT",
            source_id=self.source,
            signal_type=self.event_type,
            subject=self.subject or self.resource or "system",
            entity=self.resource,
            scope=self.environment.upper(),
            severity=self.severity,
            payload=self.payload,
            confidence=self.confidence,
            trust_classification=self.source_trust,
            observed_at=self.occurred_at,
            received_at=self.received_at,
            provenance=self.provenance,
            correlation_id=self.correlation_id,
            correlation_keys=keys,
            metadata={"severity": self.severity.value, "actor": self.actor},
        )


class SignalIngestRequest(BaseModel):
    """Structured request to ingest an operational signal (Section 3, 4)."""
    model_config = ConfigDict(extra="ignore")

    source_type: str = "TELEMETRY"
    source_id: str = ""
    source_version: str = "v1"
    signal_type: str = "OBSERVATION"
    subject: str = ""
    entity: Optional[str] = None
    scope: str = "SYSTEM"
    severity: SituationSeverity = SituationSeverity.INFO
    payload: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0
    provenance: dict[str, Any] = Field(default_factory=dict)
    trust_level: SourceTrustLevel = SourceTrustLevel.TRUSTED_INTERNAL
    sensitivity: str = "INTERNAL"
    correlation_keys: list[str] = Field(default_factory=list)
    causal_refs: list[str] = Field(default_factory=list)
    world_state_refs: list[str] = Field(default_factory=list)
    decision_refs: list[str] = Field(default_factory=list)
    trace_id: Optional[str] = None
    correlation_id: Optional[str] = None
    event_id: Optional[str] = None
    observed_at: Optional[datetime] = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_signal_req(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "source_system" in data and not data.get("source_id"):
                data["source_id"] = data["source_system"]
                if "source_type" not in data:
                    data["source_type"] = data["source_system"]
            if "source_trust" in data and "trust_level" not in data:
                data["trust_level"] = data["source_trust"]
            if "causal_references" in data and "causal_refs" not in data:
                data["causal_refs"] = data["causal_references"]
            if "world_state_references" in data and "world_state_refs" not in data:
                data["world_state_refs"] = data["world_state_references"]
            if "decision_references" in data and "decision_refs" not in data:
                data["decision_refs"] = data["decision_references"]
        return data

    @property
    def source_system(self) -> str:
        return self.source_id or self.source_type

    @property
    def source_trust(self) -> SourceTrustLevel:
        return self.trust_level

    @property
    def causal_references(self) -> list[str]:
        return self.causal_refs

    @property
    def world_state_references(self) -> list[str]:
        return self.world_state_refs



class EventIngestRequest(BaseModel):
    """Backward-compatible event ingestion request (Task 60 compatibility)."""
    model_config = ConfigDict(extra="ignore")

    event_type: str
    source: str
    subject: str
    environment: str = "development"
    resource: Optional[str] = None
    actor: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)
    severity: SituationSeverity = SituationSeverity.INFO
    occurred_at: Optional[datetime] = None
    source_trust: Optional[SourceTrustLevel] = None


class SituationFilterQuery(BaseModel):
    """Query parameters for multi-dimensional situation filtering (Section 39)."""
    lifecycle_state: Optional[SituationLifecycleState] = None
    situation_type: Optional[SituationType] = None
    severity: Optional[SituationSeverity] = None
    scope: Optional[str] = None
    project_id: Optional[str] = None
    affected_entity: Optional[str] = None
    min_confidence: Optional[float] = None
    unresolved_only: bool = True
    limit: int = 50
    offset: int = 0


class SituationSuppressRequest(BaseModel):
    """Request payload to suppress a situation with auditable reason (Section 22)."""
    reason: str
    duration_seconds: Optional[float] = None
    suppressed_by: str = "user"


class SituationResolveRequest(BaseModel):
    """Request payload to resolve a situation with verified evidence (Section 10)."""
    model_config = ConfigDict(extra="ignore")
    resolution_summary: str = "Situation resolved with verified evidence"
    verified_evidence: dict[str, Any] = Field(default_factory=dict)
    verification_evidence: dict[str, Any] = Field(default_factory=dict)
    resolved_by: str = "user"
    actor: Optional[str] = None

    def __init__(self, **data: Any) -> None:
        if "verification_evidence" in data and not data.get("verified_evidence"):
            data["verified_evidence"] = data["verification_evidence"]
        elif "verified_evidence" in data and not data.get("verification_evidence"):
            data["verification_evidence"] = data["verified_evidence"]
        super().__init__(**data)


class SituationInvestigateRequest(BaseModel):
    """Request to trigger bounded multi-agent or tool investigation (Section 27)."""
    model_config = ConfigDict(extra="ignore")
    scope: Optional[str] = None
    investigation_depth: int = 2
    max_agents: int = 3
    requested_by: str = "orchestrator"


class SituationStatsResponse(BaseModel):
    """Operational statistics and metrics overview (Section 37, 40)."""
    total_situations: int = 0
    active_count: int = 0
    forming_count: int = 0
    escalating_count: int = 0
    intervention_active_count: int = 0
    observing_count: int = 0
    resolved_today_count: int = 0
    suppressed_count: int = 0
    unknown_count: int = 0
    signals_processed_total: int = 0
    storm_backpressure_active: bool = False
    average_correlation_score: float = 0.0


# Legacy Task 60 schema models for backward compatibility
class SignalBaseline(BaseModel):
    model_config = ConfigDict(extra="ignore")
    baseline_id: str = Field(default_factory=lambda: f"bsl_{uuid.uuid4().hex[:8]}")
    signal_name: str
    resource: str
    environment: str = "development"
    mean_val: float = 0.0
    std_dev: float = 1.0
    min_val: float = 0.0
    max_val: float = 100.0
    sample_count: int = 0
    version: int = 1
    is_quarantined: bool = False
    last_calibrated_at: datetime = Field(default_factory=utc_now)


class EventCluster(BaseModel):
    model_config = ConfigDict(extra="ignore")
    cluster_id: str = Field(default_factory=lambda: f"cluster_{uuid.uuid4().hex[:8]}")
    events: list[Any] = Field(default_factory=list)
    resources: list[str] = Field(default_factory=list)
    environment: str = "development"
    confidence: float = 1.0
    rationale: str = ""


class AnomalySignal(BaseModel):
    model_config = ConfigDict(extra="ignore")
    anomaly_id: str = Field(default_factory=lambda: f"anom_{uuid.uuid4().hex[:8]}")
    signal_name: str
    resource: str
    observed_value: float
    baseline_mean: float
    deviation_sigmas: float
    confidence: float = 0.9
    detected_at: datetime = Field(default_factory=utc_now)


class CausalConfidence(str, Enum):
    # Task 60 backward-compatible values
    VERIFIED = "VERIFIED"
    SUPPORTED = "SUPPORTED"
    LIKELY = "LIKELY"
    SPECULATIVE = "SPECULATIVE"
    # Task 99 values
    CONFIRMED = "CONFIRMED"
    PLAUSIBLE = "PLAUSIBLE"
    UNCERTAIN = "UNCERTAIN"
    UNKNOWN = "UNKNOWN"
    DISPROVEN = "DISPROVEN"


class CausalHypothesis(BaseModel):
    model_config = ConfigDict(extra="ignore")
    hypothesis_id: str = Field(default_factory=lambda: f"hyp_{uuid.uuid4().hex[:8]}")
    situation_id: str
    candidate_cause: str
    confidence_level: CausalConfidence | str = CausalConfidence.PLAUSIBLE
    evidence_summary: str = ""
    recommended_diagnostics: list[str] = Field(default_factory=list)
    status: str = "UNVERIFIED"
    created_at: datetime = Field(default_factory=utc_now)


class TaskImpactState(str, Enum):
    UNAFFECTED = "UNAFFECTED"
    UNBLOCKED = "UNBLOCKED"
    DEGRADED = "DEGRADED"
    BLOCKED = "BLOCKED"
    AT_RISK = "AT_RISK"
    INVALIDATED = "INVALIDATED"


class AutomationLevel(str, Enum):
    AUTONOMOUS = "AUTONOMOUS"
    RECOMMEND = "RECOMMEND"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    MANUAL_ONLY = "MANUAL_ONLY"


class BlastRadiusImpact(BaseModel):
    model_config = ConfigDict(extra="ignore")
    situation_id: str
    known_affected_services: list[str] = Field(default_factory=list)
    potentially_affected_services: list[str] = Field(default_factory=list)
    affected_resources: list[str] = Field(default_factory=list)
    affected_plans: list[str] = Field(default_factory=list)
    affected_goals: list[str] = Field(default_factory=list)
    task_impacts: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.85


class AttentionItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    item_id: str = Field(default_factory=lambda: f"att_{uuid.uuid4().hex[:8]}")
    situation_id: str
    title: str
    severity: SituationSeverity = SituationSeverity.MEDIUM
    urgency: float = 0.5
    composite_priority: float = 0.5
    requires_human_action: bool = False
    created_at: datetime = Field(default_factory=utc_now)
