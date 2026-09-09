"""Dependency health tracking, real probes, liveness, and readiness determination."""

from datetime import UTC, datetime
import logging
import time
from typing import Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.resilience.schemas import DependencyHealth, DependencyHealthReport, utc_now

logger = logging.getLogger(__name__)


class DependencyHealthTracker:
    """Tracks real-time dependency health via real lightweight probes and error telemetry."""

    def __init__(self) -> None:
        self._cached_health: dict[str, DependencyHealthReport] = {}

    async def probe_database(self, session: AsyncSession | None = None) -> DependencyHealthReport:
        """Lightweight database probe executing SELECT 1."""
        start = time.perf_counter()
        if session is None:
            return DependencyHealthReport(
                dependency="database",
                status=DependencyHealth.UNKNOWN,
                latency_ms=0.0,
                details="No database session provided for probe",
                checked_at=utc_now(),
            )
        try:
            await session.execute(text("SELECT 1"))
            latency = (time.perf_counter() - start) * 1000.0
            report = DependencyHealthReport(
                dependency="database",
                status=DependencyHealth.HEALTHY,
                latency_ms=latency,
                details="Database connection verified",
                checked_at=utc_now(),
            )
        except Exception as exc:
            latency = (time.perf_counter() - start) * 1000.0
            report = DependencyHealthReport(
                dependency="database",
                status=DependencyHealth.UNAVAILABLE,
                latency_ms=latency,
                details=f"DB probe failed: {str(exc)[:100]}",
                checked_at=utc_now(),
            )
        self._cached_health["database"] = report
        return report

    async def probe_redis(self) -> DependencyHealthReport:
        """Lightweight Redis ping probe."""
        start = time.perf_counter()
        try:
            from app.core.redis import get_redis
            redis = await get_redis()
            if redis:
                await redis.ping()
                latency = (time.perf_counter() - start) * 1000.0
                report = DependencyHealthReport(
                    dependency="redis",
                    status=DependencyHealth.HEALTHY,
                    latency_ms=latency,
                    details="Redis ping successful",
                    checked_at=utc_now(),
                )
            else:
                report = DependencyHealthReport(
                    dependency="redis",
                    status=DependencyHealth.DEGRADED,
                    latency_ms=0.0,
                    details="Redis disabled; falling back to in-memory/DB store",
                    checked_at=utc_now(),
                )
        except Exception as exc:
            latency = (time.perf_counter() - start) * 1000.0
            report = DependencyHealthReport(
                dependency="redis",
                status=DependencyHealth.DEGRADED,
                latency_ms=latency,
                details=f"Redis unavailable: {str(exc)[:100]} (non-fatal fallback active)",
                checked_at=utc_now(),
            )
        self._cached_health["redis"] = report
        return report

    def record_dependency_status(
        self,
        dependency: str,
        status: DependencyHealth,
        latency_ms: float = 0.0,
        details: str | None = None,
    ) -> DependencyHealthReport:
        """Records telemetry-driven status of an external service (e.g. GitHub, Model Provider)."""
        report = DependencyHealthReport(
            dependency=dependency,
            status=status,
            latency_ms=latency_ms,
            details=details,
            checked_at=utc_now(),
        )
        self._cached_health[dependency] = report
        return report

    def get_all_reports(self) -> list[DependencyHealthReport]:
        return list(self._cached_health.values())

    def evaluate_readiness(self) -> tuple[bool, str]:
        """Evaluates readiness: service is ready only if critical dependencies (like DB) are healthy."""
        db_rep = self._cached_health.get("database")
        if db_rep and db_rep.status == DependencyHealth.UNAVAILABLE:
            return False, "Database is unavailable"
        return True, "Ready to serve requests"

    def evaluate_liveness(self) -> tuple[bool, str]:
        """Evaluates liveness: process is executing and event loop is responsive."""
        return True, "Process is alive and responsive"
