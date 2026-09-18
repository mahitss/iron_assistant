"""Domain models, typed enums, and operational structures for Task 111:
KAIRO Autonomous Temporal Intelligence, Event History, Change Reconstruction,
State Transitions, Temporal Queries & "What Changed?" Engine.

Core Invariants:
- EVENT != STATE != CAUSE
- TEMPORAL ORDER != CAUSATION
- CORRELATION != CAUSATION
- OBSERVATION != TRUTH
- MEMORY != CURRENT STATE
- BELIEF != FACT
- FORECAST != OUTCOME
- SIMULATION != REALITY
- EXPECTED STATE != ACTUAL STATE
- ABSENCE OF EVENT != PROOF OF ABSENCE
- LATE EVENT != CURRENT EVENT
- EVENT TIME != INGESTION TIME
- HISTORICAL STATE != CURRENT STATE
- RECONSTRUCTION != CERTAINTY
- UNATTRIBUTED CHANGE MUST REMAIN UNATTRIBUTED
- NEVER FABRICATE CAUSAL EXPLANATIONS
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import Enum
import hashlib
import json
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> datetime:
    """Authoritative UTC now timestamp."""
    return datetime.now(UTC)


def gen_temporal_id(prefix: str = "temp") -> str:
    """Generates unique prefixed identifier."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ============================================================================
# 1. Enums
# ============================================================================

class TemporalClockType(str, Enum):
    """Explicit multi-clock timestamp classification (Section 5)."""
    EVENT_TIME = "EVENT_TIME"          # When the occurrence happened in the logical/physical world
    OBSERVED_TIME = "OBSERVED_TIME"    # When a sensor/observer detected the occurrence
    INGESTED_TIME = "INGESTED_TIME"    # When the event arrived at storage/event bus
    PROCESSED_TIME = "PROCESSED_TIME"  # When normalizers/engines processed the event
    EFFECTIVE_TIME = "EFFECTIVE_TIME"  # When state delta became legally/operationally active


class ChangeCategory(str, Enum):
    """Semantic classification of state mutations (Section 14)."""
    ADDED = "ADDED"
    REMOVED = "REMOVED"
    MODIFIED = "MODIFIED"
    REORDERED = "REORDERED"
    SUPERSEDED = "SUPERSEDED"
    EXPIRED = "EXPIRED"
    STALE = "STALE"
    RECOVERED = "RECOVERED"
    DEGRADED = "DEGRADED"
    UNKNOWN = "UNKNOWN"


class AttributionCertainty(str, Enum):
    """Strict attribution classification without causal fabrication (Section 15)."""
    DIRECTLY_ATTRIBUTED = "DIRECTLY_ATTRIBUTED"  # Deterministic proof (e.g. action execution transaction ID)
    STRONGLY_LINKED = "STRONGLY_LINKED"          # High confidence causal evidence & strict temporal precedence
    POSSIBLY_LINKED = "POSSIBLY_LINKED"          # Plausible causal hypothesis with temporal precedence
    CORRELATED = "CORRELATED"                    # Statistical or temporal proximity without verified causation
    UNATTRIBUTED = "UNATTRIBUTED"                # Explicitly unknown actor/cause (must not be fabricated)
    CONTRADICTED = "CONTRADICTED"                # Proposed cause occurred after effect
    UNKNOWN = "UNKNOWN"


class ExpectationStatus(str, Enum):
    """Expectation vs observation discrepancy state (Section 16)."""
    EXPECTED = "EXPECTED"          # Forecasted / postcondition expectation
    OBSERVED = "OBSERVED"          # Telemetry / observation occurred
    VERIFIED = "VERIFIED"          # Confirmed matching expectation
    UNVERIFIED = "UNVERIFIED"      # Observed but postconditions not yet verified
    CONTRADICTED = "CONTRADICTED"  # Observed state differs from expected
    UNKNOWN = "UNKNOWN"


