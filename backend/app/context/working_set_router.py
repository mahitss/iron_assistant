"""FastAPI REST router for Task 110:
Cognitive Working Set, Relevance Packing & Context Lifecycle Engine.
"""

from typing import Annotated, Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.context.working_set_domain import (
    ContextAssemblyRequest,
    ContextFeedback,
    WorkingSet,
)
from app.context.working_set_schemas import (
    ContextAssemblyRequestSchema,
    ContextFeedbackRequestSchema,
    ContextItemResponseSchema,
    ContextPinRequestSchema,
    ContextQualityResponseSchema,
    ContextSectionResponseSchema,
    ContextSnapshotResponseSchema,
    WorkingSetResponseSchema,
)
from app.context.working_set_service import WorkingSetService

router = APIRouter(tags=["Cognitive Working Set"])


def get_user_scope(x_user_id: Annotated[Optional[str], Header()] = None) -> str:
    """Extract authenticated user scope from request headers."""
    if not x_user_id or not x_user_id.strip():
        return "default_user"
    return x_user_id.strip()


def get_tenant_id(x_tenant_id: Annotated[Optional[str], Header()] = None) -> str:
    """Extract authenticated tenant ID from request headers."""
    if not x_tenant_id or not x_tenant_id.strip():
        return "default"
    return x_tenant_id.strip()


def _serialize_working_set(ws: WorkingSet) -> WorkingSetResponseSchema:
    """Helper serializer converting domain WorkingSet to API response schema."""
    sections_resp: Dict[str, ContextSectionResponseSchema] = {}
    for sec_type, sec in ws.sections.items():
        items_resp = [
            ContextItemResponseSchema(
                item_id=item.item_id,
                version=item.version,
                section=item.section.value,
                title=item.title,
                content=item.content,
                inclusion=item.inclusion,
                relevance_score=item.relevance_score,
                relevance_components=item.relevance_components,
                confidence=item.confidence,
                freshness_classification=item.freshness.classification,
                provenance_source=item.provenance.source_type,
                trust_label=item.provenance.trust_label.value,
                compression_level=item.compression,
                token_estimate=item.token_estimate,
                character_count=item.character_count,
                is_pinned=item.is_pinned,
                is_untrusted=item.is_untrusted,
                dependencies=item.dependencies,
                created_at=item.created_at,
            )
            for item in sec.items
        ]
        sections_resp[sec_type] = ContextSectionResponseSchema(
            section_type=sec.section_type.value,
            title=sec.title,
            item_count=sec.item_count,
            total_tokens=sec.total_tokens,
            is_empty=sec.is_empty,
            items=items_resp,
        )

    lease_state = ws.lease.state if ws.lease else None
    lease_expires = ws.lease.expires_at if ws.lease else None

    return WorkingSetResponseSchema(
        working_set_id=ws.working_set_id,
        version=ws.version,
        tenant_id=ws.tenant_id,
        user_scope=ws.user_scope,
        operation_type=ws.operation_type,
        operation_id=ws.operation_id,
        request_id=ws.request_id,
        objective=ws.objective,
        lifecycle=ws.lifecycle,
        lease_state=lease_state or "VALID",
        lease_expires_at=lease_expires,
        quality_score=ws.quality_score,
        completeness_estimate=ws.completeness_estimate,
        confidence_summary=ws.confidence_summary,
        item_count=ws.item_count,
        total_tokens=ws.total_tokens,
        compressed_item_count=ws.compressed_item_count,
        has_untrusted_content=ws.has_untrusted_content,
        conflicts_count=len(ws.conflicts),
        gaps_count=len(ws.gaps),
        exclusions_count=len(ws.exclusions),
        pinned_items_count=len(ws.pinned_items),
        sections=sections_resp,
        trace_id=ws.trace_id,
        created_at=ws.created_at,
        updated_at=ws.updated_at,
    )


# ============================================================================
# Endpoints
# ============================================================================

