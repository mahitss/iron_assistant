"""Data retention policies for traces, logs, metrics, and incidents (Task 38)."""

from datetime import UTC, datetime, timedelta


class RetentionPolicy:
    """Configures retention durations for operational telemetry."""

    def __init__(
        self,
        routine_trace_retention_days: int = 7,
        error_trace_retention_days: int = 30,
        incident_retention_days: int = 90,
        metric_snapshot_retention_days: int = 60,
    ) -> None:
        self.routine_trace_retention_days = routine_trace_retention_days
        self.error_trace_retention_days = error_trace_retention_days
        self.incident_retention_days = incident_retention_days
        self.metric_snapshot_retention_days = metric_snapshot_retention_days

    def is_trace_expired(self, started_at: datetime, has_errors: bool = False) -> bool:
        """Determines if a trace is past its retention cutoff."""
        retention_days = self.error_trace_retention_days if has_errors else self.routine_trace_retention_days
        cutoff = datetime.now(UTC) - timedelta(days=retention_days)
        return started_at < cutoff

    def is_incident_expired(self, created_at: datetime) -> bool:
        """Determines if an incident is past its retention cutoff."""
        cutoff = datetime.now(UTC) - timedelta(days=self.incident_retention_days)
        return created_at < cutoff
