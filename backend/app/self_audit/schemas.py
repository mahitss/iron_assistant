"""Pydantic v2 domain schemas and data contracts for Kairo Metacognitive Control & Autonomous Self-Audit Engine (Task 67)."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# =====================================================================
# Domain Enums
# =====================================================================


class CapabilityState(str, enum.Enum):
    """Execution status of a system capability (Spec 4).

    Invariant: Capability presence != authorization.
    """

    CAPABILITY_AVAILABLE = "CAPABILITY_AVAILABLE"
    CAPABILITY_DEGRADED = "CAPABILITY_DEGRADED"
    CAPABILITY_UNAVAILABLE = "CAPABILITY_UNAVAILABLE"
    CAPABILITY_UNKNOWN = "CAPABILITY_UNKNOWN"


class SelfKnowledgeType(str, enum.Enum):
    """Epistemic classification of self-knowledge (Spec 6).

    Invariant: Never collapse INFERRED/PREDICTED/ASSUMED into KNOWN/OBSERVED.
    """

    KNOWN = "KNOWN"
    OBSERVED = "OBSERVED"
    INFERRED = "INFERRED"
    ESTIMATED = "ESTIMATED"
    PREDICTED = "PREDICTED"
    ASSUMED = "ASSUMED"
    UNKNOWN = "UNKNOWN"


class BeliefStatus(str, enum.Enum):
    """Lifecycle state of an internal belief (Spec 7, 8)."""

    ACTIVE = "ACTIVE"
    QUESTIONED = "QUESTIONED"
    CONTRADICTED = "CONTRADICTED"
    STALE = "STALE"
    RETIRED = "RETIRED"


class AuditSourceType(str, enum.Enum):
    """Origin of audit evaluation (Spec 20).

    Invariant: SELF_AUDIT != EXTERNAL_AUDIT.
    """

    SELF_AUDIT = "SELF_AUDIT"
    PEER_REVIEW = "PEER_REVIEW"
    SYSTEM_VERIFICATION = "SYSTEM_VERIFICATION"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    EXTERNAL_AUDIT = "EXTERNAL_AUDIT"


class ConfidenceCalibrationState(str, enum.Enum):
    """Calibration alignment of self-reported confidence against empirical outcomes (Spec 24-26)."""

    OVERCONFIDENT = "OVERCONFIDENT"
    UNDERCONFIDENT = "UNDERCONFIDENT"
    WELL_CALIBRATED = "WELL_CALIBRATED"
    UNKNOWN = "UNKNOWN"


class ErrorCategory(str, enum.Enum):
    """Standard error taxonomy across 12 operational dimensions (Spec 27)."""

    KNOWLEDGE_ERROR = "KNOWLEDGE_ERROR"
    REASONING_ERROR = "REASONING_ERROR"
    PLANNING_ERROR = "PLANNING_ERROR"
    PREDICTION_ERROR = "PREDICTION_ERROR"
    EXECUTION_ERROR = "EXECUTION_ERROR"
    TOOL_ERROR = "TOOL_ERROR"
    RESOURCE_ERROR = "RESOURCE_ERROR"
    COMMUNICATION_ERROR = "COMMUNICATION_ERROR"
    VERIFICATION_ERROR = "VERIFICATION_ERROR"
    CALIBRATION_ERROR = "CALIBRATION_ERROR"
    GOAL_ERROR = "GOAL_ERROR"
    COORDINATION_ERROR = "COORDINATION_ERROR"


class ErrorSeverity(str, enum.Enum):
    """Severity classification of self-audit findings (Spec 28)."""

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FindingState(str, enum.Enum):
    """State machine of an audit finding (Spec 51)."""

    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    INVESTIGATING = "INVESTIGATING"
    MITIGATED = "MITIGATED"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"
    UNVERIFIED = "UNVERIFIED"


class AuditType(str, enum.Enum):
    """Contextual triggers and scope for self-audit (Spec 46, 47)."""

    CONTINUOUS = "CONTINUOUS"
    PERIODIC = "PERIODIC"
    EVENT_TRIGGERED = "EVENT_TRIGGERED"
    MISSION_COMPLETE = "MISSION_COMPLETE"
    INCIDENT_POSTMORTEM = "INCIDENT_POSTMORTEM"
    DECISION_REVIEW = "DECISION_REVIEW"
    SECURITY_REVIEW = "SECURITY_REVIEW"
    PERFORMANCE_REVIEW = "PERFORMANCE_REVIEW"
    MODEL_REVIEW = "MODEL_REVIEW"


class AuditDepth(str, enum.Enum):
    """Resource-bounded depth of analysis (Spec 48, 49)."""

    LIGHT = "LIGHT"
    STANDARD = "STANDARD"
    DEEP = "DEEP"
    FORENSIC = "FORENSIC"


class MetacognitiveState(str, enum.Enum):
    """Top-level self-awareness assessment (Spec 92)."""

    CONFIDENT = "CONFIDENT"
    UNCERTAIN = "UNCERTAIN"
    CONFLICTED = "CONFLICTED"
    BLOCKED = "BLOCKED"
    DEGRADED = "DEGRADED"
    SELF_AUDIT_REQUIRED = "SELF_AUDIT_REQUIRED"
    EXTERNAL_REVIEW_REQUIRED = "EXTERNAL_REVIEW_REQUIRED"


# =====================================================================
# Domain Data Models
# =====================================================================


class Belief(BaseModel):
    """Structured representation of internal system belief (Spec 7, 8).

    Invariant: BELIEF != FACT.
    """

    model_config = ConfigDict(extra="ignore")

    belief_id: str = Field(default_factory=lambda: f"blf_{uuid.uuid4().hex[:10]}")
    subject: str
    claim: str
    basis: str
    evidence: list[str] = Field(default_factory=list)
    confidence: float = 0.5  # 0.0 to 1.0
    scope: dict[str, Any] = Field(default_factory=dict)
    status: BeliefStatus = BeliefStatus.ACTIVE
    provenance: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=_now_utc)
    tenant_id: str = "default"


class BeliefRevision(BaseModel):
    """Historical non-destructive revision record when beliefs change (Spec 8)."""

    model_config = ConfigDict(extra="ignore")

    revision_id: str = Field(default_factory=lambda: f"rev_{uuid.uuid4().hex[:8]}")
    belief_id: str
    previous_claim: str
    new_claim: str
    new_evidence: list[str] = Field(default_factory=list)
    reason: str
    previous_confidence: float = 0.5
    new_confidence: float = 0.5
    new_status: BeliefStatus = BeliefStatus.ACTIVE
    timestamp: datetime = Field(default_factory=_now_utc)


class AuditFinding(BaseModel):
    """Concrete discovery or deficiency identified by self-audit (Spec 50, 51)."""

    model_config = ConfigDict(extra="ignore")

    finding_id: str = Field(default_factory=lambda: f"fnd_{uuid.uuid4().hex[:8]}")
    audit_id: str
    category: ErrorCategory = ErrorCategory.REASONING_ERROR
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    description: str
    evidence: list[str] = Field(default_factory=list)
    impact: str = ""
    confidence: float = 0.7
    recommendation: str = ""
    status: FindingState = FindingState.OPEN
    created_at: datetime = Field(default_factory=_now_utc)
    resolved_at: datetime | None = None


class SelfAuditRecord(BaseModel):
    """Complete record of a self-audit execution (Spec 45).

    Invariant: SELF-AUDIT != TRUTH.
    """

    model_config = ConfigDict(extra="ignore")

    audit_id: str = Field(default_factory=lambda: f"aud_{uuid.uuid4().hex[:10]}")
    scope: str = "system"
    subject: str
    audit_type: AuditType = AuditType.PERIODIC
    depth: AuditDepth = AuditDepth.STANDARD
    checks_performed: list[str] = Field(default_factory=list)
    findings: list[AuditFinding] = Field(default_factory=list)
    severity: ErrorSeverity = ErrorSeverity.INFO
    evidence: list[str] = Field(default_factory=list)
    confidence: float = 0.8
    recommendations: list[str] = Field(default_factory=list)
    verification: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    version: int = 1
    timestamp: datetime = Field(default_factory=_now_utc)
    tenant_id: str = "default"


class SelfModel(BaseModel):
    """Verifiable operational model of Kairo's internal state and limits (Spec 3, 4, 5)."""

    model_config = ConfigDict(extra="ignore")

    self_model_id: str = Field(default_factory=lambda: f"sm_{uuid.uuid4().hex[:8]}")
    version: int = 1
    capabilities: dict[str, CapabilityState] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    active_goals: list[str] = Field(default_factory=list)
    active_missions: list[str] = Field(default_factory=list)
    known_dependencies: list[str] = Field(default_factory=list)
    current_state: MetacognitiveState = MetacognitiveState.CONFIDENT
    uncertainties: list[str] = Field(default_factory=list)
    known_failure_modes: list[str] = Field(default_factory=list)
    performance_metrics: dict[str, float] = Field(default_factory=dict)
    calibration: ConfidenceCalibrationState = ConfidenceCalibrationState.WELL_CALIBRATED
    resource_state: dict[str, Any] = Field(default_factory=dict)
    tool_state: dict[str, Any] = Field(default_factory=dict)
    model_state: dict[str, Any] = Field(default_factory=dict)
    risk_state: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=_now_utc)
    tenant_id: str = "default"


