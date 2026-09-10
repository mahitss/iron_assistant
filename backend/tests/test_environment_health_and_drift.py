"""Unit tests for Health Modeling, Uncertainty, and Multi-type Drift Detection (Task 54)."""

from app.environment.configurations import ConfigurationManager
from app.environment.deployments import DeploymentModelManager
from app.environment.drift import DriftDetector
from app.environment.health import HealthManager
from app.environment.schemas import (
    DriftSeverity,
    DriftType,
    HealthEvidence,
    HealthStatus,
)
from app.environment.services import ServiceModelManager


def test_missing_telemetry_defaults_to_unknown():
    """Prompt #95, #200: Missing telemetry means UNKNOWN, never HEALTHY."""
    record = HealthManager.aggregate_node_health(node_id="svc_unknown", evidences=[])
    assert record.status == HealthStatus.UNKNOWN
    assert "No telemetry or dependency evidence available" in record.reason

    service_record = ServiceModelManager.evaluate_service_health(service_id="svc_untested", evidence=[])
    assert service_record.status == HealthStatus.UNKNOWN


def test_evidence_backed_health_evaluation():
    """Prompt #21, #22, #93, #94: Health evaluates concrete metrics against thresholds."""
    # 1. Critical error rate leads to UNHEALTHY
    err_evidence = HealthEvidence(
        metric_name="error_rate",
        observed_value=0.25,  # 25% errors
        threshold=0.10,
        source="prometheus",
    )
    rec_unhealthy = HealthManager.aggregate_node_health(node_id="svc_api", evidences=[err_evidence])
    assert rec_unhealthy.status == HealthStatus.UNHEALTHY
    assert "High error rate" in rec_unhealthy.reason

    # 2. Elevated latency leads to DEGRADED
    lat_evidence = HealthEvidence(
        metric_name="latency_p99",
        observed_value=1800,  # 1.8s latency
        threshold=1000,
        source="datadog",
    )
    rec_degraded = HealthManager.aggregate_node_health(node_id="svc_api", evidences=[lat_evidence])
    assert rec_degraded.status == HealthStatus.DEGRADED

    # 3. Nominal telemetry leads to HEALTHY
    ok_evidence = HealthEvidence(
        metric_name="error_rate",
        observed_value=0.001,
        threshold=0.05,
        source="prometheus",
    )
    rec_healthy = HealthManager.aggregate_node_health(node_id="svc_api", evidences=[ok_evidence])
    assert rec_healthy.status == HealthStatus.HEALTHY


def test_dependency_health_propagation():
    """Upstream UNHEALTHY dependency degrades downstream service health."""
    ok_evidence = [HealthEvidence(metric_name="error_rate", observed_value=0.0, source="prom")]
    rec = HealthManager.aggregate_node_health(
        node_id="svc_frontend",
        evidences=ok_evidence,
        dependency_healths=[HealthStatus.UNHEALTHY],
    )
    assert rec.status == HealthStatus.DEGRADED
    assert "Upstream dependency is UNHEALTHY" in rec.reason


def test_configuration_drift_detection():
    """Prompt #54, #136: Configuration drift compares expected and actual parameters."""
    config_node = ConfigurationManager.create_configuration_node(
        config_id="app_cfg",
        name="production_flags",
        parameters={"rate_limit": 500, "debug_mode": False, "timeout_seconds": 30},
    )

    expected = {"rate_limit": 1000, "debug_mode": False, "timeout_seconds": 30}
    drift = ConfigurationManager.detect_configuration_drift(config_node, expected)

    assert drift is not None
    assert drift.drift_type == DriftType.CONFIGURATION
    assert "rate_limit" in drift.expected["drifted_keys"]
    assert drift.expected["expected_values"]["rate_limit"] == 1000
    assert drift.actual["actual_values"]["rate_limit"] == 500


def test_deployment_version_drift():
    """Prompt #138, #203: Deployment drift checks desired vs actual deployed version."""
    dep_node = DeploymentModelManager.create_deployment_node(
        deployment_id="dep_01",
        service_id="svc_auth",
        desired_version="2.4.0",
        actual_version="2.3.9",
        environment="PRODUCTION",
    )
    drift = DeploymentModelManager.detect_deployment_drift(dep_node)

    assert drift is not None
    assert drift.drift_type == DriftType.DEPLOYMENT
    assert drift.severity == DriftSeverity.HIGH  # Production deployment drift is elevated
    assert drift.expected["version"] == "2.4.0"
    assert drift.actual["version"] == "2.3.9"


def test_security_drift_elevated_severity():
    """Prompt #135: Security drift receives elevated priority (CRITICAL)."""
    drift = DriftDetector.create_drift_record(
        resource_id="sec_tls_cert",
        drift_type=DriftType.SECURITY,
        expected={"cipher_suite": "TLS_AES_256_GCM_SHA384", "min_tls_version": "1.3"},
        actual={"cipher_suite": "TLS_RSA_WITH_AES_128_CBC_SHA", "min_tls_version": "1.0"},
    )
    assert drift.severity == DriftSeverity.CRITICAL
