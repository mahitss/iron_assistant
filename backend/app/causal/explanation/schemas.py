"""Pydantic v2 schemas for Task 112 Causal Explanation REST API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.causal.explanation.domain import (
    CausalAlternative,
    CausalConfidenceBreakdown,
    CausalContributor,
    CausalExplanation,
    CausalLink,
    CounterfactualScenario,
    EventChain,
    ExplanationEvidence,
    ExplanationGap,
    ExplanationLifecycleStage,
    ExplanationQualityAssessment,
    ExplanationVerification,
    RootCauseCategory,
)


class CreateExplanationRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    target_entity: str
    target_event_id: Optional[str] = None
    target_state_change: Optional[str] = None
    target_incident_id: Optional[str] = None
    user_query: Optional[str] = None
    time_window_start: Optional[datetime] = None
    time_window_end: Optional[datetime] = None
    max_chain_depth: int = Field(default=10, le=50)
    min_confidence_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    scope: str = "DEFAULT"


class VerifyExplanationRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    actual_observation: str
    predicted_consequence: Optional[str] = None
    actor: str = "operator"
    notes: Optional[str] = None


class ExplanationFeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    actor: str = "operator"
    feedback_text: str
    is_accurate: bool = True
    suggested_alternative: Optional[str] = None


class ExplanationSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    explanation_id: str
    target_entity: str
    lifecycle_stage: str
    primary_cause: Optional[str]
    root_cause_category: str
    composite_confidence: float
    is_verified: bool
    is_cause_unknown: bool
    created_at: datetime
    updated_at: datetime
