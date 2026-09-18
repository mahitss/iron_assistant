"""Pydantic v2 schemas and API contracts for Task 114 Active Observation Engine."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.observation.domain import (
    InformationGap,
    InformationValueEstimate,
    ObservationCandidate,
    ObservationMethodType,
    ObservationOutcome,
    ObservationPlan,
    ObservationPlanStatus,
    ObservationScope,
    ObservationVerification,
    StopConditionReason,
    UncertaintyDimensionType,
    UncertaintyState,
)


class ObservationPlanCreateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    target_entity: str = Field(..., description="Target entity, node, or capability requiring observation")
    question: str = Field(default="What don't I know and what observation is needed?", description="Inquiry question")
    dependent_decision_id: Optional[str] = None
    dependent_mission_id: Optional[str] = None
    dependent_situation_id: Optional[str] = None
    uncertainty_dimensions: List[UncertaintyDimensionType] = Field(default_factory=list)
    budget_units: float = Field(default=10.0, ge=0.5, le=100.0)
    deadline_seconds: float = Field(default=30.0, ge=1.0, le=3600.0)
    scope: ObservationScope = ObservationScope.ENTITY
    observed_signals: Optional[Dict[str, Any]] = None
    existing_internal_data: Optional[List[Dict[str, Any]]] = None
    causal_hypotheses: Optional[List[str]] = None


class ObservationExecuteRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    candidate_id: Optional[str] = Field(default=None, description="Specific candidate ID to execute, or None for best VoI candidate")
    simulated_outcome_data: Optional[Dict[str, Any]] = None


class ObservationPlanResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    plan_id: str
    version: int
    objective: str
    target_entity: str
    status: ObservationPlanStatus
    recommended_stance: str
    gaps_count: int
    candidates_count: int
    outcomes_count: int
    budget_allocated: float
    budget_spent: float
    stop_reason: Optional[str] = None
    is_stale: bool
    overall_confidence_before: Optional[float] = None
    overall_confidence_after: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class ObservationPlanDetailResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    plan: ObservationPlan


class UncertaintyResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    target_entity: str
    overall_confidence: float
    dimensions: Dict[str, Any]
    missing_data_count: int
    stale_signals_count: int
    assessed_at: datetime


class InformationGapsResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    plan_id: str
    target_entity: str
    gaps: List[InformationGap]


class ObservationCandidatesResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    plan_id: str
    target_entity: str
    candidates: List[ObservationCandidate]


class ObservationVerificationResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    plan_id: str
    verifications: List[ObservationVerification]
