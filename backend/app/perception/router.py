"""FastAPI REST API Router for Kairo Perception & Environmental Awareness Engine (Task 46)."""

from __future__ import annotations

import logging
from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.perception.context import PerceptionContext
from app.perception.events import EventAuthenticityError, InvalidEventError, PayloadSizeExceededError
from app.perception.privacy import CrossTenantPerceptionError, PrivacyViolationError
from app.perception.schemas import (
    ChangeEventResponse,
    HealthMetricsResponse,
    ObservationResponse,
    PerceptionEventIngestRequest,
    PerceptionEventIngestResponse,
    PerceptionSourceRegisterRequest,
    PerceptionSourceResponse,
    SituationResponse,
    SnapshotCreateRequest,
    SnapshotResponse,
)
from app.perception.service import PerceptionService
from app.perception.sources import (
    PerceptionSourceScope,
    PrivacyLevel,
    SourceStatus,
    SourceType,
    SourceUnauthorizedError,
)

logger = logging.getLogger("kairo.perception.router")

router = APIRouter(prefix="/perception", tags=["perception"])

_global_perception_service: Optional[PerceptionService] = None


def get_perception_service() -> PerceptionService:
    global _global_perception_service
    if _global_perception_service is None:
        _global_perception_service = PerceptionService()
    return _global_perception_service


def get_current_user_id(x_user_id: Annotated[Optional[str], Header()] = None) -> str:
    return x_user_id or "default_user"


def get_current_project_id(x_project_id: Annotated[Optional[str], Header()] = None) -> str:
    return x_project_id or "default_project"


# ==================================================
# Sources Endpoints (Spec 2-5, 170)
# ==================================================

@router.post("/sources", response_model=PerceptionSourceResponse, status_code=status.HTTP_201_CREATED)
async def register_perception_source(
    req: PerceptionSourceRegisterRequest,
    service: Annotated[PerceptionService, Depends(get_perception_service)],
) -> PerceptionSourceResponse:
    """Register an authorized perception source with explicit scope boundaries."""
    try:
        stype = SourceType(req.type.upper())
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid source type: {req.type}")

    try:
        plevel = PrivacyLevel(req.privacy_level.upper())
    except ValueError:
        plevel = PrivacyLevel.INTERNAL

    scope = PerceptionSourceScope(
        allowed_users=req.allowed_users,
        allowed_projects=req.allowed_projects,
        allowed_devices=req.allowed_devices,
        allowed_directories=req.allowed_directories,
        allowed_domains=req.allowed_domains,
        require_explicit_consent=req.require_explicit_consent,
    )

    source = service.sources.register_source(
        source_type=stype,
        name=req.name,
        scope=scope,
        capabilities=req.capabilities,
        reliability=req.reliability,
        privacy_level=plevel,
    )

    return PerceptionSourceResponse(
        source_id=source.source_id,
        type=source.type.value,
        name=source.name,
        capabilities=source.capabilities,
        reliability=source.reliability,
        status=source.status.value,
        privacy_level=source.privacy_level.value,
        last_seen=source.last_seen.isoformat(),
        scope={
            "allowed_users": source.scope.allowed_users,
            "allowed_projects": source.scope.allowed_projects,
            "allowed_devices": source.scope.allowed_devices,
            "allowed_directories": source.scope.allowed_directories,
            "allowed_domains": source.scope.allowed_domains,
        },
    )


@router.get("/sources", response_model=List[PerceptionSourceResponse])
async def list_perception_sources(
    service: Annotated[PerceptionService, Depends(get_perception_service)],
    user_id: Annotated[str, Depends(get_current_user_id)],
    project_id: Annotated[str, Depends(get_current_project_id)],
    type: Optional[str] = Query(None),
) -> List[PerceptionSourceResponse]:
    stype = SourceType(type.upper()) if type else None
    sources = service.sources.list_sources(source_type=stype, user_id=user_id, project_id=project_id)
    return [
        PerceptionSourceResponse(
            source_id=s.source_id,
            type=s.type.value,
            name=s.name,
            capabilities=s.capabilities,
            reliability=s.reliability,
            status=s.status.value,
            privacy_level=s.privacy_level.value,
            last_seen=s.last_seen.isoformat(),
            scope={
                "allowed_users": s.scope.allowed_users,
                "allowed_projects": s.scope.allowed_projects,
                "allowed_devices": s.scope.allowed_devices,
                "allowed_directories": s.scope.allowed_directories,
                "allowed_domains": s.scope.allowed_domains,
            },
        )
        for s in sources
    ]