class TemporalAnomalyType(str, Enum):
    """Temporal and timing anomalies (Section 17)."""
    IMPOSSIBLE_ORDERING = "IMPOSSIBLE_ORDERING"          # Child event timestamped before parent
    NEGATIVE_DURATION = "NEGATIVE_DURATION"              # End time earlier than start time
    OVERLAPPING_INCOMPATIBLE = "OVERLAPPING_INCOMPATIBLE"# Mutually exclusive states at same time
    STATE_REGRESSION = "STATE_REGRESSION"                # Unexplained rollback to prior state
    RAPID_OSCILLATION = "RAPID_OSCILLATION"              # High-frequency flip-flopping
    LONG_SILENCE = "LONG_SILENCE"                        # Expected periodic heartbeat missing
    MISSING_EXPECTED_TRANSITION = "MISSING_TRANSITION"   # State jumped past required intermediate phase
    EVENT_BURST = "EVENT_BURST"                          # Pathological ingestion spike
    CLOCK_SKEW = "CLOCK_SKEW"                            # Timestamps skewed relative to monotonic reference
    STALE_EVENT = "STALE_EVENT"                          # Arrived long after temporal relevance window
    FUTURE_DATED_EVENT = "FUTURE_DATED_EVENT"            # Timestamped significantly ahead of wall-clock
    IMPOSSIBLE_CAUSATION = "IMPOSSIBLE_CAUSATION"        # Cause occurred after effect
    DUPLICATE_EVENT = "DUPLICATE_EVENT"                  # Identical event received repeatedly
    CONFLICTING_TIMESTAMPS = "CONFLICTING_TIMESTAMPS"    # Discrepant clocks across sources


class CorrectionType(str, Enum):
    """Immutable correction classification (Section 21)."""
    CORRECTED = "CORRECTED"
    SUPERSEDED = "SUPERSEDED"
    RETRACTED = "RETRACTED"
    RECLASSIFIED = "RECLASSIFIED"


class TemporalIntervalType(str, Enum):
    """Nature of interval boundaries (Section 10)."""
    POINT = "POINT"            # Instantaneous event (duration = 0)
    OPEN = "OPEN"              # Start known, ongoing/unbounded end
    CLOSED = "CLOSED"          # Distinct start and end
    ESTIMATED = "ESTIMATED"    # Reconstructed bounds with confidence interval
    UNCERTAIN = "UNCERTAIN"    # Bounded only by outer bounds


class TemporalEntityType(str, Enum):
    """Entities whose state transitions over time (Section 8)."""
    MISSION = "MISSION"
    GOAL = "GOAL"
    SITUATION = "SITUATION"
    DECISION = "DECISION"
    ACTION = "ACTION"
    WORKFLOW = "WORKFLOW"
    CAPABILITY = "CAPABILITY"
    RESOURCE = "RESOURCE"
    AGENT = "AGENT"
    WORLD_STATE = "WORLD_STATE"
    SELF_MODEL = "SELF_MODEL"
    MEMORY = "MEMORY"
    BELIEF = "BELIEF"
    CONTEXT = "CONTEXT"
    SERVICE = "SERVICE"
    RUNTIME = "RUNTIME"
    SYSTEM = "SYSTEM"


# ============================================================================
# 2. Domain Data Models
# ============================================================================

class MultiClockTimestamps(BaseModel):
    """Preserves distinct clocks across ingestion and reality (Section 5)."""
    model_config = ConfigDict(extra="ignore")

    event_time: datetime = Field(default_factory=utc_now, description="When occurrence took place")
    observed_time: Optional[datetime] = Field(default=None, description="When observed by sensor/agent")
    ingested_time: datetime = Field(default_factory=utc_now, description="When stored in Kairo event bus")
    processed_time: Optional[datetime] = Field(default=None, description="When processed by temporal engine")
    effective_time: datetime = Field(default_factory=utc_now, description="When state change took effect")
    valid_from: datetime = Field(default_factory=utc_now, description="Start of validity interval")
    valid_until: Optional[datetime] = Field(default=None, description="End of validity interval (None if open)")

    @property
    def ingestion_lag_seconds(self) -> float:
        """Computes lag between event occurrence and ingestion."""
        return max(0.0, (self.ingested_time - self.event_time).total_seconds())

    @property
    def observation_lag_seconds(self) -> float:
        """Computes lag between event occurrence and observation."""
        if self.observed_time:
            return max(0.0, (self.observed_time - self.event_time).total_seconds())
        return 0.0


