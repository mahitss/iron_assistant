"""Pydantic Request and Response Schemas for Perception REST API (Task 46)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PerceptionSourceRegisterRequest(BaseModel):
    type: str = Field(..., description="Source type: DEVICE, BROWSER, GIT, SERVICE, etc.")
    name: str = Field(..., description="Descriptive source name")
    capabilities: List[str] = Field(default_factory=list)
    reliability: float = Field(1.0, ge=0.0, le=1.0)
    privacy_level: str = "INTERNAL"
    allowed_users: List[str] = Field(default_factory=lambda: ["*"])
    allowed_projects: List[str] = Field(default_factory=lambda: ["*"])
    allowed_devices: List[str] = Field(default_factory=lambda: ["*"])
    allowed_directories: List[str] = Field(default_factory=list)
    allowed_domains: List[str] = Field(default_factory=list)
    require_explicit_consent: bool = False


class PerceptionSourceResponse(BaseModel):
    source_id: str
    type: str
    name: str
    capabilities: List[str]
    reliability: float
    status: str
    privacy_level: str
    last_seen: str
    scope: Dict[str, Any]


class PerceptionEventIngestRequest(BaseModel):
    event_type: str = "UPDATED"
    subject: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    sequence: int = 0
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    environment: str = "DEVELOPMENT"
    has_explicit_user_consent: bool = False
    expected_status: Optional[str] = None


class PerceptionEventIngestResponse(BaseModel):
    status: str
    observation_id: Optional[str] = None
    event_id: Optional[str] = None
    source_id: str
    subject: str
    event_type: str
    confidence: float
    latency_ms: float
    change_detected: bool
    change_id: Optional[str] = None
    significance: Optional[str] = None
    anomaly_detected: bool
    anomaly_id: Optional[str] = None


class ObservationResponse(BaseModel):
    observation_id: str
    source_id: str
    source_type: str
    subject: str
    event_type: str
    payload_reference: str
    observed_at: str
    received_at: str
    age_seconds: float
    latency_ms: float
    confidence: float
    correlation_id: Optional[str] = None
    scope: Dict[str, Any]
    data: Dict[str, Any]


class ChangeEventResponse(BaseModel):
    change_id: str
    subject: str
    change_type: str
    significance: str
    environment: str
    before: Any
    after: Any
    timestamp: str


class SnapshotCreateRequest(BaseModel):
    environment: str = "DEVELOPMENT"
    is_atomic: bool = True
    missing_sources: List[str] = Field(default_factory=list)


class SnapshotResponse(BaseModel):
    snapshot_id: str
    version: int
    environment: str
    timestamp: str
    devices: Dict[str, Any]
    apps: Dict[str, Any]
    services: Dict[str, Any]
    repositories: Dict[str, Any]
    deployments: Dict[str, Any]
    tasks: Dict[str, Any]
    agents: Dict[str, Any]
    is_atomic: bool
    missing_sources: List[str]


class SituationResponse(BaseModel):
    situation_id: str
    version: int
    scope: Dict[str, Any]
    summary: str
    observed_facts: List[str]
    inferences: List[str]
    changes: List[Dict[str, Any]]
    anomalies: List[Dict[str, Any]]
    active_tasks: List[str]
    risks: List[str]
    uncertainties: List[str]
    timestamp: str


class HealthMetricsResponse(BaseModel):
    events_received: int
    events_processed: int
    events_deduplicated: int
    events_dropped: int
    stale_events_rejected: int
    out_of_order_events: int
    changes_detected: int
    anomalies_detected: int
    avg_latency_ms: float
    last_event_at: Optional[str] = None