@router.post(
    "/context/assemble",
    response_model=WorkingSetResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Assemble a bounded Cognitive Working Set for downstream operation",
)
async def assemble_context(
    payload: ContextAssemblyRequestSchema,
    user_scope: Annotated[str, Depends(get_user_scope)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> WorkingSetResponseSchema:
    service = WorkingSetService.get_instance()

    req = ContextAssemblyRequest(
        tenant_id=tenant_id,
        user_scope=user_scope,
        operation_type=payload.operation_type,
        operation_id=payload.operation_id,
        session_id=payload.session_id,
        conversation_id=payload.conversation_id,
        objective=payload.objective,
        explicit_user_request=payload.explicit_user_request,
        current_intent_id=payload.current_intent_id,
        active_mission_id=payload.active_mission_id,
        active_goal_id=payload.active_goal_id,
        active_situation_id=payload.active_situation_id,
        active_decision_id=payload.active_decision_id,
        active_action_transaction_id=payload.active_action_transaction_id,
        agent_id=payload.agent_id,
        token_budget=payload.token_budget,
        latency_budget_ms=payload.latency_budget_ms,
        freshness_threshold_seconds=payload.freshness_threshold_seconds,
        compression_policy=payload.compression_policy,
        pinned_item_ids=payload.pinned_item_ids,
        forbidden_sources=payload.forbidden_sources,
    )

    ws = service.assemble_working_set(req)
    return _serialize_working_set(ws)


@router.get(
    "/context/working-sets",
    response_model=List[WorkingSetResponseSchema],
    summary="List active working sets",
)
async def list_working_sets(
    user_scope: Annotated[str, Depends(get_user_scope)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> List[WorkingSetResponseSchema]:
    service = WorkingSetService.get_instance()
    results = service.list_working_sets(user_scope=user_scope, tenant_id=tenant_id)
    return [_serialize_working_set(ws) for ws in results]


@router.get(
    "/context/working-sets/{working_set_id}",
    response_model=WorkingSetResponseSchema,
    summary="Retrieve a specific working set",
)
async def get_working_set(working_set_id: str) -> WorkingSetResponseSchema:
    service = WorkingSetService.get_instance()
    ws = service.get_working_set(working_set_id)
    if not ws:
        raise HTTPException(status_code=404, detail=f"Working set '{working_set_id}' not found")
    return _serialize_working_set(ws)


@router.get(
    "/context/working-sets/{working_set_id}/items",
    response_model=List[ContextItemResponseSchema],
    summary="List all items within a working set",
)
async def get_working_set_items(working_set_id: str) -> List[ContextItemResponseSchema]:
    service = WorkingSetService.get_instance()
    ws = service.get_working_set(working_set_id)
    if not ws:
        raise HTTPException(status_code=404, detail=f"Working set '{working_set_id}' not found")

    items_out: List[ContextItemResponseSchema] = []
    for sec in ws.sections.values():
        for item in sec.items:
            items_out.append(
                ContextItemResponseSchema(
                    item_id=item.item_id,
                    version=item.version,
                    section=item.section.value,
                    title=item.title,
                    content=item.content,
                    inclusion=item.inclusion,
                    relevance_score=item.relevance_score,
                    relevance_components=item.relevance_components,
                    confidence=item.confidence,
                    freshness_classification=item.freshness.classification,
                    provenance_source=item.provenance.source_type,
                    trust_label=item.provenance.trust_label.value,
                    compression_level=item.compression,
                    token_estimate=item.token_estimate,
                    character_count=item.character_count,
                    is_pinned=item.is_pinned,
                    is_untrusted=item.is_untrusted,
                    dependencies=item.dependencies,
                    created_at=item.created_at,
                )
            )
    return items_out


@router.get(
    "/context/working-sets/{working_set_id}/provenance",
    summary="Inspect provenance details of all items in a working set",
)
async def get_working_set_provenance(working_set_id: str) -> Dict[str, Any]:
    service = WorkingSetService.get_instance()
    ws = service.get_working_set(working_set_id)
    if not ws:
        raise HTTPException(status_code=404, detail=f"Working set '{working_set_id}' not found")

    prov_map = {}
    for sec in ws.sections.values():
        for item in sec.items:
            prov_map[item.item_id] = {
                "source_type": item.provenance.source_type,
                "source_id": item.provenance.source_id,
                "originating_subsystem": item.provenance.originating_subsystem,
                "trust_label": item.provenance.trust_label.value,
                "lineage_path": item.provenance.lineage_path,
                "signature": item.provenance.signature,
                "observation_timestamp": item.provenance.observation_timestamp.isoformat(),
            }
    return {"working_set_id": working_set_id, "items_provenance": prov_map}


@router.get(
    "/context/working-sets/{working_set_id}/conflicts",
    summary="List explicitly preserved conflicts within a working set",
)
async def get_working_set_conflicts(working_set_id: str) -> List[Dict[str, Any]]:
    service = WorkingSetService.get_instance()
    ws = service.get_working_set(working_set_id)
    if not ws:
        raise HTTPException(status_code=404, detail=f"Working set '{working_set_id}' not found")
    return [c.model_dump() for c in ws.conflicts]


@router.get(
    "/context/working-sets/{working_set_id}/gaps",
    summary="List identified missing context gaps within a working set",
)
async def get_working_set_gaps(working_set_id: str) -> List[Dict[str, Any]]:
    service = WorkingSetService.get_instance()
    ws = service.get_working_set(working_set_id)
    if not ws:
        raise HTTPException(status_code=404, detail=f"Working set '{working_set_id}' not found")
    return [g.model_dump() for g in ws.gaps]


@router.get(
    "/context/working-sets/{working_set_id}/snapshot",
    response_model=ContextSnapshotResponseSchema,
    summary="Retrieve immutable audit snapshot for a working set",
)
async def get_working_set_snapshot(working_set_id: str) -> ContextSnapshotResponseSchema:
    service = WorkingSetService.get_instance()
    snap = service.get_snapshot(working_set_id)
    if not snap:
        raise HTTPException(status_code=404, detail=f"Snapshot for '{working_set_id}' not found")

    return ContextSnapshotResponseSchema(
        snapshot_id=snap.snapshot_id,
        working_set_id=snap.working_set_id,
        working_set_version=snap.working_set_version,
        operation_type=snap.operation_type,
        operation_id=snap.operation_id,
        item_ids=snap.item_ids,
        source_versions=snap.source_versions,
        total_tokens=snap.total_tokens,
        quality_score=snap.quality_score,
        has_untrusted_content=snap.has_untrusted_content,
        snapshot_hash=snap.snapshot_hash,
        trace_id=snap.trace_id,
        created_at=snap.created_at,
    )


@router.post(
    "/context/working-sets/{working_set_id}/refresh",
    response_model=WorkingSetResponseSchema,
    summary="Incrementally refresh and revalidate a working set",
)
async def refresh_working_set(
    working_set_id: str,
    sections: Optional[List[str]] = Query(default=None),
) -> WorkingSetResponseSchema:
    service = WorkingSetService.get_instance()
    try:
        updated = service.refresh_working_set(working_set_id, sections_to_refresh=sections)
        return _serialize_working_set(updated)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/context/working-sets/{working_set_id}/invalidate",
    response_model=WorkingSetResponseSchema,
    summary="Explicitly invalidate a working set fail-closed",
)
async def invalidate_working_set(
    working_set_id: str,
    reason: str = Query(default="Manual invalidation"),
) -> WorkingSetResponseSchema:
    service = WorkingSetService.get_instance()
    try:
        invalidated = service.invalidate_working_set(working_set_id, reason=reason)
        return _serialize_working_set(invalidated)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/context/working-sets/{working_set_id}/pin",
    response_model=WorkingSetResponseSchema,
    summary="Pin a context item within the working set",
)
async def pin_context_item(
    working_set_id: str,
    payload: ContextPinRequestSchema,
) -> WorkingSetResponseSchema:
    service = WorkingSetService.get_instance()
    try:
        updated = service.pin_item(working_set_id, payload.item_id, reason=payload.reason)
        return _serialize_working_set(updated)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/context/working-sets/{working_set_id}/unpin",
    response_model=WorkingSetResponseSchema,
    summary="Unpin a context item within the working set",
)
async def unpin_context_item(
    working_set_id: str,
    item_id: str = Query(...),
) -> WorkingSetResponseSchema:
    service = WorkingSetService.get_instance()
    try:
        updated = service.unpin_item(working_set_id, item_id)
        return _serialize_working_set(updated)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/context/working-sets/{working_set_id}/feedback",
    summary="Submit post-deliberation empirical feedback",
)
async def submit_context_feedback(
    working_set_id: str,
    payload: ContextFeedbackRequestSchema,
) -> Dict[str, Any]:
    service = WorkingSetService.get_instance()
    feedback = ContextFeedback(
        working_set_id=working_set_id,
        operation_id=payload.operation_id,
        items_used=payload.items_used,
        items_ignored=payload.items_ignored,
        items_misleading=payload.items_misleading,
        items_missing=payload.items_missing,
        was_compression_harmful=payload.was_compression_harmful,
        was_freshness_sufficient=payload.was_freshness_sufficient,
        context_size_rating=payload.context_size_rating,
        downstream_outcome=payload.downstream_outcome,
        comments=payload.comments,
    )
    try:
        return service.record_feedback(working_set_id, feedback)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get(
    "/context/working-sets/{working_set_id}/quality",
    response_model=ContextQualityResponseSchema,
    summary="Retrieve 13-dimension quality assessment for a working set",
)
async def get_context_quality(working_set_id: str) -> ContextQualityResponseSchema:
    service = WorkingSetService.get_instance()
    q = service.get_quality_assessment(working_set_id)
    if not q:
        raise HTTPException(status_code=404, detail=f"Quality assessment for '{working_set_id}' not found")

    return ContextQualityResponseSchema(
        assessment_id=q.assessment_id,
        working_set_id=q.working_set_id,
        relevance_score=q.relevance_score,
        freshness_score=q.freshness_score,
        completeness_score=q.completeness_score,
        provenance_coverage_score=q.provenance_coverage_score,
        contradiction_visibility_score=q.contradiction_visibility_score,
        redundancy_penalty=q.redundancy_penalty,
        compression_quality_score=q.compression_quality_score,
        budget_efficiency_score=q.budget_efficiency_score,
        latency_score=q.latency_score,
        source_diversity_score=q.source_diversity_score,
        task_alignment_score=q.task_alignment_score,
        safety_coverage_score=q.safety_coverage_score,
        isolation_correctness_score=q.isolation_correctness_score,
        composite_quality=q.composite_quality,
        created_at=q.created_at,
    )


@router.get(
    "/context/working-sets/{working_set_id}/timeline",
    summary="Retrieve audit event timeline for a working set",
)
async def get_context_timeline(working_set_id: str) -> List[Dict[str, Any]]:
    service = WorkingSetService.get_instance()
    return service.get_timeline(working_set_id)