class TemporalEvent(BaseModel):
    """Normalized temporal projection of a system or domain event (Section 7)."""
    model_config = ConfigDict(extra="ignore")

    temporal_event_id: str = Field(default_factory=lambda: gen_temporal_id("tevt"))
    canonical_event_id: str = Field(description="Underlying Event.event_id in events table")
    event_type: str
    event_version: str = "v1"
    category: str = "SYSTEM"  # e.g. ACTION, MISSION, WORLD_STATE, DECISION, BELIEF
    clocks: MultiClockTimestamps = Field(default_factory=MultiClockTimestamps)
    sequence_number: int = 0
    monotonic_timestamp: float = 0.0
    source_subsystem: str
    source_entity_id: Optional[str] = None
    actor_id: Optional[str] = None
    correlation_id: str
    causation_id: Optional[str] = None
    parent_event_id: Optional[str] = None
    payload_summary: str = ""
    payload_diff: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0
    is_untrusted: bool = False
    is_late: bool = False
    is_out_of_order: bool = False
    is_duplicate: bool = False
    correction_state: Optional[CorrectionType] = None
    superseded_by: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TemporalInterval(BaseModel):
    """Typed temporal interval with certainty indicators (Section 10)."""
    model_config = ConfigDict(extra="ignore")

    interval_id: str = Field(default_factory=lambda: gen_temporal_id("tint"))
    interval_type: TemporalIntervalType = TemporalIntervalType.CLOSED
    start_time: datetime
    end_time: Optional[datetime] = None
    estimated_duration_seconds: Optional[float] = None
    confidence: float = 1.0
    description: str = ""

    @property
    def is_open(self) -> bool:
        return self.end_time is None

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.end_time:
            return max(0.0, (self.end_time - self.start_time).total_seconds())
        return self.estimated_duration_seconds


class StateTransition(BaseModel):
    """Explicit state transition between consecutive states (Section 9)."""
    model_config = ConfigDict(extra="ignore")

    transition_id: str = Field(default_factory=lambda: gen_temporal_id("trans"))
    entity_id: str
    entity_type: TemporalEntityType
    previous_state: str
    next_state: str
    trigger_event_id: Optional[str] = None
    actor: Optional[str] = None
    timestamp: datetime = Field(default_factory=utc_now)
    expectation_status: ExpectationStatus = ExpectationStatus.OBSERVED
    evidence: List[str] = Field(default_factory=list)
    confidence: float = 1.0
    attribution: AttributionCertainty = AttributionCertainty.UNATTRIBUTED
    attributed_cause: Optional[str] = None
    correlation_id: Optional[str] = None
    scope: str = "DEFAULT"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TemporalEntity(BaseModel):
    """Entity whose state evolution is tracked over time (Section 8)."""
    model_config = ConfigDict(extra="ignore")

    entity_id: str
    entity_type: TemporalEntityType
    scope: str = "DEFAULT"
    current_version: int = 1
    current_state: str = "INITIAL"
    valid_from: datetime = Field(default_factory=utc_now)
    last_transition_time: datetime = Field(default_factory=utc_now)
    state_attributes: Dict[str, Any] = Field(default_factory=dict)
    provenance_source: str = "system"
    confidence: float = 1.0


