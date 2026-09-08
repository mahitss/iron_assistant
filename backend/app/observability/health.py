"""Health check and metrics endpoints for production observability."""

import logging

from fastapi import APIRouter, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config.settings import get_settings
from app.db.session import get_sessionmaker
from app.models.health import HealthResponse
from app.observability.metrics import get_metrics_collector

logger = logging.getLogger("kairo.observability.health")

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Basic Application Health",
)
async def health() -> HealthResponse:
    """Return basic health status of Kairo application process."""
    settings = get_settings()
    return HealthResponse(
        status="healthy",
        app="Kairo",
        version=settings.VERSION,
        environment=settings.ENVIRONMENT.value
        if hasattr(settings.ENVIRONMENT, "value")
        else str(settings.ENVIRONMENT),
    )


@router.get(
    "/health/live",
    status_code=status.HTTP_200_OK,
    summary="Liveness Probe",
)
async def liveness() -> dict[str, str]:
    """Kubernetes / container liveness probe indicating process is executing."""
    return {"status": "alive"}


@router.get(
    "/health/ready",
    summary="Readiness Probe",
)
async def readiness() -> JSONResponse:
    """Readiness probe verifying PostgreSQL and Redis connections without exposing credentials."""
    settings = get_settings()
    db_status = "inactive"
    redis_status = "inactive"
    is_ready = True
    details: dict[str, str] = {}

    # 1. Test Relational Database
    if settings.DATABASE_URL:
        try:
            session_factory = get_sessionmaker()
            if session_factory is not None:
                async with session_factory() as session:
                    await session.execute(text("SELECT 1"))
                db_status = "connected"
            else:
                db_status = "uninitialized"
                is_ready = False
        except Exception as exc:
            logger.warning("Database readiness probe failed: %s", exc)
            db_status = "failed"
            is_ready = False
    else:
        db_status = "skipped_not_configured"

    details["database"] = db_status

    # 2. Test Redis
    if settings.REDIS_URL:
        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(
                settings.REDIS_URL,
                socket_connect_timeout=1.0,
                socket_timeout=1.0,
            )
            await r.ping()
            await r.aclose()
            redis_status = "connected"
        except Exception as exc:
            logger.warning("Redis readiness probe failed: %s", exc)
            redis_status = "failed"
            is_ready = False
    else:
        redis_status = "skipped_not_configured"

    details["redis"] = redis_status

    http_status = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=http_status,
        content={
            "status": "ready" if is_ready else "degraded",
            "components": details,
        },
    )


@router.get(
    "/metrics",
    summary="Prometheus Metrics",
)
async def metrics() -> Response:
    """Return application metrics in Prometheus text exposition format."""
    collector = get_metrics_collector()
    text_content = collector.generate_prometheus_text()
    return Response(content=text_content, media_type="text/plain; version=0.0.4")


@router.get(
    "/health/version",
    summary="Safe Version Metadata",
)
async def version() -> dict[str, str]:
    """Return safe deployment version metadata without exposing environment variables or secrets."""
    settings = get_settings()
    env_str = (
        settings.ENVIRONMENT.value if hasattr(settings.ENVIRONMENT, "value") else str(settings.ENVIRONMENT)
    )
    return {
        "version": settings.VERSION,
        "git_sha": settings.GIT_SHA,
        "build_timestamp": settings.BUILD_TIMESTAMP or "unknown",
        "environment": env_str,
    }
