"""Pydantic schemas for Autonomous Execution REST API endpoints (Task 45)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AutonomousGoalCreateRequest(BaseModel):
    title: str = Field(..., description="High-level goal title")
    description: str = Field(..., description="Detailed mission description")
    project_id: str = "default_project"
    success_criteria: List[str] = Field(default_factory=list)
    hard_constraints: List[str] = Field(default_factory=list)
    scope: Dict[str, Any] = Field(default_factory=dict)


class AutonomousGoalResponse(BaseModel):
    goal_id: str
    title: str
    description: str
    user_id: str
    project_id: str
    status: str
    success_criteria: List[str]
    created_at: str


class AutonomousRunCreateRequest(BaseModel):
    goal_id: str
    autonomy_level: str = "AUTONOMOUS"
    project_id: str = "default_project"
    max_model_calls: int = 100
    max_tool_calls: int = 50
    max_cost_usd: float = 5.0
    timeout_minutes: Optional[int] = 60
    initial_steps: Optional[List[Dict[str, Any]]] = None


class AutonomousRunResponse(BaseModel):
    run_id: str
    goal_id: str
    plan_id: str
    plan_version: int
    status: str
    autonomy_level: str
    owner_user_id: str
    project_id: str
    current_step_id: Optional[str] = None
    progress_pct: float
    created_at: str


class RunControlActionRequest(BaseModel):
    run_id: Optional[str] = None
    action: str  # PAUSE, RESUME, CANCEL, EMERGENCY_STOP
    reason: Optional[str] = None


class RunControlActionResponse(BaseModel):
    run_id: str
    status: str
    action_applied: str
    message: str


class StepExecutionRequest(BaseModel):
    is_pre_approved: bool = False
    is_dry_run: bool = False


class StepExecutionResponse(BaseModel):
    step_id: str
    is_success: bool
    is_verified: bool
    outputs: Dict[str, Any]
    verification_notes: str
    error: Optional[str] = None


class AutonomousCheckpointResponse(BaseModel):
    checkpoint_id: str
    run_id: str
    plan_version: int
    step_id: Optional[str]
    run_state: str
    is_valid: bool
    corruption_hash: str
    created_at: str


class CompletionRecordResponse(BaseModel):
    record_id: str
    run_id: str
    goal_id: str
    plan_version: int
    success_criteria: List[str]
    verification_results: List[str]
    evidence_refs: List[str]
    remaining_uncertainty: List[str]
    completed_at: str


class ProgressResponse(BaseModel):
    run_id: str
    status: str
    progress_pct: float
    total_steps: int
    completed_steps: int
    verified_criteria_count: int
    total_criteria_count: int
    summary: str


class WatchdogInspectionResponse(BaseModel):
    run_id: str
    issue_detected: str
    recommended_action: str
    details: Dict[str, Any]
    inspected_at: str


class JournalEntryResponse(BaseModel):
    id: str
    run_id: str
    event_type: str
    step_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    sequence_num: int
    created_at: str


class EventPostRequest(BaseModel):
    event_id: str
    event_type: str
    sequence_num: int
    step_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    is_authenticated: bool = True