class BehaviorBaseline(BaseModel):
    """Operational baseline metrics against which drift is detected (Spec 33, 34)."""

    model_config = ConfigDict(extra="ignore")

    baseline_id: str = Field(default_factory=lambda: f"bsl_{uuid.uuid4().hex[:8]}")
    metric_name: str
    normal_mean: float
    normal_std: float = 1.0
    drift_threshold_pct: float = 30.0
    current_value: float = 0.0
    is_drifting: bool = False
    drift_reason: str = ""
    updated_at: datetime = Field(default_factory=_now_utc)


class PredictionCalibrationRecord(BaseModel):
    """Historical record evaluating predicted outcomes vs actual results (Spec 15, 24)."""

    model_config = ConfigDict(extra="ignore")

    prediction_id: str = Field(default_factory=lambda: f"prd_{uuid.uuid4().hex[:8]}")
    subject: str
    prediction: str
    confidence: float
    expected_outcome: str
    actual_outcome: str | None = None
    outcome_verified: bool = False
    brier_score: float | None = None
    calibration_state: ConfidenceCalibrationState = ConfidenceCalibrationState.UNKNOWN
    timestamp: datetime = Field(default_factory=_now_utc)


class ErrorCluster(BaseModel):
    """Grouped recurring operational errors indicating systematic failure (Spec 29, 31)."""

    model_config = ConfigDict(extra="ignore")

    cluster_id: str = Field(default_factory=lambda: f"cls_{uuid.uuid4().hex[:8]}")
    error_category: ErrorCategory
    pattern_name: str
    recurring_count: int = 1
    root_cause_hypothesis: str
    is_verified: bool = False
    sample_error_ids: list[str] = Field(default_factory=list)
    first_detected_at: datetime = Field(default_factory=_now_utc)
    last_detected_at: datetime = Field(default_factory=_now_utc)


