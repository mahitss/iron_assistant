"""Domain models, typed enums, and operational structures for Task 112:
KAIRO Autonomous Causal Explanation, Event Chain Reconstruction, Root-Cause Analysis & "Why Did This Happen?" Engine.

Hard Architectural Invariants:
- CAUSATION != CORRELATION
- TEMPORAL ORDER != CAUSATION
- GRAPH PATH != CAUSATION
- DEPENDENCY != CAUSATION
- CONTRIBUTION != SOLE CAUSE
- OBSERVATION != EXPLANATION
- EXPLANATION != TRUTH
- BELIEF != FACT
- FORECAST != OUTCOME
- SIMULATION != REALITY
- COUNTERFACTUAL != OBSERVATION
- MODEL OUTPUT != EVIDENCE
- AGENT CLAIM != INDEPENDENT EVIDENCE
- USER CLAIM != AUTOMATIC FACT
- ABSENCE OF EVIDENCE != EVIDENCE OF ABSENCE
- PLAUSIBLE EXPLANATION != VERIFIED EXPLANATION
- UNATTRIBUTED CHANGE MUST REMAIN UNATTRIBUTED
- NEVER FABRICATE CAUSAL CONFIDENCE OR EXPLANATIONS
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


def gen_explanation_id(prefix: str = "expl") -> str:
    """Generates unique prefixed identifier."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ============================================================================
# 1. Enums
# ============================================================================

class ExplanationLifecycleStage(str, Enum):
    """Lifecycle stages of an explanation (Section 5)."""
    REQUESTED = "REQUESTED"
    ASSEMBLING = "ASSEMBLING"
    HYPOTHESIS_GENERATED = "HYPOTHESIS_GENERATED"
    EVIDENCE_PENDING = "EVIDENCE_PENDING"
    TEMPORALLY_VALIDATED = "TEMPORALLY_VALIDATED"
    CAUSALLY_ASSESSED = "CAUSALLY_ASSESSED"
    ALTERNATIVES_ASSESSED = "ALTERNATIVES_ASSESSED"
    COUNTERFACTUAL_PENDING = "COUNTERFACTUAL_PENDING"
    PROVISIONAL = "PROVISIONAL"
    SUPPORTED = "SUPPORTED"
    CONTESTED = "CONTESTED"
    CONTRADICTED = "CONTRADICTED"
    VERIFICATION_PENDING = "VERIFICATION_PENDING"
    VERIFIED = "VERIFIED"
    STALE = "STALE"
    SUPERSEDED = "SUPERSEDED"
    REJECTED = "REJECTED"
    UNKNOWN = "UNKNOWN"


class CausalRelationshipRole(str, Enum):
    """Semantic role of a link in a causal chain (Section 9)."""
    DIRECT_CAUSE = "DIRECT_CAUSE"
    CONTRIBUTING_CAUSE = "CONTRIBUTING_CAUSE"
    UPSTREAM_CAUSE = "UPSTREAM_CAUSE"
    TRIGGER = "TRIGGER"
    ENABLING_CONDITION = "ENABLING_CONDITION"
    NECESSARY_CONDITION = "NECESSARY_CONDITION"
    SUFFICIENT_CONDITION = "SUFFICIENT_CONDITION"
    INHIBITOR = "INHIBITOR"
    PROTECTIVE_FACTOR = "PROTECTIVE_FACTOR"
    MEDIATOR = "MEDIATOR"
    CONFOUNDING_CANDIDATE = "CONFOUNDING_CANDIDATE"
    CORRELATED = "CORRELATED"
    TEMPORALLY_ASSOCIATED = "TEMPORALLY_ASSOCIATED"
    DEPENDENCY_ONLY = "DEPENDENCY_ONLY"
    UNKNOWN = "UNKNOWN"


class CausalStatus(str, Enum):
    """Causal confidence classification (Section 10)."""
    UNKNOWN = "UNKNOWN"
    CANDIDATE = "CANDIDATE"
    POSSIBLE = "POSSIBLE"
    SUPPORTED = "SUPPORTED"
    STRONGLY_SUPPORTED = "STRONGLY_SUPPORTED"
    CONTESTED = "CONTESTED"
    CONTRADICTED = "CONTRADICTED"
    REJECTED = "REJECTED"
    VERIFIED = "VERIFIED"


