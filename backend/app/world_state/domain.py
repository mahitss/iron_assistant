"""Domain models, enums, and operational contracts for Task 98:
KAIRO Autonomous World-State Reconstruction, State Estimation, Reality Synchronization & Drift Reconciliation Engine.

Enforces:
- OBSERVATION != TRUTH
- EXPECTED STATE != ACTUAL STATE
- MISSING DATA != NO CHANGE
- STALE != CURRENT
- DRIFT != CAUSE
- CORRELATION != CAUSATION
- SIMULATION != REALITY
- EXECUTION != VERIFIED STATE
- UNKNOWN MUST REMAIN UNKNOWN
- CONFLICT MUST REMAIN VISIBLE
- HISTORICAL STATE MUST REMAIN RECONSTRUCTABLE
- UNATTRIBUTED CHANGE MUST NOT RECEIVE A FABRICATED ACTOR
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
import hashlib
import json
from typing import Any, Dict, List, Optional, Union
import uuid

from pydantic import BaseModel, ConfigDict, Field, model_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


def generate_uuid(prefix: str = "st") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


# =====================================================================
# ENUMS
# =====================================================================

class WorldScope(str, Enum):
    """Supported operational scope boundaries (Phase 1)."""
    SYSTEM = "SYSTEM"
    PROJECT = "PROJECT"
    WORKFLOW = "WORKFLOW"
    TASK = "TASK"
    SERVICE = "SERVICE"
    CAPABILITY = "CAPABILITY"
    RESOURCE = "RESOURCE"
    ENVIRONMENT = "ENVIRONMENT"
    USER_SESSION = "USER_SESSION"
    AGENT_SWARM = "AGENT_SWARM"
    INFRASTRUCTURE = "INFRASTRUCTURE"


class StateStatus(str, Enum):
    """Explicit state lifecycle statuses (Phase 2)."""
    UNKNOWN = "UNKNOWN"
    PROVISIONAL = "PROVISIONAL"
    OBSERVED = "OBSERVED"
    RECONSTRUCTING = "RECONSTRUCTING"
    CURRENT = "CURRENT"
    STALE = "STALE"
    DRIFTED = "DRIFTED"
    CONFLICTED = "CONFLICTED"
    DEGRADED = "DEGRADED"
    UNCERTAIN = "UNCERTAIN"
    INVALIDATED = "INVALIDATED"
    SUPERSEDED = "SUPERSEDED"
    ARCHIVED = "ARCHIVED"


class EpistemicCertainty(str, Enum):
    """Epistemic classification of state information."""
    OBSERVED = "OBSERVED"      # Direct measurement/heartbeat
    DERIVED = "DERIVED"        # Logically computed through valid inference
    INFERRED = "INFERRED"      # Probabilistic or heuristic attribution
    PREDICTED = "PREDICTED"    # Forecasted or simulated counterfactual
    CERTAIN = "CERTAIN"        # Unambiguous verifiable certainty
    PROBABLE = "PROBABLE"      # High likelihood
    UNCERTAIN = "UNCERTAIN"    # Low confidence
    UNKNOWN = "UNKNOWN"        # Missing or unobserved


class CertaintyTier(str, Enum):
    """Epistemic certainty tiers (consistent with Task 97)."""
    KNOWN = "KNOWN"
    LIKELY = "LIKELY"
    POSSIBLE = "POSSIBLE"
    UNCERTAIN = "UNCERTAIN"
    CONTRADICTED = "CONTRADICTED"
    UNKNOWN = "UNKNOWN"


class FreshnessState(str, Enum):
    """Freshness policy classification (Phase 35)."""
    FRESH = "FRESH"
    AGING = "AGING"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class DriftType(str, Enum):
    """Taxonomy of detected reality drift (Phase 10)."""
    VALUE_DIVERGENCE = "VALUE_DIVERGENCE"
    STATUS_MISMATCH = "STATUS_MISMATCH"
    CONFIGURATION_DRIFT = "CONFIGURATION_DRIFT"
    STATE_DRIFT = "STATE_DRIFT"
    DEPENDENCY_DRIFT = "DEPENDENCY_DRIFT"
    CAPABILITY_DRIFT = "CAPABILITY_DRIFT"
    RESOURCE_DRIFT = "RESOURCE_DRIFT"
    POLICY_DRIFT = "POLICY_DRIFT"
    BEHAVIORAL_DRIFT = "BEHAVIORAL_DRIFT"
    PERFORMANCE_DRIFT = "PERFORMANCE_DRIFT"
    SCHEMA_DRIFT = "SCHEMA_DRIFT"
    ENVIRONMENT_DRIFT = "ENVIRONMENT_DRIFT"
    MODEL_DRIFT = "MODEL_DRIFT"


class DriftSeverity(str, Enum):
    """Criticality of observed drift (Phase 11)."""
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


class DriftClassification(str, Enum):
    """Operational classification of detected drift (Phase 12)."""
    EXPECTED_CHANGE = "EXPECTED_CHANGE"
    BENIGN_DRIFT = "BENIGN_DRIFT"
    ACTIONABLE_DRIFT = "ACTIONABLE_DRIFT"
    UNATTRIBUTED_CHANGE = "UNATTRIBUTED_CHANGE"
    EXTERNAL_MODIFICATION = "EXTERNAL_MODIFICATION"
    UNKNOWN_DRIFT = "UNKNOWN_DRIFT"
    CRITICAL_DRIFT = "CRITICAL_DRIFT"


class DriftStatus(str, Enum):
    """Lifecycle status of a drift record."""
    DETECTED = "DETECTED"
    INVESTIGATING = "INVESTIGATING"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RECONCILED = "RECONCILED"
    RESOLVED = "RESOLVED"
    IGNORED = "IGNORED"


class ExpectationMatchOutcome(str, Enum):
    """Result of comparing expected vs actual state (Phase 19)."""
    MATCHED = "MATCHED"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    MISMATCH = "MISMATCH"
    DRIFT_DETECTED = "DRIFT_DETECTED"
    UNKNOWN = "UNKNOWN"
    NOT_VERIFIABLE = "NOT_VERIFIABLE"


class CausalEvidenceStatus(str, Enum):
    """Causal linkage between drift and system causes (Phase 13)."""
    CAUSAL_EVIDENCE_AVAILABLE = "CAUSAL_EVIDENCE_AVAILABLE"
    CORRELATION_ONLY = "CORRELATION_ONLY"
    NO_EVIDENCE = "NO_EVIDENCE"
    UNKNOWN = "UNKNOWN"


class StateDiffType(str, Enum):
    """Structural differential between two state snapshots (Phase 32)."""
    ADDED = "ADDED"
    REMOVED = "REMOVED"
    CHANGED = "CHANGED"
    UNCHANGED = "UNCHANGED"
    UNKNOWN = "UNKNOWN"


# =====================================================================
# CORE SCHEMAS & MODELS
# =====================================================================

class StateObservation(BaseModel):
    """Strongly typed observation from an authorized telemetry or probe source (Phase 3)."""
    model_config = ConfigDict(extra="ignore")

    observation_id: str = Field(default_factory=lambda: generate_uuid("obs"))
    source: str = "system"              # tool, telemetry, agent, network, etc.
    source_id: str = ""
    entity_id: str = ""
    observed_value: Any = None
    observed_at: datetime = Field(default_factory=utc_now)
    received_at: datetime = Field(default_factory=utc_now)
    provenance: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    certainty: CertaintyTier = CertaintyTier.KNOWN
    freshness: FreshnessState = FreshnessState.FRESH
    sensitivity: str = "INTERNAL"
    validation_status: str = "RAW"       # RAW, VERIFIED, REJECTED, UNVERIFIED
    correlation_id: Optional[str] = None
    trace_id: Optional[str] = None
    scope: WorldScope = WorldScope.SYSTEM

    @model_validator(mode="before")
    @classmethod
    def _normalize_obs(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "canonical_id" in data and not data.get("entity_id"):
                data["entity_id"] = data["canonical_id"]
            if "attributes" in data and "observed_value" not in data:
                data["observed_value"] = data["attributes"]
            # Map EpistemicCertainty enum to CertaintyTier if passed
            if "certainty" in data and hasattr(data["certainty"], "value"):
                val = data["certainty"].value
                if val in CertaintyTier.__members__:
                    data["certainty"] = CertaintyTier(val)
                elif val == "CERTAIN":
                    data["certainty"] = CertaintyTier.KNOWN
                elif val == "PROBABLE":
                    data["certainty"] = CertaintyTier.LIKELY
                elif val == "UNCERTAIN":
                    data["certainty"] = CertaintyTier.UNCERTAIN
                else:
                    data["certainty"] = CertaintyTier.KNOWN
        return data

    @property
    def canonical_id(self) -> str:
        return self.entity_id

    @property
    def attributes(self) -> Any:
        return self.observed_value


class ExpectedState(BaseModel):
    """Declared expectation from decisions, action postconditions, or contracts (Phase 4)."""
    model_config = ConfigDict(extra="ignore")

    expected_id: str = Field(default_factory=lambda: generate_uuid("exp"))
    entity_id: str = ""
    expected_value: Any = None
    expected_by: str = "ActionTransaction"
    source_type: str = "ACTION_POSTCONDITION"  # ACTION_POSTCONDITION, DECISION_ASSUMPTION, CAPABILITY_CONTRACT, etc.
    source_id: str = ""
    tolerance: Any = 0.0
    valid_from: datetime = Field(default_factory=utc_now)
    valid_until: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utc_now)
    scope: WorldScope = WorldScope.SYSTEM
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _normalize_exp(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "canonical_id" in data and not data.get("entity_id"):
                data["entity_id"] = data["canonical_id"]
            if "expected_attributes" in data and "expected_value" not in data:
                data["expected_value"] = data["expected_attributes"]
            if "purpose" in data and "metadata" not in data:
                data["metadata"] = {"purpose": data["purpose"]}
        return data

    @property
    def canonical_id(self) -> str:
        return self.entity_id

    @property
    def expected_attributes(self) -> Any:
        return self.expected_value


class StateAttributeRecord(BaseModel):
    """Versioned attribute record for an actual state entity (Phase 5)."""
    model_config = ConfigDict(extra="ignore")

    attribute_name: str
    current_value: Any
    previous_value: Optional[Any] = None
    confidence: float = 1.0
    certainty: CertaintyTier = CertaintyTier.KNOWN
    observed_at: datetime = Field(default_factory=utc_now)
    valid_from: datetime = Field(default_factory=utc_now)
    valid_until: Optional[datetime] = None
    source: str = "system"
    evidence: list[str] = Field(default_factory=list)
    source_count: int = 1

    @property
    def value(self) -> Any:
        return self.current_value


class WorldStateEntity(BaseModel):
    """Reconstructed actual state entity with confidence, freshness, and attribution (Phase 5)."""
    model_config = ConfigDict(extra="ignore")

    entity_id: str = ""
    canonical_name: str = ""
    canonical_key: str = ""
    scope: WorldScope = WorldScope.SYSTEM
    status: StateStatus = StateStatus.CURRENT
    epistemic_certainty: EpistemicCertainty = EpistemicCertainty.OBSERVED
    confidence: float = 1.0
    observation_confidence: float = 1.0
    verification_confidence: float = 1.0
    freshness: FreshnessState = FreshnessState.FRESH
    last_observed_at: datetime = Field(default_factory=utc_now)
    next_expected_observation: Optional[datetime] = None
    expected_update_interval_seconds: float = 300.0
    attributes: dict[str, StateAttributeRecord] = Field(default_factory=dict)
    active_drift_ids: list[str] = Field(default_factory=list)
    active_conflict_ids: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    version: int = 1
    sensitivity: str = "INTERNAL"
    user_id: str = "default_user"
    project_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _normalize_entity(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "canonical_id" in data and not data.get("entity_id"):
                data["entity_id"] = data["canonical_id"]
            if not data.get("canonical_name"):
                data["canonical_name"] = data.get("entity_id", "")
        return data

    @property
    def canonical_id(self) -> str:
        return self.entity_id

    def is_stale(self, now: Optional[datetime] = None) -> bool:
        current_time = now or utc_now()
        elapsed = (current_time - self.last_observed_at).total_seconds()
        return elapsed > self.expected_update_interval_seconds


class StateDriftRecord(BaseModel):
    """Structured record of detected divergence between expected and actual state (Phase 10)."""
    model_config = ConfigDict(extra="ignore")

    drift_id: str = Field(default_factory=lambda: generate_uuid("drift"))
    entity_id: str
    attribute_name: str = "state"
    scope: WorldScope = WorldScope.SYSTEM
    drift_type: DriftType = DriftType.STATE_DRIFT
    severity: DriftSeverity = DriftSeverity.MEDIUM
    classification: DriftClassification = DriftClassification.ACTIONABLE_DRIFT
    status: DriftStatus = DriftStatus.DETECTED
    expected_value: Any = None
    actual_value: Any = None
    deviation_magnitude: float = 0.0
    evidence: list[str] = Field(default_factory=list)
    confidence: float = 1.0
    detected_at: datetime = Field(default_factory=utc_now)
    resolved_at: Optional[datetime] = None
    causal_status: CausalEvidenceStatus = CausalEvidenceStatus.UNKNOWN
    attributed_source_type: Optional[str] = None  # ACTION_TRANSACTION, DECISION, UNATTRIBUTED_CHANGE, etc.
    attributed_source_id: Optional[str] = None
    revalidation_candidate_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def canonical_id(self) -> str:
        return self.entity_id

    @property
    def observed_value(self) -> Any:
        return self.actual_value

    @property
    def attributed_action_id(self) -> Optional[str]:
        return self.attributed_source_id if self.attributed_source_type == "ACTION_TRANSACTION" else None

    @property
    def attributed_decision_id(self) -> Optional[str]:
        return self.attributed_source_id if self.attributed_source_type == "DECISION" else None


class StateConflictRecord(BaseModel):
    """Explicitly preserved dialectic disagreement between observation sources (Phase 16)."""
    model_config = ConfigDict(extra="ignore")

    conflict_id: str = Field(default_factory=lambda: generate_uuid("conf"))
    entity_id: str
    attribute_name: str
    observations: list[StateObservation] = Field(default_factory=list)
    resolution_state: str = "UNRESOLVED"        # UNRESOLVED, RESOLVED, SUPERSEDED
    resolved_value: Optional[Any] = None
    resolution_reason: Optional[str] = None
    detected_at: datetime = Field(default_factory=utc_now)
    resolved_at: Optional[datetime] = None

    @property
    def canonical_id(self) -> str:
        return self.entity_id

    @property
    def status(self) -> str:
        return self.resolution_state

    @property
    def sources(self) -> list[str]:
        return [o.source_id or o.source for o in self.observations]


class StateInvariantViolation(BaseModel):
    """Formal violation of domain invariants (Phase 34)."""
    model_config = ConfigDict(extra="ignore")

    violation_id: str = Field(default_factory=lambda: generate_uuid("inv"))
    invariant_name: str
    entity_id: str
    scope: WorldScope = WorldScope.SYSTEM
    severity: DriftSeverity = DriftSeverity.HIGH
    description: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    detected_at: datetime = Field(default_factory=utc_now)
    remediation_suggestion: Optional[str] = None

    @property
    def canonical_id(self) -> str:
        return self.entity_id


class RevalidationCandidate(BaseModel):
    """Bounded, prioritized revalidation candidate (Phase 21)."""
    model_config = ConfigDict(extra="ignore")

    candidate_id: str = Field(default_factory=lambda: generate_uuid("reval"))
    entity_id: str
    target_type: str = "CAPABILITY"      # CAPABILITY, WORKFLOW, DECISION, ACTION
    reason: str
    drift_id: Optional[str] = None
    priority: str = "NORMAL"                    # CRITICAL, HIGH, NORMAL, LOW
    created_at: datetime = Field(default_factory=utc_now)
    status: str = "PENDING"                     # PENDING, DISPATCHED, COMPLETED, DISMISSED


class WorldStateSnapshot(BaseModel):
    """Immutable, versioned snapshot of world state (Phase 1, 31)."""
    model_config = ConfigDict(extra="ignore")

    snapshot_id: str = Field(default_factory=lambda: generate_uuid("snap"))
    state_id: str = ""
    scope: WorldScope = WorldScope.SYSTEM
    timestamp: datetime = Field(default_factory=utc_now)
    created_at: Optional[datetime] = None
    valid_from: datetime = Field(default_factory=utc_now)
    valid_until: Optional[datetime] = None
    version: int = 1
    parent_state_id: Optional[str] = None
    source_observations: list[str] = Field(default_factory=list)
    entities: dict[str, Any] = Field(default_factory=dict)
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    expected_state_references: list[str] = Field(default_factory=list)
    entity_count: int = 0
    confidence: float = 1.0
    certainty: CertaintyTier = CertaintyTier.KNOWN
    freshness: FreshnessState = FreshnessState.FRESH
    drift_status: str = "NORMAL"
    reconciliation_status: str = "SYNCHRONIZED"
    provenance: dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[str] = None
    trace_id: Optional[str] = None
    state_hash: str = ""
    integrity_hash: str = ""
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _normalize_snapshot(cls, data: Any) -> Any:
        if isinstance(data, dict):
            sid = data.get("snapshot_id") or data.get("state_id")
            if sid:
                data["snapshot_id"] = sid
                data["state_id"] = sid
            if "created_at" in data and not data.get("timestamp"):
                data["timestamp"] = data["created_at"]
            elif "timestamp" in data and not data.get("created_at"):
                data["created_at"] = data["timestamp"]
            if "integrity_hash" in data and not data.get("state_hash"):
                data["state_hash"] = data["integrity_hash"]
            elif "state_hash" in data and not data.get("integrity_hash"):
                data["integrity_hash"] = data["state_hash"]
            if "entities" in data and isinstance(data["entities"], dict) and not data.get("entity_count"):
                data["entity_count"] = len(data["entities"])
        return data

    @property
    def canonical_id(self) -> str:
        return self.snapshot_id


class WorldStateDiff(BaseModel):
    """Structured differential between two state snapshots (Phase 32)."""
    model_config = ConfigDict(extra="ignore")

    diff_id: str = Field(default_factory=lambda: generate_uuid("diff"))
    from_state_id: str
    to_state_id: str
    added_entities: list[str] = Field(default_factory=list)
    removed_entities: list[str] = Field(default_factory=list)
    changed_entities: dict[str, dict[str, Any]] = Field(default_factory=dict)
    unchanged_entities: list[str] = Field(default_factory=list)
    detected_drift_ids: list[str] = Field(default_factory=list)
    computed_at: datetime = Field(default_factory=utc_now)

    @property
    def modified_entities(self) -> dict[str, dict[str, Any]]:
        return self.changed_entities


# =====================================================================
# REQUEST & RESPONSE SCHEMAS
# =====================================================================

class IngestObservationRequest(BaseModel):
    source: str = "telemetry"
    source_id: str = ""
    entity_id: str
    observed_value: Any
    observed_at: Optional[datetime] = None
    provenance: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0
    certainty: CertaintyTier = CertaintyTier.KNOWN
    sensitivity: str = "INTERNAL"
    scope: WorldScope = WorldScope.SYSTEM
    correlation_id: Optional[str] = None


class DeclareExpectedStateRequest(BaseModel):
    entity_id: str
    expected_value: Any
    expected_by: str = "ActionTransaction"
    source_type: str = "ACTION_POSTCONDITION"
    source_id: str = ""
    tolerance: float = 0.0
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    scope: WorldScope = WorldScope.SYSTEM
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReconcileStateRequest(BaseModel):
    scope: WorldScope = WorldScope.SYSTEM
    entity_ids: Optional[list[str]] = None
    as_of: Optional[datetime] = None
    user_id: str = "default_user"


class AnalyzeDriftRequest(BaseModel):
    scope: WorldScope = WorldScope.SYSTEM
    entity_id: Optional[str] = None
    user_id: str = "default_user"


class HistoricalReconstructionRequest(BaseModel):
    timestamp: datetime
    scope: WorldScope = WorldScope.SYSTEM
    entity_ids: Optional[list[str]] = None
    user_id: str = "default_user"
