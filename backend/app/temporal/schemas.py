"""Pydantic request and response schemas for Task 111 Temporal Intelligence REST API."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.temporal.domain import (
    AttributionCertainty,
    ChangeCategory,
    ChangeRecord,
    ChangeSet,
    ChangeSummary,
    ExpectationStatus,
    ExpectedVsActual,
    StateTransition,
    TemporalAnomaly,
    TemporalAnomalyType,
    TemporalCheckpoint,
    TemporalEntity,
    TemporalEntityType,
    TemporalEvent,
    TemporalGap,
    TemporalInterval,
    TemporalQuery,
    TemporalQueryResult,
    TemporalWatermark,
    Timeline,
    TimelineSegment,
)


class TemporalQueryRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    entity_id: Optional[str] = None
    entity_type: Optional[str] = None
    from_time: Optional[datetime] = None
    to_time: Optional[datetime] = None
    scope: str = "DEFAULT"
    category: Optional[str] = None
    attribution: Optional[str] = None
    limit: int = Field(default=100, le=1000)
    include_events: bool = True
    include_transitions: bool = True
    include_anomalies: bool = True
    include_gaps: bool = True


class DiffRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    state_a: Dict[str, Any] = Field(default_factory=dict)
    state_b: Dict[str, Any] = Field(default_factory=dict)
    from_reference: str = "checkpoint_a"
    to_reference: str = "checkpoint_b"
    entity_id: str = "global"
    entity_type: str = "SYSTEM"


class CheckpointCreateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    checkpoint_type: str = "MANUAL"
    entity_states: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ReconstructionRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    subsystem: str = "telemetry"
    reconnect_time: Optional[datetime] = None
    observed_state: Dict[str, Any] = Field(default_factory=dict)
    prior_state: Dict[str, Any] = Field(default_factory=dict)


class TimelineResponse(BaseModel):
    timeline_id: str
    entity_id: Optional[str] = None
    start_time: datetime
    end_time: datetime
    total_events: int
    total_transitions: int
    events: List[TemporalEvent] = Field(default_factory=list)
    transitions: List[StateTransition] = Field(default_factory=list)


class StateAtTimeResponse(BaseModel):
    entity_id: str
    state: str
    as_of_time: str
    effective_from: Optional[str] = None
    confidence: float = 1.0
    is_historical_reconstruction: bool = True
    source: str = "system"


class HealthCheckResponse(BaseModel):
    status: str = "HEALTHY"
    subsystem: str = "temporal_intelligence"
    events_count: int = 0
    transitions_count: int = 0
    anomalies_count: int = 0
    gaps_count: int = 0
    active_watermarks: int = 0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