class RootCauseCategory(str, Enum):
    """Structural root cause categorization without forced mono-causality (Section 14)."""
    IMMEDIATE_TRIGGER = "IMMEDIATE_TRIGGER"
    CONTRIBUTING_FACTOR = "CONTRIBUTING_FACTOR"
    UPSTREAM_CAUSE = "UPSTREAM_CAUSE"
    ENABLING_CONDITION = "ENABLING_CONDITION"
    SYSTEMIC_FACTOR = "SYSTEMIC_FACTOR"
    ENVIRONMENTAL_FACTOR = "ENVIRONMENTAL_FACTOR"
    HUMAN_INPUT = "HUMAN_INPUT"
    CONFIGURATION = "CONFIGURATION"
    CAPABILITY_FAILURE = "CAPABILITY_FAILURE"
    RESOURCE_LIMIT = "RESOURCE_LIMIT"
    DEPENDENCY_FAILURE = "DEPENDENCY_FAILURE"
    EXTERNAL_CHANGE = "EXTERNAL_CHANGE"
    UNKNOWN = "UNKNOWN"


class EvidenceClassification(str, Enum):
    """Epistemic evidence quality classification (Section 11)."""
    DIRECT = "DIRECT"
    INDIRECT = "INDIRECT"
    DERIVED = "DERIVED"
    SIMULATED = "SIMULATED"
    SIMULATION = "SIMULATED"
    PREDICTIVE = "PREDICTIVE"
    FORECAST = "PREDICTIVE"
    AGENT_REPORTED = "AGENT_REPORTED"
    AGENT_REPORT = "AGENT_REPORTED"
    USER_REPORTED = "USER_REPORTED"
    USER_REPORT = "USER_REPORTED"
    HISTORICAL = "HISTORICAL"
    UNVERIFIED = "UNVERIFIED"


class VerificationOutcome(str, Enum):
    """Outcome of empirical follow-up verification (Section 38)."""
    SUPPORTED = "SUPPORTED"
    WEAKENED = "WEAKENED"
    CONTRADICTED = "CONTRADICTED"
    UNRESOLVED = "UNRESOLVED"


# ============================================================================
# 2. Domain Data Models
# ============================================================================

class CausalConfidenceBreakdown(BaseModel):
    """Decomposed multi-dimensional causal confidence (Section 20)."""
    model_config = ConfigDict(extra="ignore")

    temporal_fit: float = Field(default=0.5, ge=0.0, le=1.0)
    mechanism_fit: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence_strength: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence_independence: float = Field(default=1.0, ge=0.0, le=1.0)
    intervention_support: float = Field(default=0.0, ge=0.0, le=1.0)
    counterfactual_support: float = Field(default=0.0, ge=0.0, le=1.0)
    contradiction_penalty: float = Field(default=0.0, ge=0.0, le=1.0)
    uncertainty_score: float = Field(default=0.5, ge=0.0, le=1.0)
    observational_completeness: float = Field(default=0.5, ge=0.0, le=1.0)
    composite_confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    @classmethod
    def calculate_composite(
        cls,
        temporal_fit: float,
        mechanism_fit: float,
        evidence_strength: float,
        evidence_independence: float = 1.0,
        contradiction_penalty: float = 0.0,
        observational_completeness: float = 0.5,
    ) -> CausalConfidenceBreakdown:
        # Base weighted sum
        raw = (
            temporal_fit * 0.25
            + mechanism_fit * 0.25
            + (evidence_strength * evidence_independence) * 0.35
            + observational_completeness * 0.15
        )
        # Apply contradiction penalty
        adjusted = max(0.0, raw - (contradiction_penalty * 0.5))
        composite = round(min(1.0, max(0.0, adjusted)), 3)
        uncertainty = round(1.0 - composite, 3)

        return cls(
            temporal_fit=temporal_fit,
            mechanism_fit=mechanism_fit,
            evidence_strength=evidence_strength,
            evidence_independence=evidence_independence,
            contradiction_penalty=contradiction_penalty,
            uncertainty_score=uncertainty,
            observational_completeness=observational_completeness,
            composite_confidence=composite,
        )