class ChangeRecord(BaseModel):
    """Granular change record for a field, attribute, or sub-entity (Section 14)."""
    model_config = ConfigDict(extra="ignore")

    change_id: str = Field(default_factory=lambda: gen_temporal_id("chg"))
    entity_id: str
    entity_type: TemporalEntityType
    attribute_path: str
    previous_value: Any = None
    new_value: Any = None
    category: ChangeCategory = ChangeCategory.MODIFIED
    timestamp: datetime = Field(default_factory=utc_now)
    attribution: AttributionCertainty = AttributionCertainty.UNATTRIBUTED
    attributed_action_id: Optional[str] = None
    attributed_actor: Optional[str] = None
    causal_evidence: Optional[str] = None
    confidence: float = 1.0
    impact_level: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL


class ChangeSet(BaseModel):
    """Collection of changes between two snapshots or temporal boundaries (Section 14)."""
    model_config = ConfigDict(extra="ignore")

    changeset_id: str = Field(default_factory=lambda: gen_temporal_id("chgset"))
    from_reference: str  # timestamp ISO, checkpoint ID, or snapshot ID
    to_reference: str
    from_time: datetime
    to_time: datetime
    changes: List[ChangeRecord] = Field(default_factory=list)
    added_count: int = 0
    removed_count: int = 0
    modified_count: int = 0
    degraded_count: int = 0
    recovered_count: int = 0
    unattributed_count: int = 0
    created_at: datetime = Field(default_factory=utc_now)

    def summarize(self) -> Dict[str, int]:
        return {
            "total_changes": len(self.changes),
            "added": self.added_count,
            "removed": self.removed_count,
            "modified": self.modified_count,
            "degraded": self.degraded_count,
            "recovered": self.recovered_count,
            "unattributed": self.unattributed_count,
        }


class ChangeSummary(BaseModel):
    """Compact summary of changes formatted for downstream consumption (Section 23)."""
    model_config = ConfigDict(extra="ignore")

    summary_id: str = Field(default_factory=lambda: gen_temporal_id("csum"))
    scope: str
    time_window_seconds: float
    headline: str
    total_changes: int
    critical_changes: List[str] = Field(default_factory=list)
    unresolved_discrepancies: List[str] = Field(default_factory=list)
    has_degraded_capabilities: bool = False
    has_unattributed_changes: bool = False
    generated_at: datetime = Field(default_factory=utc_now)


class ExpectedVsActual(BaseModel):
    """Explicit pairing of forecast/expected postcondition with actual observation (Section 16)."""
    model_config = ConfigDict(extra="ignore")

    evaluation_id: str = Field(default_factory=lambda: gen_temporal_id("eva"))
    subject_entity_id: str
    expected_state: str
    observed_state: str
    expected_by_time: datetime
    observed_time: datetime
    status: ExpectationStatus = ExpectationStatus.UNVERIFIED
    discrepancy_explanation: Optional[str] = None
    expected_source: str = "forecast"  # forecast, action_postcondition, mission_milestone
    observed_source: str = "observation"
    confidence: float = 1.0


class TemporalAnomaly(BaseModel):
    """Detected timing or temporal integrity anomaly (Section 17)."""
    model_config = ConfigDict(extra="ignore")

    anomaly_id: str = Field(default_factory=lambda: gen_temporal_id("anom"))
    anomaly_type: TemporalAnomalyType
    entity_id: Optional[str] = None
    event_ids: List[str] = Field(default_factory=list)
    detected_at: datetime = Field(default_factory=utc_now)
    severity: str = "WARNING"  # INFO, WARNING, ERROR, CRITICAL
    explanation: str
    remediation_suggested: Optional[str] = None
    is_adversarial_suspect: bool = False


class TemporalGap(BaseModel):
    """Detected period of missing telemetry or observations (Section 18)."""
    model_config = ConfigDict(extra="ignore")

    gap_id: str = Field(default_factory=lambda: gen_temporal_id("tgap"))
    subsystem: str
    entity_id: Optional[str] = None
    gap_start: datetime
    gap_end: datetime
    duration_seconds: float
    reason: str = "Missing telemetry window"
    is_offline_period: bool = False
    confidence_impact: float = 0.5  # Drops confidence of state during gap