class SelfAuditOverview(BaseModel):
    """Aggregated dashboard telemetry for the Self-Audit Control Center (Spec 59)."""

    model_config = ConfigDict(extra="ignore")

    metacognitive_state: MetacognitiveState = MetacognitiveState.CONFIDENT
    calibration_state: ConfidenceCalibrationState = ConfidenceCalibrationState.WELL_CALIBRATED
    total_audits: int = 0
    open_findings_count: int = 0
    critical_findings_count: int = 0
    active_beliefs_count: int = 0
    active_drifts_count: int = 0
    recurring_error_clusters: int = 0
    average_brier_score: float = 0.0
    audit_chain_intact: bool = True
    recent_audits: list[SelfAuditRecord] = Field(default_factory=list)


# =====================================================================
# Request / Response DTOs
# =====================================================================


class SelfAuditCreateRequest(BaseModel):
    """Payload to trigger a self-audit evaluation."""

    subject: str
    scope: str = "system"
    audit_type: AuditType = AuditType.PERIODIC
    depth: AuditDepth = AuditDepth.STANDARD
    evidence: list[str] | None = None
    tenant_id: str = "default"


class BeliefCreateRequest(BaseModel):
    """Payload to register an internal belief."""

    subject: str
    claim: str
    basis: str
    evidence: list[str] | None = None
    confidence: float = 0.7
    scope: dict[str, Any] | None = None
    tenant_id: str = "default"


class BeliefReviseRequest(BaseModel):
    """Payload to revise an internal belief with new evidence."""

    new_claim: str
    new_evidence: list[str]
    reason: str
    new_confidence: float = 0.6
    new_status: BeliefStatus = BeliefStatus.ACTIVE
    tenant_id: str = "default"


class AuditCycleRequest(BaseModel):
    """Payload to run a full 11-step metacognitive audit cycle."""

    subject: str
    observed_actions: list[str]
    reported_confidence: float = 0.8
    observed_outcomes: dict[str, Any] | None = None
    depth: AuditDepth = AuditDepth.STANDARD
    is_adversarial: bool = False
    tenant_id: str = "default"