class ExplanationEvidence(BaseModel):
    """Empirical evidence item supporting or contradicting a causal link (Section 11)."""
    model_config = ConfigDict(extra="ignore")

    evidence_id: str = Field(default_factory=lambda: gen_explanation_id("evid"))
    classification: EvidenceClassification = EvidenceClassification.DIRECT
    source_subsystem: str
    source_entity_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=utc_now)
    content: str
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    is_contradiction: bool = False
    is_untrusted_source: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CausalLink(BaseModel):
    """Verified or hypothesized directional causal step between two nodes (Section 9)."""
    model_config = ConfigDict(extra="ignore")

    link_id: str = Field(default_factory=lambda: gen_explanation_id("link"))
    source_node: str
    target_node: str
    relationship_role: CausalRelationshipRole = CausalRelationshipRole.DIRECT_CAUSE
    status: CausalStatus = CausalStatus.CANDIDATE
    mechanism: str = "Proposed direct transmission mechanism"
    lag_seconds: float = 0.0
    confidence: CausalConfidenceBreakdown = Field(default_factory=CausalConfidenceBreakdown)
    supporting_evidence: List[ExplanationEvidence] = Field(default_factory=list)
    contradicting_evidence: List[ExplanationEvidence] = Field(default_factory=list)
    is_temporally_valid: bool = True
    assumptions: List[str] = Field(default_factory=list)


class CausalContributor(BaseModel):
    """A contributor to an incident with qualitative contribution level (Section 24)."""
    model_config = ConfigDict(extra="ignore")

    contributor_id: str = Field(default_factory=lambda: gen_explanation_id("cntr"))
    entity_id: str
    category: RootCauseCategory = RootCauseCategory.CONTRIBUTING_FACTOR
    role: CausalRelationshipRole = CausalRelationshipRole.CONTRIBUTING_CAUSE
    description: str
    qualitative_contribution: str = "MODERATE"  # LOW, MODERATE, HIGH, UNCERTAIN
    estimated_fraction: Optional[float] = None
    confidence: float = 0.5


class EventChainStep(BaseModel):
    """Chronologically reconstructed step in a failure chain (Section 8)."""
    model_config = ConfigDict(extra="ignore")

    step_index: int
    event_id: str
    event_type: str
    entity_id: str
    timestamp: datetime
    state_before: Optional[str] = None
    state_after: Optional[str] = None
    source_subsystem: str = "system"
    is_causally_linked: bool = False
    transition_role: Optional[CausalRelationshipRole] = None
    evidence_summary: str = ""


class EventChain(BaseModel):
    """Bounded sequence of events and transitions leading to target (Section 8)."""
    model_config = ConfigDict(extra="ignore")

    chain_id: str = Field(default_factory=lambda: gen_explanation_id("chn"))
    target_event_id: str
    target_entity_id: str
    start_time: datetime
    end_time: datetime
    steps: List[EventChainStep] = Field(default_factory=list)
    total_steps: int = 0
    is_truncated: bool = False


class CausalAlternative(BaseModel):
    """Competing alternative causal hypothesis with discriminating test (Section 16, 17)."""
    model_config = ConfigDict(extra="ignore")

    alternative_id: str = Field(default_factory=lambda: gen_explanation_id("alt"))
    name: str
    hypothesis_summary: str
    proposed_cause: str
    confidence: float = 0.5
    supporting_points: List[str] = Field(default_factory=list)
    contradicting_points: List[str] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    discriminating_observation: str = Field(
        description="Specific observation or metric that would distinguish this alternative from primary"
    )
    status: CausalStatus = CausalStatus.POSSIBLE