class TemporalWatermark(BaseModel):
    """High-water marks tracking ingestion and reconciliation lag (Section 20)."""
    model_config = ConfigDict(extra="ignore")

    watermark_id: str = Field(default_factory=lambda: gen_temporal_id("wtmk"))
    subsystem: str
    source_watermark: datetime = Field(default_factory=utc_now)
    ingestion_watermark: datetime = Field(default_factory=utc_now)
    processing_watermark: datetime = Field(default_factory=utc_now)
    reconciliation_watermark: datetime = Field(default_factory=utc_now)
    last_updated: datetime = Field(default_factory=utc_now)

    @property
    def processing_lag_seconds(self) -> float:
        return max(0.0, (self.ingestion_watermark - self.processing_watermark).total_seconds())

    @property
    def reconciliation_lag_seconds(self) -> float:
        return max(0.0, (self.ingestion_watermark - self.reconciliation_watermark).total_seconds())


class TemporalCheckpoint(BaseModel):
    """Named stable point in time for fast diffing and rollback reconstruction (Section 4)."""
    model_config = ConfigDict(extra="ignore")

    checkpoint_id: str = Field(default_factory=lambda: gen_temporal_id("chkp"))
    name: str
    checkpoint_type: str = "MANUAL"  # MANUAL, MISSION_MILESTONE, CONTROL_CYCLE, RECOVERY
    timestamp: datetime = Field(default_factory=utc_now)
    active_entity_states: Dict[str, str] = Field(default_factory=dict)
    state_snapshot_hash: str = ""
    creator: str = "system"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TimelineSegment(BaseModel):
    """Chronologically bounded slice of a timeline (Section 11)."""
    model_config = ConfigDict(extra="ignore")

    segment_id: str = Field(default_factory=lambda: gen_temporal_id("tseg"))
    start_time: datetime
    end_time: datetime
    events: List[TemporalEvent] = Field(default_factory=list)
    transitions: List[StateTransition] = Field(default_factory=list)
    anomalies: List[TemporalAnomaly] = Field(default_factory=list)
    gaps: List[TemporalGap] = Field(default_factory=list)


class Timeline(BaseModel):
    """Complete, queryable timeline of events and transitions (Section 11)."""
    model_config = ConfigDict(extra="ignore")

    timeline_id: str = Field(default_factory=lambda: gen_temporal_id("time"))
    entity_id: Optional[str] = None
    entity_type: Optional[TemporalEntityType] = None
    scope: str = "DEFAULT"
    start_time: datetime
    end_time: datetime
    total_events: int = 0
    total_transitions: int = 0
    segments: List[TimelineSegment] = Field(default_factory=list)
    watermark: Optional[TemporalWatermark] = None
    created_at: datetime = Field(default_factory=utc_now)


class TemporalQuery(BaseModel):
    """Typed temporal query specification (Section 12)."""
    model_config = ConfigDict(extra="ignore")

    entity_id: Optional[str] = None
    entity_type: Optional[TemporalEntityType] = None
    from_time: Optional[datetime] = None
    to_time: Optional[datetime] = None
    scope: str = "DEFAULT"
    category: Optional[str] = None
    attribution: Optional[AttributionCertainty] = None
    limit: int = Field(default=100, le=1000)
    include_events: bool = True
    include_transitions: bool = True
    include_anomalies: bool = True
    include_gaps: bool = True


class TemporalQueryResult(BaseModel):
    """Results returned from a temporal query (Section 12)."""
    model_config = ConfigDict(extra="ignore")

    query_id: str = Field(default_factory=lambda: gen_temporal_id("tqry"))
    executed_at: datetime = Field(default_factory=utc_now)
    from_time: datetime
    to_time: datetime
    events: List[TemporalEvent] = Field(default_factory=list)
    transitions: List[StateTransition] = Field(default_factory=list)
    anomalies: List[TemporalAnomaly] = Field(default_factory=list)
    gaps: List[TemporalGap] = Field(default_factory=list)
    total_count: int = 0
    is_truncated: bool = False
