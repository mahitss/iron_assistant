from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.routes.automations import router as automations_router
from app.api.routes.chat import router as chat_router
from app.api.routes.memory import router as memory_router
from app.api.routes.memory import user_router as user_memory_router
from app.api.routes.security import router as security_router
from app.api.routes.voice import router as voice_router
from app.core.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown lifecycle."""
    yield
    # Gracefully shut down active browser sessions and Playwright process
    try:
        from app.tools.browser.manager import get_browser_manager
        manager = get_browser_manager()
        await manager.close_all()
    except Exception:
        pass


def create_app() -> FastAPI:
    """Application factory for Kairo backend service."""
    settings = get_settings()

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="Autonomous Personal AI Assistant API",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )


    # Configure CORS
    if settings.ALLOWED_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.ALLOWED_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Register root health endpoint
    app.include_router(health_router)

    app.include_router(chat_router, prefix=settings.API_V1_STR)
    app.include_router(memory_router, prefix=settings.API_V1_STR)
    app.include_router(user_memory_router, prefix=settings.API_V1_STR)
    app.include_router(voice_router, prefix=settings.API_V1_STR)
    app.include_router(automations_router, prefix=settings.API_V1_STR)
    app.include_router(security_router, prefix=settings.API_V1_STR)

    return app



app = create_app()

if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