class CounterfactualScenario(BaseModel):
    """Explicit what-if scenario (Section 18). Must be tagged is_hypothetical=True."""
    model_config = ConfigDict(extra="ignore")

    scenario_id: str = Field(default_factory=lambda: gen_explanation_id("cf"))
    target_incident_id: str
    intervention_description: str  # "What if resource allocation was 8GB instead of 2GB?"
    expected_difference: str       # "Queue would not have backlogged"
    assumptions: List[str] = Field(default_factory=list)
    confidence: float = 0.5
    is_hypothetical: bool = True   # Hard guarantee: never presented as empirical fact
    simulated_outcome: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class ExplanationGap(BaseModel):
    """Unobserved periods, missing telemetry, or unresolved uncertainties (Section 21)."""
    model_config = ConfigDict(extra="ignore")

    gap_id: str = Field(default_factory=lambda: gen_explanation_id("gap"))
    subsystem: str
    description: str
    why_it_matters: str
    missing_data_type: str = "telemetry"  # telemetry, transition, control_group, dependency
    severity: str = "MEDIUM"  # LOW, MEDIUM, HIGH, CRITICAL


class ExplanationVerification(BaseModel):
    """Follow-up empirical verification record (Section 38)."""
    model_config = ConfigDict(extra="ignore")

    verification_id: str = Field(default_factory=lambda: gen_explanation_id("ver"))
    explanation_id: str
    tested_hypothesis: str
    predicted_consequence: str
    actual_observation: str
    outcome: VerificationOutcome = VerificationOutcome.UNRESOLVED
    observation_timestamp: datetime = Field(default_factory=utc_now)
    verified_by_actor: str = "system"
    notes: Optional[str] = None


class ExplanationRequest(BaseModel):
    """Typed request for causal explanation (Section 6)."""
    model_config = ConfigDict(extra="ignore")

    target_entity: str
    target_event_id: Optional[str] = None
    target_state_change: Optional[str] = None
    target_incident_id: Optional[str] = None
    time_window_start: Optional[datetime] = None
    time_window_end: Optional[datetime] = None
    max_chain_depth: int = Field(default=10, le=50)
    min_confidence_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    user_query: Optional[str] = None
    scope: str = "DEFAULT"


class ExplanationQualityAssessment(BaseModel):
    """Multi-dimensional evaluation of explanation rigor (Section 39)."""
    model_config = ConfigDict(extra="ignore")

    evidence_coverage: float = 0.5
    causal_support: float = 0.5
    temporal_consistency: float = 1.0
    mechanism_completeness: float = 0.5
    alternative_coverage: float = 0.5
    contradiction_visibility: float = 1.0
    uncertainty_calibration: float = 0.8
    overall_quality: float = 0.65


class CausalExplanation(BaseModel):
    """Complete, auditable, structured causal explanation (Section 1, 4, 55)."""
    model_config = ConfigDict(extra="ignore")

    explanation_id: str = Field(default_factory=lambda: gen_explanation_id("expl"))
    version: int = 1
    target_entity: str
    target_event_id: Optional[str] = None
    target_state_change: Optional[str] = None
    lifecycle_stage: ExplanationLifecycleStage = ExplanationLifecycleStage.REQUESTED
    
    # 6-Part Structured Human-Readable Components (Section 55)
    what_happened: str = ""
    what_changed: str = ""
    what_preceded_it: str = ""
    why_it_happened: str = "CAUSE UNKNOWN"
    contributing_factors_summary: str = ""
    what_would_verify_this: str = ""

    # Deep Causal Artifacts
    root_cause_category: RootCauseCategory = RootCauseCategory.UNKNOWN
    primary_cause: Optional[str] = None
    primary_mechanism: Optional[str] = None
    causal_links: List[CausalLink] = Field(default_factory=list)
    contributors: List[CausalContributor] = Field(default_factory=list)
    event_chain: Optional[EventChain] = None
    alternatives: List[CausalAlternative] = Field(default_factory=list)
    counterfactuals: List[CounterfactualScenario] = Field(default_factory=list)
    unresolved_gaps: List[ExplanationGap] = Field(default_factory=list)
    
    # Confidence & Calibration
    confidence: CausalConfidenceBreakdown = Field(default_factory=CausalConfidenceBreakdown)
    quality: ExplanationQualityAssessment = Field(default_factory=ExplanationQualityAssessment)
    is_verified: bool = False
    is_cause_unknown: bool = True
    superseded_by: Optional[str] = None
    
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    scope: str = "DEFAULT"
    metadata: Dict[str, Any] = Field(default_factory=dict)
