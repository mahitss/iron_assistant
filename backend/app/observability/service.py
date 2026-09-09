"""Central coordinator service for Kairo Unified Observability (Task 38)."""

from typing import Any

from app.observability.anomalies import AnomalyDetector
from app.observability.dashboards import DashboardAggregator
from app.observability.dependencies import DependencyGraphTracker, dependency_tracker
from app.observability.diagnostics import DiagnosticService, diagnostic_service
from app.observability.exporters import TelemetryExporter
from app.observability.health import HealthEvaluator
from app.observability.incidents import IncidentManager, incident_manager
from app.observability.metrics import MetricsCollector, get_metrics_collector
from app.observability.retention import RetentionPolicy
from app.observability.root_cause import RootCauseAnalysisEngine, rca_engine
from app.observability.sampling import TraceSampler
from app.observability.schemas import (
    DiagnosticReport,
    HealthScoreSummary,
    Incident,
    RootCauseAnalysis,
    ServiceMap,
    Trace,
)
from app.observability.tracing import DistributedTracer, tracer


class ObservabilityService:
    """Master coordinator unifying distributed tracing, metrics, incidents, and RCA."""

    def __init__(self) -> None:
        self.tracer: DistributedTracer = tracer
        self.metrics: MetricsCollector = get_metrics_collector()
        self.dependencies: DependencyGraphTracker = dependency_tracker
        self.anomalies: AnomalyDetector = AnomalyDetector()
        self.incidents: IncidentManager = incident_manager
        self.rca: RootCauseAnalysisEngine = rca_engine
        self.diagnostics: DiagnosticService = diagnostic_service
        self.sampler: TraceSampler = TraceSampler()
        self.exporter: TelemetryExporter = TelemetryExporter()
        self.retention: RetentionPolicy = RetentionPolicy()
        self.dashboards: type[DashboardAggregator] = DashboardAggregator

    def get_health_score(
        self,
        db_healthy: bool = True,
        redis_healthy: bool = True,
        error_rate: float = 0.0,
        latency_p95_ms: float = 25.0,
    ) -> HealthScoreSummary:
        """Returns deterministic service health score."""
        return HealthEvaluator.calculate_health_score(
            db_healthy=db_healthy,
            redis_healthy=redis_healthy,
            error_rate=error_rate,
            latency_p95_ms=latency_p95_ms,
        )

    def diagnose_trace(self, trace_id: str) -> DiagnosticReport:
        """Produces plain-English diagnostic summary for a given trace."""
        trace = self.tracer.get_trace(trace_id)
        if not trace:
            raise ValueError(f"Trace '{trace_id}' not found")
        return self.diagnostics.generate_user_diagnostic(trace)

    def perform_rca(self, trace_id: str) -> RootCauseAnalysis:
        """Executes evidence-backed root cause analysis on a given trace."""
        trace = self.tracer.get_trace(trace_id)
        if not trace:
            raise ValueError(f"Trace '{trace_id}' not found")
        return self.rca.analyze_trace(trace)


observability_service = ObservabilityService()
