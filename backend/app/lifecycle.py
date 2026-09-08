"""Application startup and shutdown lifecycle hooks, stale state recovery, and resource cleanup."""

import logging

from sqlalchemy import text

from app.config.settings import get_settings
from app.config.validation import validate_environment
from app.db.session import get_engine, get_sessionmaker

logger = logging.getLogger("kairo.lifecycle")


async def startup_lifecycle() -> None:
    """Execute startup procedures, validate environment, and recover stale in-flight state."""
    logger.info("Initializing Kairo application lifecycle...")
    settings = get_settings()

    # 1. Validate environment configuration
    validate_environment(settings)

    # 2. Database stale state recovery
    if settings.DATABASE_URL:
        session_factory = get_sessionmaker()
        if session_factory is not None:
            try:
                async with session_factory() as session:
                    # Stale automation workflow runs recovery
                    await session.execute(
                        text(
                            "UPDATE workflow_runs SET status = 'FAILED', "
                            "error = 'Server restarted while workflow run was active.' "
                            "WHERE status IN ('RUNNING', 'PENDING')"
                        )
                    )
                    # Stale multi-agent tasks recovery
                    await session.execute(
                        text(
                            "UPDATE agent_tasks SET status = 'FAILED', "
                            "error = 'Server restarted while agent task was active.' "
                            "WHERE status IN ('RUNNING', 'PENDING')"
                        )
                    )
                    await session.commit()
                    logger.info(
                        "Recovered and finalized stale workflow runs and agent tasks from prior execution."
                    )
            except Exception as exc:
                logger.warning("Could not complete database stale state recovery on startup: %s", exc)

    # 3. Ensure high-risk capabilities start disabled by default on startup
    settings.KAIRO_COMPUTER_ENABLED = False
    logger.info("Computer control initialized to disabled state on startup.")

    logger.info("Kairo startup lifecycle completed successfully.")


async def shutdown_lifecycle() -> None:
    """Gracefully terminate background workers, active sessions, and database connections."""
    logger.info("Initiating graceful shutdown for Kairo...")

    # 1. Close active browser sessions and Playwright child processes
    try:
        from app.tools.browser.manager import get_browser_manager

        manager = get_browser_manager()
        await manager.close_all()
        logger.info("Closed all active Playwright browser sessions.")
    except Exception as exc:
        logger.debug("Browser manager shutdown skipped or already closed: %s", exc)

    # 2. Close active voice streaming sessions
    try:
        from app.voice.session import VoiceSessionManager

        VoiceSessionManager.clear_all()
        logger.info("Terminated all active voice sessions.")
    except Exception as exc:
        logger.debug("Voice session cleanup skipped: %s", exc)

    # 3. Dispose database connection pool
    try:
        engine = get_engine()
        if engine is not None:
            await engine.dispose()
            logger.info("Disposed SQLAlchemy database engine and connection pool.")
    except Exception as exc:
        logger.debug("Database engine disposal skipped: %s", exc)

    logger.info("Kairo graceful shutdown finished.")
