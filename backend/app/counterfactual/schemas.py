"""Pydantic schemas for Task 113 REST API endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class CounterfactualCreateRequest(BaseModel):
    """Request payload to initiate counterfactual analysis."""
    target_entity: str
    target_variable: str | None = None
    question: str = "What would happen if we intervene?"
    counterfactual_type: str = "RESOURCE"  # ABSTENTION, SUBSTITUTION, TIMING, DOSAGE, RESOURCE, CAPABILITY, DEPENDENCY, POLICY, ENVIRONMENT, COMBINATIONAL
    baseline_type: str = "CURRENT"        # HISTORICAL, CURRENT, RECONSTRUCTED, SIMULATED, EXPECTED, NO_ACTION
    baseline_time: datetime | None = None
    candidate_interventions: list[dict[str, Any]] = Field(default_factory=list)
    include_no_action: bool = True
    causal_depth_limit: int = 4
    simulation_budget_seconds: float = 10.0


class CounterfactualSimulateRequest(BaseModel):
    """Request payload to re-run or simulate specific scenario."""
    scenario_id: str | None = None
    simulation_budget_seconds: float = 5.0
    random_seed: int | None = None


class CounterfactualVerifyRequest(BaseModel):
    """Request payload to verify prediction against real observed telemetry."""
    executed_intervention_id: str
    observed_state: dict[str, Any]


class CounterfactualFeedbackRequest(BaseModel):
    """User or operator feedback on counterfactual accuracy."""
    feedback_score: float = Field(..., ge=0.0, le=1.0)
    comments: str = ""


class ScenarioResponse(BaseModel):
    scenario_id: str
    scenario_name: str
    is_no_action: bool
    scenario_type: str
    predicted_state: dict[str, Any] | None = None
    outcome: dict[str, Any] | None = None
    is_hypothetical: bool = True


class ComparisonResponse(BaseModel):
    comparison_id: str
    baseline_scenario_id: str
    items: list[dict[str, Any]]
    tradeoff_summary: str
    recommended_option: str | None = None
    no_action_viable: bool = True


class CounterfactualResponse(BaseModel):
    analysis_id: str
    target_entity: str
    question: str
    lifecycle_stage: str
    counterfactual_type: str
    baseline_id: str
    baseline_type: str
    scenarios_count: int
    recommended_candidate: str | None = None
    no_action_viable: bool = True
    is_stale: bool = False
    stale_reason: str = ""
    environment_label: str = "SIMULATION_ONLY"
    is_hypothetical: bool = True
    created_at: datetime
    updated_at: datetime
