"""
Domain models, enums, and data structures for Kairo Autonomous Hypothesis Management,
Competing Explanations, Evidence Update, Falsification, and Uncertainty Resolution Engine (Task 115).

Hard Invariants:
- HYPOTHESIS != BELIEF
- HYPOTHESIS != FACT
- HYPOTHESIS != TRUTH
- HYPOTHESIS != DECISION
- HYPOTHESIS != AUTHORIZATION
- HYPOTHESIS != ACTION
- EVIDENCE != TRUTH
- CORRELATION != CAUSATION
- TEMPORAL ORDER != CAUSATION
- SIMULATION != REALITY
- COUNTERFACTUAL != HISTORY
- AGENT CLAIM != INDEPENDENT EVIDENCE
- ABSENCE OF EVIDENCE != EVIDENCE OF ABSENCE
- UNKNOWN / UNEXPLAINED must always remain representable to prevent forced convergence.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class HypothesisStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    DRAFT = "DRAFT"
    UNDER_INVESTIGATION = "UNDER_INVESTIGATION"
    EVIDENCE_PENDING = "EVIDENCE_PENDING"
    PROVISIONAL = "PROVISIONAL"
    SUPPORTED = "SUPPORTED"
    STRONGLY_SUPPORTED = "STRONGLY_SUPPORTED"
    CONTESTED = "CONTESTED"
    WEAKENED = "WEAKENED"
    FALSIFIED = "FALSIFIED"
    REJECTED = "REJECTED"
    VERIFIED = "VERIFIED"
    STALE = "STALE"
    SUPERSEDED = "SUPERSEDED"
    MERGED = "MERGED"
    SPLIT = "SPLIT"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"


class HypothesisProvenance(str, Enum):
    GENERATED = "GENERATED"
    OBSERVED = "OBSERVED"
    USER_PROVIDED = "USER_PROVIDED"
    AGENT_PROVIDED = "AGENT_PROVIDED"
    MODEL_DERIVED = "MODEL_DERIVED"
    HISTORICAL = "HISTORICAL"
    SIMULATED = "SIMULATED"


class EvidenceType(str, Enum):
    OBSERVATION = "OBSERVATION"
    TELEMETRY = "TELEMETRY"
    STATE_TRANSITION = "STATE_TRANSITION"
    EVENT = "EVENT"
    EXPERIMENT = "EXPERIMENT"
    INTERVENTION = "INTERVENTION"
    SIMULATION = "SIMULATION"
    COUNTERFACTUAL = "COUNTERFACTUAL"
    USER_REPORT = "USER_REPORT"
    AGENT_REPORT = "AGENT_REPORT"
    MEMORY = "MEMORY"
    BELIEF = "BELIEF"
    GRAPH = "GRAPH"
    FORECAST = "FORECAST"
    HISTORICAL_PATTERN = "HISTORICAL_PATTERN"
    DERIVED_SIGNAL = "DERIVED_SIGNAL"


class EvidenceIndependence(str, Enum):
    INDEPENDENT = "INDEPENDENT"
    DERIVED = "DERIVED"
    DUPLICATE = "DUPLICATE"
    CORRELATED = "CORRELATED"
    UNKNOWN = "UNKNOWN"


class SupportVerdict(str, Enum):
    SUPPORTS = "SUPPORTS"
    WEAKLY_SUPPORTS = "WEAKLY_SUPPORTS"
    NEUTRAL = "NEUTRAL"
    WEAKLY_CONTRADICTS = "WEAKLY_CONTRADICTS"
    CONTRADICTS = "CONTRADICTS"
    FALSIFIES = "FALSIFIES"
    UNKNOWN = "UNKNOWN"


class HypothesisRelationshipType(str, Enum):
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    DEPENDS_ON = "DEPENDS_ON"
    ALTERNATIVE_TO = "ALTERNATIVE_TO"
    SPECIALIZES = "SPECIALIZES"
    GENERALIZES = "GENERALIZES"
    CAUSES = "CAUSES"
    CONTRIBUTES_TO = "CONTRIBUTES_TO"
    EXPLAINS = "EXPLAINS"
    REQUIRES = "REQUIRES"
    CONFOUNDING_CANDIDATE = "CONFOUNDING_CANDIDATE"
    UNKNOWN_RELATION = "UNKNOWN_RELATION"


class HypothesisEventType(str, Enum):
    HYPOTHESIS_CREATED = "HYPOTHESIS_CREATED"
    HYPOTHESIS_UPDATED = "HYPOTHESIS_UPDATED"
    HYPOTHESIS_SUPPORTED = "HYPOTHESIS_SUPPORTED"
    HYPOTHESIS_WEAKENED = "HYPOTHESIS_WEAKENED"
    HYPOTHESIS_CONTESTED = "HYPOTHESIS_CONTESTED"
    HYPOTHESIS_FALSIFIED = "HYPOTHESIS_FALSIFIED"
    HYPOTHESIS_VERIFIED = "HYPOTHESIS_VERIFIED"
    HYPOTHESIS_STALE = "HYPOTHESIS_STALE"
    HYPOTHESIS_SUPERSEDED = "HYPOTHESIS_SUPERSEDED"
    HYPOTHESIS_MERGED = "HYPOTHESIS_MERGED"
    HYPOTHESIS_SPLIT = "HYPOTHESIS_SPLIT"
    HYPOTHESIS_CONFLICT_DETECTED = "HYPOTHESIS_CONFLICT_DETECTED"
    HYPOTHESIS_EVIDENCE_ATTACHED = "HYPOTHESIS_EVIDENCE_ATTACHED"
    HYPOTHESIS_EVIDENCE_CONTRADICTED = "HYPOTHESIS_EVIDENCE_CONTRADICTED"
    HYPOTHESIS_PREDICTION_CREATED = "HYPOTHESIS_PREDICTION_CREATED"
    HYPOTHESIS_PREDICTION_FAILED = "HYPOTHESIS_PREDICTION_FAILED"
    HYPOTHESIS_DISCRIMINATOR_CREATED = "HYPOTHESIS_DISCRIMINATOR_CREATED"
    HYPOTHESIS_INFORMATION_GAP_CREATED = "HYPOTHESIS_INFORMATION_GAP_CREATED"
    HYPOTHESIS_OBSERVATION_REQUESTED = "HYPOTHESIS_OBSERVATION_REQUESTED"
    HYPOTHESIS_EXPERIMENT_PROPOSED = "HYPOTHESIS_EXPERIMENT_PROPOSED"
    HYPOTHESIS_SNAPSHOT_CREATED = "HYPOTHESIS_SNAPSHOT_CREATED"
    HYPOTHESIS_VERIFICATION_STARTED = "HYPOTHESIS_VERIFICATION_STARTED"
    HYPOTHESIS_VERIFICATION_COMPLETED = "HYPOTHESIS_VERIFICATION_COMPLETED"
    HYPOTHESIS_UNKNOWN = "HYPOTHESIS_UNKNOWN"


@dataclass
class HypothesisClaim:
    """Core assertion made by the hypothesis."""
    claim_id: str = field(default_factory=lambda: f"claim_{uuid.uuid4().hex[:8]}")
    subject: str = ""
    predicate: str = ""
    object_value: Any = None
    qualifier: str = ""
    target_metric: Optional[str] = None
    expected_direction: Optional[str] = None  # e.g., "increase", "decrease", "anomaly"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "subject": self.subject,
            "predicate": self.predicate,
            "object_value": self.object_value,
            "qualifier": self.qualifier,
            "target_metric": self.target_metric,
            "expected_direction": self.expected_direction,
        }


@dataclass
class HypothesisScope:
    """Bounded operational scope of a hypothesis."""
    entity_ids: List[str] = field(default_factory=list)
    subsystems: List[str] = field(default_factory=list)
    time_window_start: Optional[datetime] = None
    time_window_end: Optional[datetime] = None
    environment: str = "production"
    context_keys: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_ids": self.entity_ids,
            "subsystems": self.subsystems,
            "time_window_start": self.time_window_start.isoformat() if self.time_window_start else None,
            "time_window_end": self.time_window_end.isoformat() if self.time_window_end else None,
            "environment": self.environment,
            "context_keys": self.context_keys,
        }


@dataclass
class HypothesisFalsificationCondition:
    """Explicit, testable, bounded criterion that would disprove this hypothesis."""
    condition_id: str = field(default_factory=lambda: f"fals_{uuid.uuid4().hex[:8]}")
    description: str = ""
    required_observations: List[str] = field(default_factory=list)
    metric_thresholds: Dict[str, Any] = field(default_factory=dict)
    contradiction_signals: List[str] = field(default_factory=list)
    is_falsified: bool = False
    falsification_evidence_ids: List[str] = field(default_factory=list)
    falsification_reasoning: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "condition_id": self.condition_id,
            "description": self.description,
            "required_observations": self.required_observations,
            "metric_thresholds": self.metric_thresholds,
            "contradiction_signals": self.contradiction_signals,
            "is_falsified": self.is_falsified,
            "falsification_evidence_ids": self.falsification_evidence_ids,
            "falsification_reasoning": self.falsification_reasoning,
        }


@dataclass
class HypothesisPrediction:
    """Testable prediction made by the hypothesis."""
    prediction_id: str = field(default_factory=lambda: f"pred_{uuid.uuid4().hex[:8]}")
    predicted_event: str = ""
    predicted_state: Dict[str, Any] = field(default_factory=dict)
    expected_metric: Optional[str] = None
    expected_value_range: Optional[tuple[float, float]] = None
    expected_timing_seconds: float = 0.0
    validity_window_start: Optional[datetime] = None
    validity_window_end: Optional[datetime] = None
    uncertainty_range: float = 0.1
    source_model: str = "causal_model"
    observed_outcome: Optional[Any] = None
    outcome_status: str = "PENDING"  # PENDING, CONFIRMED, FAILED, EXPIRED
    failure_notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "predicted_event": self.predicted_event,
            "predicted_state": self.predicted_state,
            "expected_metric": self.expected_metric,
            "expected_value_range": list(self.expected_value_range) if self.expected_value_range else None,
            "expected_timing_seconds": self.expected_timing_seconds,
            "validity_window_start": self.validity_window_start.isoformat() if self.validity_window_start else None,
            "validity_window_end": self.validity_window_end.isoformat() if self.validity_window_end else None,
            "uncertainty_range": self.uncertainty_range,
            "source_model": self.source_model,
            "observed_outcome": self.observed_outcome,
            "outcome_status": self.outcome_status,
            "failure_notes": self.failure_notes,
        }


@dataclass
class HypothesisEvidenceItem:
    """Immutable evidence item attached to hypothesis reasoning."""
    evidence_id: str = field(default_factory=lambda: f"evi_{uuid.uuid4().hex[:8]}")
    source: str = ""
    source_type: str = "system"
    source_agent_id: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    observation_time: Optional[datetime] = None
    scope: Optional[HypothesisScope] = None
    provenance: str = ""
    parent_evidence_ids: List[str] = field(default_factory=list)
    independence: EvidenceIndependence = EvidenceIndependence.INDEPENDENT
    freshness_seconds: float = 0.0
    reliability_score: float = 1.0
    direct_status: bool = True  # True if direct measurement, False if inferred/derived
    evidence_type: EvidenceType = EvidenceType.OBSERVATION
    payload: Dict[str, Any] = field(default_factory=dict)
    is_simulation: bool = False
    is_counterfactual: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "source": self.source,
            "source_type": self.source_type,
            "source_agent_id": self.source_agent_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "observation_time": self.observation_time.isoformat() if self.observation_time else None,
            "scope": self.scope.to_dict() if self.scope else None,
            "provenance": self.provenance,
            "parent_evidence_ids": self.parent_evidence_ids,
            "independence": self.independence.value,
            "freshness_seconds": self.freshness_seconds,
            "reliability_score": self.reliability_score,
            "direct_status": self.direct_status,
            "evidence_type": self.evidence_type.value,
            "payload": self.payload,
            "is_simulation": self.is_simulation,
            "is_counterfactual": self.is_counterfactual,
        }


@dataclass
class HypothesisEvidenceAssessment:
    """Assessment of a single piece of evidence against a hypothesis."""
    assessment_id: str = field(default_factory=lambda: f"assess_{uuid.uuid4().hex[:8]}")
    hypothesis_id: str = ""
    evidence_id: str = ""
    verdict: SupportVerdict = SupportVerdict.NEUTRAL
    reasoning_basis: str = ""
    confidence: float = 0.5
    temporal_fit: float = 0.5  # 0.0 to 1.0
    causal_fit: float = 0.5    # 0.0 to 1.0
    independence: EvidenceIndependence = EvidenceIndependence.INDEPENDENT
    model_version: str = "v1.0"
    assessed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assessment_id": self.assessment_id,
            "hypothesis_id": self.hypothesis_id,
            "evidence_id": self.evidence_id,
            "verdict": self.verdict.value,
            "reasoning_basis": self.reasoning_basis,
            "confidence": self.confidence,
            "temporal_fit": self.temporal_fit,
            "causal_fit": self.causal_fit,
            "independence": self.independence.value,
            "model_version": self.model_version,
            "assessed_at": self.assessed_at.isoformat() if self.assessed_at else None,
        }


@dataclass
class HypothesisConfidenceProfile:
    """Multi-dimensional confidence breakdown for a hypothesis.

    Hard Invariant: Never collapsed into an opaque single scalar without exposing dimensions.
    """
    evidence_strength: float = 0.0          # 0.0 to 1.0 based on quality/weight of supporting evidence
    evidence_independence: float = 0.0      # Ratio of independent vs derived/duplicate evidence
    temporal_consistency: float = 0.5      # Temporal order & lag alignment
    mechanism_plausibility: float = 0.5    # Known physical or architectural pathway exists
    causal_support: float = 0.5            # Alignment with causal model
    predictive_success: float = 0.5        # Ratio of predictions confirmed vs failed
    counterfactual_support: float = 0.0    # Supported by what-if intervention simulation
    contradiction_score: float = 0.0       # Weight of contradicting observations (higher = more contested)
    source_reliability: float = 0.8        # Average reliability of reporting sources
    completeness: float = 0.3              # Coverage of required falsification/observational fields
    uncertainty: float = 0.7               # Residual epistemic and aleatoric uncertainty
    historical_consistency: float = 0.5    # Alignment with past incidents in memory

    def overall_viability_score(self) -> float:
        """Heuristic viability score computed transparently from dimensions."""
        # Penalty for high contradiction and high uncertainty
        base = (
            0.25 * self.evidence_strength
            + 0.20 * self.evidence_independence
            + 0.15 * self.temporal_consistency
            + 0.15 * self.causal_support
            + 0.15 * self.predictive_success
            + 0.10 * self.mechanism_plausibility
        )
        penalty = 0.5 * self.contradiction_score + 0.2 * self.uncertainty
        return max(0.0, min(1.0, base - penalty))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_strength": round(self.evidence_strength, 3),
            "evidence_independence": round(self.evidence_independence, 3),
            "temporal_consistency": round(self.temporal_consistency, 3),
            "mechanism_plausibility": round(self.mechanism_plausibility, 3),
            "causal_support": round(self.causal_support, 3),
            "predictive_success": round(self.predictive_success, 3),
            "counterfactual_support": round(self.counterfactual_support, 3),
            "contradiction_score": round(self.contradiction_score, 3),
            "source_reliability": round(self.source_reliability, 3),
            "completeness": round(self.completeness, 3),
            "uncertainty": round(self.uncertainty, 3),
            "historical_consistency": round(self.historical_consistency, 3),
            "viability_score": round(self.overall_viability_score(), 3),
        }


@dataclass
class HypothesisDiscriminator:
    """An observation or measurement that distinguishes between competing hypotheses."""
    discriminator_id: str = field(default_factory=lambda: f"disc_{uuid.uuid4().hex[:8]}")
    target_metric_or_signal: str = ""
    hypothesis_predictions: Dict[str, str] = field(default_factory=dict)  # hyp_id -> expected outcome
    observation_channel: str = ""
    information_value: float = 0.5   # From Task 114 VoI
    estimated_cost: float = 0.1
    latency_seconds: float = 1.0
    risk_level: str = "LOW"
    rationale: str = ""
    task_114_observation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "discriminator_id": self.discriminator_id,
            "target_metric_or_signal": self.target_metric_or_signal,
            "hypothesis_predictions": self.hypothesis_predictions,
            "observation_channel": self.observation_channel,
            "information_value": self.information_value,
            "estimated_cost": self.estimated_cost,
            "latency_seconds": self.latency_seconds,
            "risk_level": self.risk_level,
            "rationale": self.rationale,
            "task_114_observation_id": self.task_114_observation_id,
        }


@dataclass
class HypothesisRelationship:
    """Explicit relationship between two hypotheses."""
    relationship_id: str = field(default_factory=lambda: f"rel_{uuid.uuid4().hex[:8]}")
    source_hypothesis_id: str = ""
    target_hypothesis_id: str = ""
    relationship_type: HypothesisRelationshipType = HypothesisRelationshipType.ALTERNATIVE_TO
    rationale: str = ""
    confidence: float = 0.7

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relationship_id": self.relationship_id,
            "source_hypothesis_id": self.source_hypothesis_id,
            "target_hypothesis_id": self.target_hypothesis_id,
            "relationship_type": self.relationship_type.value,
            "rationale": self.rationale,
            "confidence": self.confidence,
        }


@dataclass
class HypothesisConflict:
    """Documented conflict between competing hypotheses or evidence."""
    conflict_id: str = field(default_factory=lambda: f"conf_{uuid.uuid4().hex[:8]}")
    hypothesis_a_id: str = ""
    hypothesis_b_id: str = ""
    conflicting_property: str = ""
    evidence_ids: List[str] = field(default_factory=list)
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolution_state: str = "UNRESOLVED"  # UNRESOLVED, RESOLVED_A, RESOLVED_B, COEXISTENT
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conflict_id": self.conflict_id,
            "hypothesis_a_id": self.hypothesis_a_id,
            "hypothesis_b_id": self.hypothesis_b_id,
            "conflicting_property": self.conflicting_property,
            "evidence_ids": self.evidence_ids,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "resolution_state": self.resolution_state,
            "notes": self.notes,
        }


@dataclass
class Hypothesis:
    """Autonomous candidate explanation for an incident or target."""
    hypothesis_id: str = field(default_factory=lambda: f"hyp_{uuid.uuid4().hex[:8]}")
    set_id: str = ""
    version: int = 1
    statement: str = ""
    claim: HypothesisClaim = field(default_factory=HypothesisClaim)
    scope: HypothesisScope = field(default_factory=HypothesisScope)
    status: HypothesisStatus = HypothesisStatus.CANDIDATE
    provenance: HypothesisProvenance = HypothesisProvenance.GENERATED
    proposer_agent_id: Optional[str] = None
    is_unknown_hypothesis: bool = False  # Set to True for UNKNOWN / OTHER CAUSE

    # Causal & mechanism details
    mechanism_summary: str = ""
    causal_node_refs: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)

    # Falsification & predictions
    falsification_conditions: List[HypothesisFalsificationCondition] = field(default_factory=list)
    predictions: List[HypothesisPrediction] = field(default_factory=list)

    # Multi-dimensional confidence
    confidence_profile: HypothesisConfidenceProfile = field(default_factory=HypothesisConfidenceProfile)

    # Attached evidence assessments
    assessments: List[HypothesisEvidenceAssessment] = field(default_factory=list)
    supporting_evidence_ids: List[str] = field(default_factory=list)
    contradicting_evidence_ids: List[str] = field(default_factory=list)
    falsifying_evidence_ids: List[str] = field(default_factory=list)

    # Lineage (splits, merges, supersessions)
    parent_hypothesis_ids: List[str] = field(default_factory=list)
    child_hypothesis_ids: List[str] = field(default_factory=list)
    superseded_by_id: Optional[str] = None

    # Lifecycle timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    stale_at: Optional[datetime] = None
    staleness_reason: Optional[str] = None

    # Cognitive bias safeguards
    contradiction_search_performed: bool = False
    bias_guard_triggers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "set_id": self.set_id,
            "version": self.version,
            "statement": self.statement,
            "claim": self.claim.to_dict(),
            "scope": self.scope.to_dict(),
            "status": self.status.value,
            "provenance": self.provenance.value,
            "proposer_agent_id": self.proposer_agent_id,
            "is_unknown_hypothesis": self.is_unknown_hypothesis,
            "mechanism_summary": self.mechanism_summary,
            "causal_node_refs": self.causal_node_refs,
            "assumptions": self.assumptions,
            "falsification_conditions": [f.to_dict() for f in self.falsification_conditions],
            "predictions": [p.to_dict() for p in self.predictions],
            "confidence_profile": self.confidence_profile.to_dict(),
            "assessments": [a.to_dict() for a in self.assessments],
            "supporting_evidence_ids": self.supporting_evidence_ids,
            "contradicting_evidence_ids": self.contradicting_evidence_ids,
            "falsifying_evidence_ids": self.falsifying_evidence_ids,
            "parent_hypothesis_ids": self.parent_hypothesis_ids,
            "child_hypothesis_ids": self.child_hypothesis_ids,
            "superseded_by_id": self.superseded_by_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "stale_at": self.stale_at.isoformat() if self.stale_at else None,
            "staleness_reason": self.staleness_reason,
            "contradiction_search_performed": self.contradiction_search_performed,
            "bias_guard_triggers": self.bias_guard_triggers,
        }


@dataclass
class HypothesisSet:
    """Set of competing hypotheses for a specific target incident or problem."""
    set_id: str = field(default_factory=lambda: f"hset_{uuid.uuid4().hex[:8]}")
    version: int = 1
    target_description: str = ""
    target_incident_id: Optional[str] = None
    scope: HypothesisScope = field(default_factory=HypothesisScope)
    active_hypothesis_ids: List[str] = field(default_factory=list)
    rejected_hypothesis_ids: List[str] = field(default_factory=list)
    unknown_hypothesis_id: Optional[str] = None
    unresolved_conflicts: List[HypothesisConflict] = field(default_factory=list)
    relationships: List[HypothesisRelationship] = field(default_factory=list)
    discriminators: List[HypothesisDiscriminator] = field(default_factory=list)
    information_gaps: List[str] = field(default_factory=list)
    is_resolved: bool = False
    resolution_summary: str = "CAUSE_UNKNOWN"  # By default unresolved
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "set_id": self.set_id,
            "version": self.version,
            "target_description": self.target_description,
            "target_incident_id": self.target_incident_id,
            "scope": self.scope.to_dict(),
            "active_hypothesis_ids": self.active_hypothesis_ids,
            "rejected_hypothesis_ids": self.rejected_hypothesis_ids,
            "unknown_hypothesis_id": self.unknown_hypothesis_id,
            "unresolved_conflicts": [c.to_dict() for c in self.unresolved_conflicts],
            "relationships": [r.to_dict() for r in self.relationships],
            "discriminators": [d.to_dict() for d in self.discriminators],
            "information_gaps": self.information_gaps,
            "is_resolved": self.is_resolved,
            "resolution_summary": self.resolution_summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass
class HypothesisSnapshot:
    """Immutable snapshot of a hypothesis set at a point in time."""
    snapshot_id: str = field(default_factory=lambda: f"hsnap_{uuid.uuid4().hex[:8]}")
    set_id: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    hypotheses_state: List[Dict[str, Any]] = field(default_factory=list)
    evidence_state: List[Dict[str, Any]] = field(default_factory=list)
    relationships_state: List[Dict[str, Any]] = field(default_factory=list)
    causal_model_version: str = "causal_v1"
    context_snapshot_id: Optional[str] = None
    world_state_id: Optional[str] = None
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "set_id": self.set_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "hypotheses_state": self.hypotheses_state,
            "evidence_state": self.evidence_state,
            "relationships_state": self.relationships_state,
            "causal_model_version": self.causal_model_version,
            "context_snapshot_id": self.context_snapshot_id,
            "world_state_id": self.world_state_id,
            "summary": self.summary,
        }


@dataclass
class HypothesisEvent:
    """Audit event emitted during hypothesis lifecycle."""
    event_id: str = field(default_factory=lambda: f"hevt_{uuid.uuid4().hex[:8]}")
    event_type: HypothesisEventType = HypothesisEventType.HYPOTHESIS_CREATED
    hypothesis_id: Optional[str] = None
    set_id: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "hypothesis_id": self.hypothesis_id,
            "set_id": self.set_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "details": self.details,
        }


@dataclass
class HypothesisExperimentCandidate:
    """Experiment proposed to test or falsify hypotheses (Task 105 integration)."""
    candidate_id: str = field(default_factory=lambda: f"hexp_{uuid.uuid4().hex[:8]}")
    target_hypothesis_id: str = ""
    competing_hypothesis_ids: List[str] = field(default_factory=list)
    expected_outcome: str = ""
    control_condition: Dict[str, Any] = field(default_factory=dict)
    treatment_condition: Dict[str, Any] = field(default_factory=dict)
    safety_constraints: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    falsification_criteria: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "target_hypothesis_id": self.target_hypothesis_id,
            "competing_hypothesis_ids": self.competing_hypothesis_ids,
            "expected_outcome": self.expected_outcome,
            "control_condition": self.control_condition,
            "treatment_condition": self.treatment_condition,
            "safety_constraints": self.safety_constraints,
            "success_criteria": self.success_criteria,
            "falsification_criteria": self.falsification_criteria,
        }
