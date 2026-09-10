"""Pydantic v2 schemas and domain models for Kairo Incident Response & Recovery Autonomy Engine (Task 61)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class IncidentStatus(str, Enum):
    DETECTED = "DETECTED"
    TRIAGING = "TRIAGING"
    INVESTIGATING = "INVESTIGATING"
    DIAGNOSING = "DIAGNOSING"
    AWAITING_DECISION = "AWAITING_DECISION"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    MITIGATING = "MITIGATING"
    RECOVERING = "RECOVERING"
    VERIFYING = "VERIFYING"
    RESOLVED = "RESOLVED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"
    PAUSED = "PAUSED"
    CLOSED = "CLOSED"


class IncidentSeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IncidentUrgency(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    IMMEDIATE = "IMMEDIATE"


class HypothesisStatus(str, Enum):
    PROPOSED = "PROPOSED"
    SUPPORTED = "SUPPORTED"
    WEAKENED = "WEAKENED"
    REJECTED = "REJECTED"
    VERIFIED = "VERIFIED"
    UNKNOWN = "UNKNOWN"


class ActionState(str, Enum):
    PROPOSED = "PROPOSED"
    AUTHORIZED = "AUTHORIZED"
    APPROVED = "APPROVED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    VERIFYING = "VERIFYING"
    VERIFIED = "VERIFIED"


class RecoveryState(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    PARTIAL = "PARTIAL"
    RECOVERED = "RECOVERED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class AutomationLevel(str, Enum):
    OBSERVE_ONLY = "OBSERVE_ONLY"
    RECOMMEND = "RECOMMEND"
    AUTO_WITH_APPROVAL = "AUTO_WITH_APPROVAL"
    AUTHORIZED_AUTOMATION = "AUTHORIZED_AUTOMATION"
    EMERGENCY_AUTOMATION = "EMERGENCY_AUTOMATION"


class ResponderRole(str, Enum):
    INCIDENT_COMMANDER = "INCIDENT_COMMANDER"
    INVESTIGATOR = "INVESTIGATOR"
    OPERATOR = "OPERATOR"
    COMMUNICATOR = "COMMUNICATOR"
    VERIFIER = "VERIFIER"


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    evidence_id: str = Field(default_factory=lambda: f"evd_{uuid.uuid4().hex[:8]}")
    source: str
    timestamp: datetime = Field(default_factory=_now_utc)
    trust_level: str = "TRUSTED_SYSTEM"
    relevance_score: float = 1.0
    is_verified: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class CausalHypothesisItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    hypothesis_id: str = Field(default_factory=lambda: f"hyp_{uuid.uuid4().hex[:8]}")
    candidate_cause: str
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    confidence: float = 0.5
    evidence_supporting: list[EvidenceItem] = Field(default_factory=list)
    evidence_contradictory: list[EvidenceItem] = Field(default_factory=list)
    recommended_diagnostics: list[str] = Field(default_factory=list)


class DiagnosticTask(BaseModel):
    model_config = ConfigDict(extra="ignore")

    task_id: str = Field(default_factory=lambda: f"diag_{uuid.uuid4().hex[:8]}")
    name: str
    target_resource: str
    purpose: str
    is_read_only: bool = True
    estimated_risk: str = "LOW"
    voi_score: float = 0.8  # Value of Information score


class InvestigationPlan(BaseModel):
    model_config = ConfigDict(extra="ignore")

    investigation_id: str = Field(default_factory=lambda: f"inv_{uuid.uuid4().hex[:8]}")
    incident_id: str
    tasks: list[DiagnosticTask] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)
    completed_task_ids: list[str] = Field(default_factory=list)


class ResponseOptionItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    option_id: str = Field(default_factory=lambda: f"opt_{uuid.uuid4().hex[:8]}")
    title: str
    strategy_type: str  # contain, rollback, failover, restart, scale, isolate
    description: str
    expected_benefit: str
    estimated_risk: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    is_reversible: bool = True
    requires_approval: bool = True
    required_capabilities: list[str] = Field(default_factory=list)
    is_capability_available: bool = True
    composite_score: float = 0.85


class RecoveryCheckpoint(BaseModel):
    model_config = ConfigDict(extra="ignore")

    checkpoint_id: str = Field(default_factory=lambda: f"chk_{uuid.uuid4().hex[:8]}")
    step_id: str
    verification_criteria: str
    is_passed: bool = False
    revalidation_state: dict[str, Any] = Field(default_factory=dict)
    verified_at: datetime | None = None


class RecoveryStep(BaseModel):
    model_config = ConfigDict(extra="ignore")

    step_id: str = Field(default_factory=lambda: f"step_{uuid.uuid4().hex[:8]}")
    title: str
    action_type: str
    target_resource: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    requires_checkpoint: bool = True
    timeout_seconds: int = 120
    is_completed: bool = False


class RecoveryPlan(BaseModel):
    model_config = ConfigDict(extra="ignore")

    plan_id: str = Field(default_factory=lambda: f"rec_{uuid.uuid4().hex[:8]}")
    incident_id: str
    strategy: str
    status: RecoveryState = RecoveryState.NOT_STARTED
    steps: list[RecoveryStep] = Field(default_factory=list)
    current_step_index: int = 0
    checkpoints: list[RecoveryCheckpoint] = Field(default_factory=list)
    rollback_strategy: dict[str, Any] = Field(default_factory=dict)
    version: int = 1


class IncidentActionItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    action_id: str = Field(default_factory=lambda: f"act_{uuid.uuid4().hex[:8]}")
    incident_id: str
    action_type: str
    title: str
    status: ActionState = ActionState.PROPOSED
    is_reversible: bool = True
    is_idempotent: bool = True
    requires_approval: bool = False
    executor_role: ResponderRole = ResponderRole.OPERATOR
    parameters: dict[str, Any] = Field(default_factory=dict)
    verification_spec: dict[str, Any] = Field(default_factory=dict)
    execution_result: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now_utc)
    completed_at: datetime | None = None


class PostmortemReport(BaseModel):
    model_config = ConfigDict(extra="ignore")

    postmortem_id: str = Field(default_factory=lambda: f"pm_{uuid.uuid4().hex[:8]}")
    incident_id: str
    summary: str
    impact_summary: str
    root_cause: str = "ROOT_CAUSE_UNKNOWN"
    contributing_factors: list[str] = Field(default_factory=list)
    what_worked: list[str] = Field(default_factory=list)
    what_failed: list[str] = Field(default_factory=list)
    action_items: list[dict[str, Any]] = Field(default_factory=list)
    lessons_learned: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now_utc)


class IncidentResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    response_id: str = Field(default_factory=lambda: f"ir_{uuid.uuid4().hex[:10]}")
    incident_id: str = Field(default_factory=lambda: f"inc_{uuid.uuid4().hex[:8]}")
    situation_id: str | None = None
    title: str
    description: str = ""
    status: IncidentStatus = IncidentStatus.DETECTED
    severity: IncidentSeverity = IncidentSeverity.MEDIUM
    urgency: IncidentUrgency = IncidentUrgency.NORMAL
    environment: str = "development"
    confidence: float = 1.0

    affected_resources: list[str] = Field(default_factory=list)
    affected_services: list[str] = Field(default_factory=list)
    affected_plans: list[str] = Field(default_factory=list)
    affected_goals: list[str] = Field(default_factory=list)

    responders: list[dict[str, Any]] = Field(default_factory=list)
    incident_commander: str | None = None

    hypotheses: list[CausalHypothesisItem] = Field(default_factory=list)
    investigation: InvestigationPlan | None = None
    response_options: list[ResponseOptionItem] = Field(default_factory=list)
    selected_option_id: str | None = None
    actions: list[IncidentActionItem] = Field(default_factory=list)
    recovery_plan: RecoveryPlan | None = None
    postmortem: PostmortemReport | None = None

    automation_level: AutomationLevel = AutomationLevel.RECOMMEND
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)
    resolved_at: datetime | None = None


# API Requests
class CreateIncidentFromSituationRequest(BaseModel):
    situation_id: str
    title: str | None = None
    description: str = ""
    environment: str = "development"
    actor: str = "SYSTEM"
    affected_resources: list[str] = Field(default_factory=list)
    affected_services: list[str] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)


class TriageIncidentRequest(BaseModel):
    override_severity: IncidentSeverity | None = None
    override_urgency: IncidentUrgency | None = None
    severity: IncidentSeverity | None = None
    urgency: IncidentUrgency | None = None
    actor: str = "SYSTEM_USER"
    responder: str | None = None
    reason: str = "Automated triage evaluation"
    triage_notes: str = ""


class AddEvidenceRequest(BaseModel):
    hypothesis_id: str
    is_supporting: bool = True
    supports: bool | None = None
    source: str
    summary: str = ""
    details: dict[str, Any] = Field(default_factory=dict)
    raw_data: dict[str, Any] = Field(default_factory=dict)
    trust: float = 1.0
    relevance: float = 1.0
    is_verified: bool = True


class ExecuteMitigationRequest(BaseModel):
    option_id: str
    actor: str = "SYSTEM_USER"
    bypass_approval: bool = False


class ApproveActionRequest(BaseModel):
    action_id: str
    approver: str
    reason: str = "Approved by authorized incident commander"
    approval_notes: str = ""


class VerifyRecoveryRequest(BaseModel):
    checkpoint_id: str
    verifier: str
    is_verified: bool = True
    observed_metrics: dict[str, Any] = Field(default_factory=dict)
    verification_evidence: dict[str, Any] = Field(default_factory=dict)
    notes: str = ""


class ResolveIncidentRequest(BaseModel):
    actor: str = "SYSTEM_USER"
    resolver: str | None = None
    is_verified: bool = True
    verification_evidence: dict[str, Any] = Field(default_factory=dict)
    resolution_summary: str = ""
    resolution_notes: str = ""
    verification_notes: str = ""
    preventive_actions: list[str] = Field(default_factory=list)
