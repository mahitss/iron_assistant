"""Health check endpoint definition."""

from fastapi import APIRouter, status
from app.core.config import get_settings
from app.models.health import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Service Health Check",
    description="Returns the health status, application name, version, and running environment.",
)
async def health_check() -> HealthResponse:
    """Return health status of the Kairo service."""
    settings = get_settings()
    return HealthResponse(
        status="healthy",
        app="Kairo",
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
    )
