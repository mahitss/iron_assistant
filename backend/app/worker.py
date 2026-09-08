"""Standalone background worker and scheduler process for Kairo.

This process polls due workflows, executes workflow steps, and recovers stale runs.
It uses PostgreSQL row-level locks (FOR UPDATE SKIP LOCKED) and deterministic
idempotency keys so that multiple worker or API instances can run concurrently
without duplicate execution.
"""

import asyncio
import logging
import signal
import sys
from typing import Any

from app.automation.executor import WorkflowExecutor
from app.automation.scheduler import SchedulerService
from app.config.settings import get_settings
from app.db.session import get_sessionmaker
from app.observability.logging import configure_structured_logging

logger = logging.getLogger("kairo.worker")


class KairoWorker:
    """Production background worker for workflow scheduling and execution."""

    def __init__(
        self,
        poll_interval_seconds: float = 5.0,
        stale_recovery_interval_seconds: float = 300.0,
    ) -> None:
        self.settings = get_settings()
        self.poll_interval_seconds = poll_interval_seconds
        self.stale_recovery_interval_seconds = stale_recovery_interval_seconds
        self._stop_event = asyncio.Event()
        self._last_stale_recovery = 0.0

    async def run_once(self, session_factory: Any) -> int:
        """Perform a single polling cycle: claim due workflows and execute them.

        Returns the number of workflow runs processed.
        """
        scheduler = SchedulerService(session_factory=session_factory, settings=self.settings)

        run_ids: list[str] = []
        async with session_factory() as session:
            try:
                run_ids = await scheduler.poll_due_workflows(session)
            except Exception as exc:
                logger.error("Error polling due workflows: %s", exc, exc_info=True)
                return 0

        # Execute claimed runs
        executed_count = 0
        for run_id in run_ids:
            if self._stop_event.is_set():
                logger.info("Stop event set; deferring run %s to next worker cycle.", run_id)
                break
            try:
                logger.info("Worker executing workflow run: %s", run_id)
                async with session_factory() as exec_session:
                    executor = WorkflowExecutor(session=exec_session, settings=self.settings)
                    await executor.execute_run(run_id)
                    executed_count += 1
            except Exception as exc:
                logger.error("Error executing workflow run %s: %s", run_id, exc, exc_info=True)

        return executed_count

    async def recover_stale(self, session_factory: Any) -> int:
        """Run periodic stale run recovery."""
        scheduler = SchedulerService(session_factory=session_factory, settings=self.settings)
        async with session_factory() as session:
            try:
                recovered = await scheduler.recover_stale_runs(session)
                if recovered > 0:
                    logger.info("Worker recovered %d stale workflow runs.", recovered)
                return recovered
            except Exception as exc:
                logger.error("Error during stale workflow recovery: %s", exc)
                return 0

    async def start(self) -> None:
        """Main worker polling loop with graceful shutdown."""
        logger.info(
            "Starting Kairo Worker (Environment: %s, Poll interval: %.1fs)",
            self.settings.ENVIRONMENT.value
            if hasattr(self.settings.ENVIRONMENT, "value")
            else self.settings.ENVIRONMENT,
            self.poll_interval_seconds,
        )

        session_factory = get_sessionmaker()
        if session_factory is None:
            logger.error("Database sessionmaker not initialized. Worker cannot start.")
            return

        loop = asyncio.get_running_loop()

        # Wire graceful shutdown signals where supported (POSIX and Windows)
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, self._handle_signal, sig)
            except NotImplementedError:
                # Windows signal handling fallback
                signal.signal(sig, lambda s, f: self._stop_event.set())

        # Main polling loop
        while not self._stop_event.is_set():
            try:
                # Check for due workflows
                await self.run_once(session_factory)

                # Periodic stale run recovery
                current_time = loop.time()
                if (current_time - self._last_stale_recovery) >= self.stale_recovery_interval_seconds:
                    await self.recover_stale(session_factory)
                    self._last_stale_recovery = current_time

            except Exception as exc:
                logger.critical("Unexpected error in worker loop: %s", exc, exc_info=True)

            # Sleep with cancellation support
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.poll_interval_seconds)
            except TimeoutError:
                pass

        logger.info("Kairo Worker shut down gracefully.")

    def _handle_signal(self, sig: int) -> None:
        logger.info("Received exit signal %s. Initiating graceful worker drain...", sig)
        self._stop_event.set()

    def stop(self) -> None:
        """Trigger worker shutdown."""
        self._stop_event.set()


def main() -> None:
    """CLI entrypoint for standalone worker execution."""
    settings = get_settings()
    if settings.ENVIRONMENT.is_production:
        configure_structured_logging(settings.LOG_LEVEL)
    else:
        logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    worker = KairoWorker()
    try:
        asyncio.run(worker.start())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Worker interrupted by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