@router.post("/sources/{source_id}/disable")
async def disable_perception_source(
    source_id: str,
    service: Annotated[PerceptionService, Depends(get_perception_service)],
) -> Dict[str, Any]:
    """Disable source and immediately mark observations UNKNOWN/UNAVAILABLE (Spec 170)."""
    ok = service.sources.disable_source(source_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Source {source_id} not found")
    return {"status": "DISABLED", "source_id": source_id, "message": "Source disabled; state marked unavailable."}


# ==================================================
# Event Ingestion & Observations (Spec 6-17)
# ==================================================

@router.post("/sources/{source_id}/events", response_model=PerceptionEventIngestResponse)
async def ingest_perception_event(
    source_id: str,
    req: PerceptionEventIngestRequest,
    service: Annotated[PerceptionService, Depends(get_perception_service)],
    user_id: Annotated[str, Depends(get_current_user_id)],
    project_id: Annotated[str, Depends(get_current_project_id)],
) -> PerceptionEventIngestResponse:
    """Ingest raw environmental event through normalization, deduplication, and live awareness."""
    try:
        raw_dict = {
            "event_type": req.event_type,
            "subject": req.subject,
            "payload": req.payload,
            "sequence": req.sequence,
            "correlation_id": req.correlation_id,
            "causation_id": req.causation_id,
            "expected_status": req.expected_status,
        }

        res = service.ingest_event(
            raw_event=raw_dict,
            source_id=source_id,
            user_id=user_id,
            project_id=project_id,
            environment=req.environment,
            has_explicit_user_consent=req.has_explicit_user_consent,
        )

        if not res:
            # Duplicate or stale event safely ignored
            return PerceptionEventIngestResponse(
                status="DEDUPLICATED_OR_STALE",
                source_id=source_id,
                subject=req.subject,
                event_type=req.event_type,
                confidence=1.0,
                latency_ms=0.0,
                change_detected=False,
                anomaly_detected=False,
            )

        obs, change, anomaly = res
        return PerceptionEventIngestResponse(
            status="PROCESSED",
            observation_id=obs.observation_id,
            event_id=raw_dict.get("event_id"),
            source_id=obs.source_id,
            subject=obs.subject,
            event_type=obs.event_type.value,
            confidence=obs.confidence,
            latency_ms=obs.latency_ms,
            change_detected=change is not None,
            change_id=change.change_id if change else None,
            significance=change.significance.value if change else None,
            anomaly_detected=anomaly is not None,
            anomaly_id=anomaly.anomaly_id if anomaly else None,
        )

    except SourceUnauthorizedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except PrivacyViolationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except CrossTenantPerceptionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except (InvalidEventError, PayloadSizeExceededError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/observations", response_model=List[ObservationResponse])
async def list_recent_observations(
    service: Annotated[PerceptionService, Depends(get_perception_service)],
    user_id: Annotated[str, Depends(get_current_user_id)],
    project_id: Annotated[str, Depends(get_current_project_id)],
    environment: str = "DEVELOPMENT",
    max_items: int = Query(20, ge=1, le=100),
) -> List[ObservationResponse]:
    ctx = PerceptionContext(user_id=user_id, project_id=project_id, environment=environment)
    ranked = service.get_relevant_observations(ctx, max_items=max_items)
    return [
        ObservationResponse(
            observation_id=o.observation_id,
            source_id=o.source_id,
            source_type=o.source_type.value,
            subject=o.subject,
            event_type=o.event_type.value,
            payload_reference=o.payload_reference,
            observed_at=o.observed_at.isoformat(),
            received_at=o.received_at.isoformat(),
            age_seconds=o.age_seconds,
            latency_ms=o.latency_ms,
            confidence=o.confidence,
            correlation_id=o.correlation_id,
            scope=o.scope,
            data=o.data,
        )
        for o in ranked
    ]


# ==================================================
# Changes, Snapshots, & Situational Awareness (Spec 31-35, 79-88, 100-106)
# ==================================================

@router.get("/changes", response_model=List[ChangeEventResponse])
async def list_recent_changes(
    service: Annotated[PerceptionService, Depends(get_perception_service)],
) -> List[ChangeEventResponse]:
    changes = []
    for obs_list in service._observations_by_subject.values():
        if obs_list:
            o = obs_list[-1]
            chg = service.change_detector.detect_change(o)
            if chg:
                changes.append(chg)
    return [
        ChangeEventResponse(
            change_id=c.change_id,
            subject=c.subject,
            change_type=c.change_type.value,
            significance=c.significance.value,
            environment=c.environment,
            before=c.before,
            after=c.after,
            timestamp=c.timestamp.isoformat(),
        )
        for c in changes
    ]


@router.post("/snapshots", response_model=SnapshotResponse, status_code=status.HTTP_201_CREATED)
async def capture_snapshot(
    req: SnapshotCreateRequest,
    service: Annotated[PerceptionService, Depends(get_perception_service)],
) -> SnapshotResponse:
    snap = service.snapshot_manager.create_snapshot(
        environment=req.environment,
        is_atomic=req.is_atomic,
        missing_sources=req.missing_sources,
    )
    return SnapshotResponse(
        snapshot_id=snap.snapshot_id,
        version=snap.version,
        environment=snap.environment,
        timestamp=snap.timestamp.isoformat(),
        devices=snap.devices,
        apps=snap.apps,
        services=snap.services,
        repositories=snap.repositories,
        deployments=snap.deployments,
        tasks=snap.tasks,
        agents=snap.agents,
        is_atomic=snap.is_atomic,
        missing_sources=snap.missing_sources,
    )


@router.get("/snapshots/latest", response_model=SnapshotResponse)
async def get_latest_snapshot(
    service: Annotated[PerceptionService, Depends(get_perception_service)],
    environment: str = "DEVELOPMENT",
) -> SnapshotResponse:
    snap = service.snapshot_manager.get_latest_snapshot(environment)
    if not snap:
        snap = service.snapshot_manager.create_snapshot(environment=environment)
    return SnapshotResponse(
        snapshot_id=snap.snapshot_id,
        version=snap.version,
        environment=snap.environment,
        timestamp=snap.timestamp.isoformat(),
        devices=snap.devices,
        apps=snap.apps,
        services=snap.services,
        repositories=snap.repositories,
        deployments=snap.deployments,
        tasks=snap.tasks,
        agents=snap.agents,
        is_atomic=snap.is_atomic,
        missing_sources=snap.missing_sources,
    )


@router.get("/situation", response_model=SituationResponse)
async def get_live_situation(
    service: Annotated[PerceptionService, Depends(get_perception_service)],
    environment: str = "DEVELOPMENT",
) -> SituationResponse:
    sit = service.get_live_situation(environment=environment)
    return SituationResponse(
        situation_id=sit.situation_id,
        version=sit.version,
        scope=sit.scope,
        summary=sit.summary,
        observed_facts=sit.observed_facts,
        inferences=sit.inferences,
        changes=sit.changes,
        anomalies=sit.anomalies,
        active_tasks=sit.active_tasks,
        risks=sit.risks,
        uncertainties=sit.uncertainties,
        timestamp=sit.timestamp.isoformat(),
    )


@router.get("/health", response_model=HealthMetricsResponse)
async def get_perception_health(
    service: Annotated[PerceptionService, Depends(get_perception_service)],
) -> HealthMetricsResponse:
    m = service.metrics
    return HealthMetricsResponse(
        events_received=m.events_received,
        events_processed=m.events_processed,
        events_deduplicated=m.events_deduplicated,
        events_dropped=m.events_dropped,
        stale_events_rejected=m.stale_events_rejected,
        out_of_order_events=m.out_of_order_events,
        changes_detected=m.changes_detected,
        anomalies_detected=m.anomalies_detected,
        avg_latency_ms=m.avg_latency_ms,
        last_event_at=m.last_event_at.isoformat() if m.last_event_at else None,
    )
