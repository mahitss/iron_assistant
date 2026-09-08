"""FastAPI application entry point for Kairo."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api.middleware import (
    BodySizeLimitMiddleware,
    RateLimitMiddleware,
    RequestIdMiddleware,
    SecurityHeadersMiddleware,
    register_exception_handlers,
)
from app.api.routes.agents import router as agents_router
from app.api.routes.auth import router as auth_router
from app.api.routes.automations import router as automations_router
from app.api.routes.chat import router as chat_router
from app.api.routes.context import router as context_router
from app.api.routes.memory import memory_api_router
from app.api.routes.memory import router as memory_router
from app.api.routes.memory import user_router as user_memory_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.proactive import router as proactive_router
from app.api.routes.projects import router as projects_router
from app.api.routes.security import router as security_router
from app.api.routes.voice import router as voice_router
from app.api.routes.web_monitors import router as web_monitors_router
from app.auth.middleware import AuthContextMiddleware
from app.config.settings import get_settings
from app.lifecycle import shutdown_lifecycle, startup_lifecycle
from app.observability.health import router as health_router
from app.observability.logging import configure_structured_logging

logger = logging.getLogger("kairo.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup, state recovery, and graceful shutdown lifecycle."""
    await startup_lifecycle()
    yield
    await shutdown_lifecycle()


def create_app() -> FastAPI:
    """Application factory for hardened Kairo backend service."""
    settings = get_settings()

    # Configure structured logging in production or if requested
    if settings.ENVIRONMENT.is_production:
        configure_structured_logging(settings.LOG_LEVEL)

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="Autonomous Personal AI Assistant API — Hardened Production Runtime",
        docs_url="/docs" if not settings.ENVIRONMENT.is_production else None,
        redoc_url="/redoc" if not settings.ENVIRONMENT.is_production else None,
        openapi_url="/openapi.json" if not settings.ENVIRONMENT.is_production else None,
        lifespan=lifespan,
    )

    # 1. Register Defensive Security Middlewares (Outer to Inner)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(BodySizeLimitMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(AuthContextMiddleware)

    # 2. Configure Safe CORS
    origins = (
        settings.ALLOWED_ORIGINS if isinstance(settings.ALLOWED_ORIGINS, list) else [settings.ALLOWED_ORIGINS]
    )
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # 3. Register Centralized Exception Handlers
    register_exception_handlers(app)

    # 4. Mount Observability & Health Probes (/health, /health/live, /health/ready, /metrics)
    app.include_router(health_router)

    # 5. Mount Protected Domain API Routers
    app.include_router(auth_router, prefix=settings.API_V1_STR)
    app.include_router(chat_router, prefix=settings.API_V1_STR)
    app.include_router(memory_router, prefix=settings.API_V1_STR)
    app.include_router(memory_api_router, prefix=settings.API_V1_STR)
    app.include_router(user_memory_router, prefix=settings.API_V1_STR)
    app.include_router(projects_router, prefix=settings.API_V1_STR)
    app.include_router(context_router, prefix=settings.API_V1_STR)
    app.include_router(voice_router, prefix=settings.API_V1_STR)
    app.include_router(automations_router, prefix=settings.API_V1_STR)
    app.include_router(security_router, prefix=settings.API_V1_STR)
    app.include_router(proactive_router, prefix=settings.API_V1_STR)
    app.include_router(notifications_router, prefix=settings.API_V1_STR)
    app.include_router(web_monitors_router, prefix=settings.API_V1_STR)
    app.include_router(agents_router, prefix=settings.API_V1_STR)

    # 6. Web Console UI & Static Assets
    frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
    index_file = frontend_dir / "index.html"

    @app.get("/", include_in_schema=False)
    async def serve_root():
        """Serve the Kairo Web Control Center dashboard."""
        if index_file.exists():
            return FileResponse(index_file)
        return {
            "name": "Kairo",
            "version": settings.VERSION,
            "status": "online",
            "docs_url": "/docs",
            "health_url": "/health/live",
        }

    if frontend_dir.exists():
        from fastapi.staticfiles import StaticFiles

        app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG and settings.ENVIRONMENT.is_development,
    )
