"""Pydantic v2 schemas and domain models for Kairo Situational Awareness & Event Correlation Engine (Task 60)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class SituationStatus(str, Enum):
    DETECTED = "DETECTED"
    ASSESSING = "ASSESSING"
    CONFIRMED = "CONFIRMED"
    MITIGATING = "MITIGATING"
    MONITORING = "MONITORING"
    RECOVERING = "RECOVERING"
    RESOLVED = "RESOLVED"
    UNKNOWN = "UNKNOWN"
    CLOSED = "CLOSED"


class SituationSeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SourceTrustLevel(str, Enum):
    TRUSTED_SYSTEM = "TRUSTED_SYSTEM"
    VERIFIED_EXTERNAL = "VERIFIED_EXTERNAL"
    USER_REPORTED = "USER_REPORTED"
    UNVERIFIED_EXTERNAL = "UNVERIFIED_EXTERNAL"
    MODEL_GENERATED = "MODEL_GENERATED"
    SIMULATED = "SIMULATED"


class CausalConfidence(str, Enum):
    VERIFIED = "VERIFIED"
    SUPPORTED = "SUPPORTED"
    LIKELY = "LIKELY"
    SPECULATIVE = "SPECULATIVE"
    UNKNOWN = "UNKNOWN"


class TaskImpactState(str, Enum):
    UNBLOCKED = "UNBLOCKED"
    AT_RISK = "AT_RISK"
    BLOCKED = "BLOCKED"
    INVALIDATED = "INVALIDATED"
    UNKNOWN = "UNKNOWN"


class AutomationLevel(str, Enum):
    OBSERVE_ONLY = "OBSERVE_ONLY"
    RECOMMEND = "RECOMMEND"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    AUTHORIZED_AUTOMATION = "AUTHORIZED_AUTOMATION"


class NormalizedEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:10]}")
    situation_id: str | None = None
    event_type: str
    source: str
    source_trust: SourceTrustLevel = SourceTrustLevel.TRUSTED_SYSTEM
    environment: str = "development"
    resource: str | None = None
    subject: str
    actor: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    severity: SituationSeverity = SituationSeverity.INFO
    confidence: float = 1.0
    provenance: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None
    causation_id: str | None = None
    is_anomaly: bool = False
    occurred_at: datetime = Field(default_factory=_now_utc)
    received_at: datetime = Field(default_factory=_now_utc)


class EventIngestRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    event_type: str
    source: str
    subject: str
    environment: str = "development"
    resource: str | None = None
    actor: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    severity: SituationSeverity = SituationSeverity.INFO
    occurred_at: datetime | None = None
    source_trust: SourceTrustLevel | None = None


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
    last_calibrated_at: datetime = Field(default_factory=_now_utc)


class AnomalySignal(BaseModel):
    model_config = ConfigDict(extra="ignore")

    anomaly_id: str = Field(default_factory=lambda: f"anom_{uuid.uuid4().hex[:8]}")
    signal_name: str
    resource: str
    observed_value: float
    baseline_mean: float
    deviation_sigmas: float
    confidence: float = 0.9
    detected_at: datetime = Field(default_factory=_now_utc)


class EventCluster(BaseModel):
    model_config = ConfigDict(extra="ignore")

    cluster_id: str = Field(default_factory=lambda: f"cls_{uuid.uuid4().hex[:8]}")
    events: list[NormalizedEvent] = Field(default_factory=list)
    time_window_seconds: float = 300.0
    resources: list[str] = Field(default_factory=list)
    environment: str = "development"
    confidence: float = 1.0
    rationale: str = ""


class CausalHypothesis(BaseModel):
    model_config = ConfigDict(extra="ignore")

    hypothesis_id: str = Field(default_factory=lambda: f"hyp_{uuid.uuid4().hex[:8]}")
    situation_id: str
    candidate_cause: str
    confidence_level: CausalConfidence = CausalConfidence.LIKELY
    evidence_summary: str = ""
    recommended_diagnostics: list[str] = Field(default_factory=list)
    status: str = "UNVERIFIED"
    created_at: datetime = Field(default_factory=_now_utc)


class BlastRadiusImpact(BaseModel):
    model_config = ConfigDict(extra="ignore")

    situation_id: str
    known_affected_services: list[str] = Field(default_factory=list)
    potentially_affected_services: list[str] = Field(default_factory=list)
    affected_resources: list[str] = Field(default_factory=list)
    affected_plans: list[str] = Field(default_factory=list)
    affected_goals: list[str] = Field(default_factory=list)
    task_impacts: dict[str, TaskImpactState] = Field(default_factory=dict)
    confidence: float = 0.85


class SituationTimelineEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    entry_id: str = Field(default_factory=lambda: f"tl_{uuid.uuid4().hex[:8]}")
    timestamp: datetime = Field(default_factory=_now_utc)
    event_type: str
    summary: str
    is_inference: bool = False
    evidence_id: str | None = None


class AttentionItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    item_id: str = Field(default_factory=lambda: f"att_{uuid.uuid4().hex[:8]}")
    situation_id: str
    title: str
    severity: SituationSeverity
    urgency: float = 0.5
    composite_priority: float = 0.5
    requires_human_action: bool = False
    created_at: datetime = Field(default_factory=_now_utc)


class Situation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    situation_id: str = Field(default_factory=lambda: f"sit_{uuid.uuid4().hex[:10]}")
    title: str
    description: str = ""
    status: SituationStatus = SituationStatus.DETECTED
    severity: SituationSeverity = SituationSeverity.MEDIUM
    confidence: float = 1.0
    environment: str = "development"
    affected_resources: list[str] = Field(default_factory=list)
    affected_services: list[str] = Field(default_factory=list)
    affected_plans: list[str] = Field(default_factory=list)
    affected_goals: list[str] = Field(default_factory=list)
    current_state: dict[str, Any] = Field(default_factory=dict)
    expected_state: dict[str, Any] = Field(default_factory=dict)
    timeline: list[SituationTimelineEntry] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    hypotheses: list[CausalHypothesis] = Field(default_factory=list)
    risk_assessment: dict[str, Any] = Field(default_factory=dict)
    next_steps: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    flapping_count: int = 0
    last_observed_at: datetime = Field(default_factory=_now_utc)
    created_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)
