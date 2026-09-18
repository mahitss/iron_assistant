"""Pydantic API request and response schemas for Task 110:
Cognitive Working Set, Relevance Packing & Context Lifecycle Engine.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.context.working_set_domain import (
    CompressionLevel,
    FreshnessClassification,
    ItemInclusionSemantics,
    LeaseState,
    WorkingSetLifecycle,
)


class ContextAssemblyRequestSchema(BaseModel):
    """Client request schema for triggering cognitive working set assembly."""
    operation_type: str = Field(default="DELIBERATION", description="Target cognitive operation type")
    operation_id: Optional[str] = Field(default=None, description="Optional caller operation tracking ID")
    session_id: Optional[str] = Field(default=None, description="Active user session ID")
    conversation_id: Optional[str] = Field(default=None, description="Active chat conversation thread ID")
    objective: str = Field(..., description="Core task objective or inquiry")
    explicit_user_request: Optional[str] = Field(default=None, description="Raw user prompt string")
    current_intent_id: Optional[str] = Field(default=None, description="Task 108 intent reference")
    active_mission_id: Optional[str] = Field(default=None, description="Task 100 mission reference")
    active_goal_id: Optional[str] = Field(default=None, description="Task 100 goal reference")
    active_situation_id: Optional[str] = Field(default=None, description="Situation awareness reference")
    active_decision_id: Optional[str] = Field(default=None, description="Task 94 decision reference")
    active_action_transaction_id: Optional[str] = Field(default=None, description="Task 95 action transaction reference")
    agent_id: Optional[str] = Field(default=None, description="Calling agent identifier")
    token_budget: int = Field(default=8000, description="Max token capacity allocated by Task 77 Resource Economy")
    latency_budget_ms: float = Field(default=250.0, description="Maximum assembly latency in milliseconds")
    freshness_threshold_seconds: float = Field(default=3600.0, description="Max acceptable age before marking stale")
    compression_policy: str = Field(default="ADAPTIVE", description="Compression policy: NONE, LIGHT, ADAPTIVE, AGGRESSIVE")
    pinned_item_ids: List[str] = Field(default_factory=list, description="IDs of items required to be pinned")
    forbidden_sources: List[str] = Field(default_factory=list, description="Sources explicitly forbidden from inclusion")
    user_scope: str = Field(default="default_user", description="Authenticated user scope")
    tenant_id: str = Field(default="default", description="Tenant namespace")


class ContextItemResponseSchema(BaseModel):
    """Item detail representation returned by working set endpoints."""
    item_id: str
    version: int
    section: str
    title: str
    content: str
    inclusion: ItemInclusionSemantics
    relevance_score: float
    relevance_components: Dict[str, float]
    confidence: float
    freshness_classification: FreshnessClassification
    provenance_source: str
    trust_label: str
    compression_level: CompressionLevel
    token_estimate: int
    character_count: int
    is_pinned: bool
    is_untrusted: bool
    dependencies: List[str]
    created_at: datetime


class ContextSectionResponseSchema(BaseModel):
    """Section summary representation."""
    section_type: str
    title: str
    item_count: int
    total_tokens: int
    is_empty: bool
    items: List[ContextItemResponseSchema] = Field(default_factory=list)


class WorkingSetResponseSchema(BaseModel):
    """Complete representation of an assembled Cognitive Working Set."""
    working_set_id: str
    version: int
    tenant_id: str
    user_scope: str
    operation_type: str
    operation_id: Optional[str]
    request_id: str
    objective: str
    lifecycle: WorkingSetLifecycle
    lease_state: LeaseState
    lease_expires_at: Optional[datetime]
    quality_score: float
    completeness_estimate: float
    confidence_summary: float
    item_count: int
    total_tokens: int
    compressed_item_count: int
    has_untrusted_content: bool
    conflicts_count: int
    gaps_count: int
    exclusions_count: int
    pinned_items_count: int
    sections: Dict[str, ContextSectionResponseSchema]
    trace_id: str
    created_at: datetime
    updated_at: datetime


class ContextPinRequestSchema(BaseModel):
    """Request payload to pin or unpin an item within a working set."""
    item_id: str
    reason: str = "User requested pin"


class ContextFeedbackRequestSchema(BaseModel):
    """Request payload to submit post-deliberation usage feedback."""
    operation_id: Optional[str] = None
    items_used: List[str] = Field(default_factory=list)
    items_ignored: List[str] = Field(default_factory=list)
    items_misleading: List[str] = Field(default_factory=list)
    items_missing: List[str] = Field(default_factory=list)
    was_compression_harmful: bool = False
    was_freshness_sufficient: bool = True
    context_size_rating: str = "OPTIMAL"
    downstream_outcome: str = "SUCCESS"
    comments: Optional[str] = None


class ContextQualityResponseSchema(BaseModel):
    """Quality scorecard response across 13 dimensions."""
    assessment_id: str
    working_set_id: str
    relevance_score: float
    freshness_score: float
    completeness_score: float
    provenance_coverage_score: float
    contradiction_visibility_score: float
    redundancy_penalty: float
    compression_quality_score: float
    budget_efficiency_score: float
    latency_score: float
    source_diversity_score: float
    task_alignment_score: float
    safety_coverage_score: float
    isolation_correctness_score: float
    composite_quality: float
    created_at: datetime


class ContextSnapshotResponseSchema(BaseModel):
    """Immutable audit snapshot response."""
    snapshot_id: str
    working_set_id: str
    working_set_version: int
    operation_type: str
    operation_id: Optional[str]
    item_ids: List[str]
    source_versions: Dict[str, str]
    total_tokens: int
    quality_score: float
    has_untrusted_content: bool
    snapshot_hash: str
    trace_id: str
    created_at: datetime
