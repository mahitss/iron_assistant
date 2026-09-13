"""FastAPI application entry point for Kairo."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.agents.router import router as collaboration_router
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
from app.api.routes.devices import router as devices_router
from app.api.routes.evaluation import router as evaluation_router
from app.api.routes.events import router as events_router
from app.api.routes.experience import router as experience_router
from app.api.routes.feedback import router as feedback_router
from app.api.routes.identity import router as identity_router
from app.api.routes.knowledge import router as knowledge_router
from app.api.routes.memory import memory_api_router
from app.api.routes.memory import router as memory_router
from app.api.routes.memory import user_router as user_memory_router
from app.api.routes.multimodal import router as multimodal_router
from app.api.routes.proactive import router as proactive_router
from app.api.routes.projects import router as projects_router
from app.api.routes.security import router as security_router
from app.api.routes.skills import router as skills_router
from app.api.routes.tasks import router as tasks_router
from app.api.routes.voice import router as voice_router
from app.api.routes.web_monitors import router as web_monitors_router
from app.api.routes.world import router as world_router
from app.attention import attention_router
from app.auth.middleware import AuthContextMiddleware
from app.autonomy.router import router as autonomy_router
from app.causal.router import router as causal_router
from app.cognition.router import router as cognition_router
from app.communication import communication_router
from app.config.settings import get_settings
from app.decision.router import router as decision_router
from app.environment.router import router as environment_router
from app.executive_memory.router import router as executive_memory_router
from app.foresight.router import router as foresight_router
from app.discovery import discovery_router, experiments_router
from app.foresight.router import world_model_router
from app.incident_response.router import router as incidents_router
from app.intent import commands_router, intent_router
from app.knowledge_graph import knowledge_graph_router
from app.learning.router import router as learning_router
from app.lifecycle import shutdown_lifecycle, startup_lifecycle
from app.memory_consolidation import memory_consolidation_router
from app.metacognition import metacognition_router
from app.missions.router import router as mission_router
from app.notifications import notifications_router
from app.observability.health import router as health_router
from app.observability.logging import configure_structured_logging
from app.observability.router import router as observability_router
from app.optimization.router import router as optimization_router
from app.orchestration.router import router as orchestration_router
from app.perception.router import router as perception_router
from app.planning.router import router as planning_router
from app.policy import admin_policy_router, governance_router, policy_router
from app.prediction.router import router as prediction_router
from app.propagation.router import router as propagation_router
from app.reasoning import reasoning_router
from app.research.router import router as research_router
from app.resilience.router import recovery_router, router as resilience_router
from app.self_audit.router import router as self_audit_router
from app.simulation.router import router as simulation_router
from app.situational_awareness.router import router as situations_router
from app.state.router import router as state_router
from app.swarm.router import router as swarm_router
from app.verification.router import router as verification_router
from app.native.router import router as native_router

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
    app.include_router(memory_consolidation_router, prefix=settings.API_V1_STR)
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
    app.include_router(devices_router, prefix=settings.API_V1_STR)
    app.include_router(knowledge_router, prefix=settings.API_V1_STR)
    app.include_router(skills_router, prefix=settings.API_V1_STR)
    app.include_router(evaluation_router, prefix=settings.API_V1_STR)
    app.include_router(events_router, prefix=settings.API_V1_STR)
    app.include_router(experience_router, prefix=settings.API_V1_STR)
    app.include_router(feedback_router, prefix=settings.API_V1_STR)
    app.include_router(multimodal_router, prefix=settings.API_V1_STR)
    app.include_router(tasks_router, prefix=settings.API_V1_STR)
    app.include_router(world_router, prefix=settings.API_V1_STR)
    app.include_router(identity_router, prefix=settings.API_V1_STR)
    app.include_router(commands_router, prefix=settings.API_V1_STR)
    app.include_router(intent_router, prefix=settings.API_V1_STR)
    app.include_router(policy_router, prefix=settings.API_V1_STR)
    app.include_router(admin_policy_router, prefix=settings.API_V1_STR)
    app.include_router(governance_router, prefix=settings.API_V1_STR)
    app.include_router(governance_router)
    app.include_router(resilience_router, prefix=settings.API_V1_STR)
    app.include_router(resilience_router)
    app.include_router(recovery_router, prefix=settings.API_V1_STR)
    app.include_router(recovery_router)
    app.include_router(state_router)
    app.include_router(observability_router)
    app.include_router(cognition_router, prefix=settings.API_V1_STR)
    app.include_router(verification_router, prefix=settings.API_V1_STR)
    app.include_router(learning_router, prefix=settings.API_V1_STR)
    app.include_router(collaboration_router, prefix=settings.API_V1_STR)
    app.include_router(autonomy_router, prefix=settings.API_V1_STR)
    app.include_router(perception_router, prefix=settings.API_V1_STR)
    app.include_router(prediction_router, prefix=settings.API_V1_STR)
    app.include_router(communication_router, prefix=settings.API_V1_STR)
    app.include_router(knowledge_graph_router, prefix=settings.API_V1_STR)
    app.include_router(metacognition_router, prefix=settings.API_V1_STR)
    app.include_router(executive_memory_router)
    app.include_router(environment_router)
    app.include_router(causal_router)
    app.include_router(simulation_router)
    app.include_router(decision_router)
    app.include_router(planning_router)
    app.include_router(orchestration_router)
    app.include_router(situations_router)
    app.include_router(incidents_router)
    app.include_router(optimization_router)
    app.include_router(research_router)
    app.include_router(swarm_router)
    app.include_router(foresight_router)
    app.include_router(world_model_router)
    app.include_router(mission_router, prefix=settings.API_V1_STR)
    app.include_router(self_audit_router, prefix=settings.API_V1_STR)
    app.include_router(attention_router, prefix=settings.API_V1_STR)
    app.include_router(reasoning_router, prefix=settings.API_V1_STR)
    app.include_router(discovery_router, prefix=settings.API_V1_STR)
    app.include_router(experiments_router, prefix=settings.API_V1_STR)
    app.include_router(propagation_router, prefix=settings.API_V1_STR)
    app.include_router(propagation_router)
    app.include_router(native_router)

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
