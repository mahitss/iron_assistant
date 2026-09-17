"""Comprehensive test suite for Kairo Autonomous Self-Model & Capability Awareness (Task 101)."""

from __future__ import annotations

import pytest
from click.testing import CliRunner
from fastapi.testclient import TestClient

from app.main import create_app
from app.security.emergency_stop import get_emergency_stop_service
from app.self_model.bridges import SelfModelBridges
from app.self_model.cli import self_model_cli
from app.self_model.delta_engine import SelfModelDeltaEngine
from app.self_model.limitation_engine import LimitationReasoningEngine
from app.self_model.query_engine import SelfModelQueryEngine
from app.self_model.schemas import (
    AutonomyMode,
    CapabilityAwarenessItem,
    CapabilityReadinessState,
    ChangeType,
    DependencyAwarenessItem,
    FreshnessState,
    LimitationItem,
    ReadinessDimensionScore,
    ResourceAwareness,
    SecurityGovernanceAwareness,
    SelfModelAnswers,
    SelfModelSnapshot,
    SelfStateChange,
    ToolAwarenessItem,
    UncertaintyItem,
)
from app.self_model.service import SelfModelService, get_self_model_service


@pytest.fixture(autouse=True)
def clean_emergency_stop():
    """Ensure EmergencyStop is reset before each test."""
    e_stop = get_emergency_stop_service()
    e_stop.reset()
    yield
    e_stop.reset()


def test_schema_and_domain_invariants():
    """Verifies that capability readiness states, freshness, and autonomy modes are well-defined."""
    assert CapabilityReadinessState.READY.value == "READY"
    assert CapabilityReadinessState.DEGRADED.value == "DEGRADED"
    assert CapabilityReadinessState.BLOCKED.value == "BLOCKED"
    assert AutonomyMode.BOUNDED_AUTONOMY.value == "BOUNDED_AUTONOMY"
    assert AutonomyMode.EMERGENCY_STOP.value == "EMERGENCY_STOP"
    assert FreshnessState.CURRENT.value == "CURRENT"


def test_resolution_of_all_15_canonical_questions():
    """Verifies that SelfModelQueryEngine deterministically resolves all 15 introspective questions."""
    capabilities = {
        "code_execution": CapabilityAwarenessItem(
            capability_id="code_execution",
            name="Code Execution Engine",
            version="1.0.0",
            lifecycle_state="ACTIVE",
            readiness_state=CapabilityReadinessState.READY,
            health_state="HEALTHY",
            reliability_score=0.99,
            consecutive_failures=0,
            evidence=["Lifecycle: ACTIVE"],
        ),
        "web_research": CapabilityAwarenessItem(
            capability_id="web_research",
            name="Web Research Engine",
            version="1.0.0",
            lifecycle_state="ACTIVE",
            readiness_state=CapabilityReadinessState.DEGRADED,
            health_state="DEGRADED",
            reliability_score=0.75,
            consecutive_failures=1,
            evidence=["Browser latency degraded"],
        ),
        "external_deploy": CapabilityAwarenessItem(
            capability_id="external_deploy",
            name="External Deployment",
            version="1.0.0",
            lifecycle_state="BLOCKED",
            readiness_state=CapabilityReadinessState.BLOCKED,
            health_state="UNHEALTHY",
            reliability_score=0.40,
            consecutive_failures=3,
            evidence=["Human approval missing"],
        ),
    }

    tools = {
        "calculator": ToolAwarenessItem(
            tool_name="calculator",
            execution_class="PYTHON",
            requires_approval=False,
            is_available=True,
        ),
        "shell_exec": ToolAwarenessItem(
            tool_name="shell_exec",
            execution_class="PYTHON",
            requires_approval=True,
            is_available=False,
            restrictions=["Requires approval"],
        ),
    }

    resources = ResourceAwareness(
        saturation_pct=0.35,
        saturation_state="HEALTHY",
        degradation_tier="FULL_FIDELITY",
    )

    security = SecurityGovernanceAwareness(
        emergency_stop_active=False,
        autonomy_mode=AutonomyMode.BOUNDED_AUTONOMY,
        approval_required_actions=["destructive_shell", "computer_control"],
        active_policies=["default_least_privilege"],
    )

    dependencies = {
        "postgresql": DependencyAwarenessItem(
            dependency_name="postgresql",
            dependency_type="DATABASE",
            status="AVAILABLE",
        ),
        "browser_engine": DependencyAwarenessItem(
            dependency_name="browser_engine",
            dependency_type="AUTOMATION",
            status="DEGRADED",
        ),
    }

    limitations = [
        LimitationItem(
            limitation_id="lim_test_1",
            subject="EXTERNAL_NETWORK",
            description="Cannot execute unrestricted outbound egress",
            reason="Security boundary",
            evidence="Policy config",
        )
    ]

    uncertainties = [
        UncertaintyItem(
            uncertainty_id="unc_test_1",
            subject="BROWSER_LATENCY",
            reason="Playwright driver response latency is erratic",
            evidence="Response telemetry",
        )
    ]

    answers = SelfModelQueryEngine.resolve_answers(
        capabilities=capabilities,
        tools=tools,
        resources=resources,
        security=security,
        dependencies=dependencies,
        limitations=limitations,
        uncertainties=uncertainties,
    )

    # Question 1: What capabilities do I have?
    assert "code_execution" in answers.q1_capabilities
    assert "web_research" in answers.q1_capabilities

    # Question 2: Which versions are available?
    assert answers.q2_versions["code_execution"] == "1.0.0"

    # Question 3: Which capabilities are actually ready?
    assert answers.q3_ready_capabilities == ["code_execution"]

    # Question 4: Which are degraded?
    assert answers.q4_degraded_capabilities == ["web_research"]

    # Question 5: Which are temporarily unavailable?
    assert answers.q5_temporarily_unavailable == ["external_deploy"]

    # Question 6: What resources do I currently have?
    assert answers.q6_current_resources.saturation_pct == 0.35

    # Question 7: What tools can I use?
    assert answers.q7_usable_tools == ["calculator"]

    # Question 8: What access is currently authorized?
    assert "STANDARD_SAFE_READ_WRITE" in answers.q8_authorized_access

    # Question 9: Which actions require approval?
    assert "destructive_shell" in answers.q9_actions_requiring_approval

    # Question 10: Which dependencies are failing?
    assert any("browser_engine" in d for d in answers.q10_failing_dependencies)

    # Question 11: Which capabilities have recently failed?
    assert "web_research" in answers.q11_recently_failed_capabilities
    assert "external_deploy" in answers.q11_recently_failed_capabilities

    # Question 12: How reliable is each capability?
    assert answers.q12_capability_reliability["code_execution"] == 0.99
    assert answers.q12_capability_reliability["web_research"] == 0.75

    # Question 13: What has changed since the last check?
    assert isinstance(answers.q13_changes_since_last_check, list)

    # Question 14: What do I know about my own limitations?
    assert len(answers.q14_limitations) == 1
    assert answers.q14_limitations[0].subject == "EXTERNAL_NETWORK"

    # Question 15: What am I uncertain about?
    assert len(answers.q15_uncertainties) == 1
    assert answers.q15_uncertainties[0].subject == "BROWSER_LATENCY"


def test_limitation_and_uncertainty_engines():
    """Verifies that limitations and uncertainties are grounded in empirical telemetry."""
    capabilities = {
        "reasoning": CapabilityAwarenessItem(
            capability_id="reasoning",
            name="Reasoning Engine",
            version="1.0.0",
            lifecycle_state="ACTIVE",
            readiness_state=CapabilityReadinessState.READY,
            health_state="HEALTHY",
            consecutive_failures=0,
        ),
        "browser": CapabilityAwarenessItem(
            capability_id="browser",
            name="Browser Automation",
            version="1.0.0",
            lifecycle_state="ACTIVE",
            readiness_state=CapabilityReadinessState.DEGRADED,
            health_state="DEGRADED",
            consecutive_failures=2,
            last_failure_reason="Timeout waiting for DOM selector",
            evidence=["Consecutive failures: 2"],
        ),
    }

    dependencies = {
        "redis": DependencyAwarenessItem(
            dependency_name="redis",
            dependency_type="CACHE",
            status="UNAVAILABLE",
            evidence="Connection refused on port 6379",
        )
    }

    security = SecurityGovernanceAwareness(
        emergency_stop_active=False,
        autonomy_mode=AutonomyMode.BOUNDED_AUTONOMY,
        approval_required_actions=["modify_root_keys"],
    )

    resources = ResourceAwareness(
        saturation_pct=0.91,
        degradation_tier="AGGRESSIVE_THROTTLE",
    )

    limitations = LimitationReasoningEngine.evaluate_limitations(
        capabilities, dependencies, security, resources
    )
    subjects = [l.subject for l in limitations]

    assert "DEPENDENCY_REDIS" in subjects
    assert "CAPABILITY_BROWSER" in subjects
    assert "RESOURCE_ECONOMY" in subjects
    assert "GOVERNANCE_BOUNDARIES" in subjects

    uncertainties = LimitationReasoningEngine.evaluate_uncertainties(
        capabilities, dependencies, security
    )
    unc_subjects = [u.subject for u in uncertainties]
    assert "CAPABILITY_BROWSER" in unc_subjects


def test_state_diffing_delta_engine():
    """Verifies that state diffs detect transitions between snapshots."""
    snap1 = SelfModelSnapshot(
        snapshot_id="snap_1",
        autonomy_mode=AutonomyMode.BOUNDED_AUTONOMY,
        emergency_stop_state=False,
        capabilities={
            "code_exec": CapabilityAwarenessItem(
                capability_id="code_exec",
                name="Code Exec",
                version="1.0.0",
                lifecycle_state="ACTIVE",
                readiness_state=CapabilityReadinessState.READY,
                health_state="HEALTHY",
                evidence=["All checks pass"],
            )
        },
        resources=ResourceAwareness(degradation_tier="FULL_FIDELITY"),
    )

    snap2 = SelfModelSnapshot(
        snapshot_id="snap_2",
        autonomy_mode=AutonomyMode.EMERGENCY_STOP,
        emergency_stop_state=True,
        capabilities={
            "code_exec": CapabilityAwarenessItem(
                capability_id="code_exec",
                name="Code Exec",
                version="1.0.0",
                lifecycle_state="BLOCKED",
                readiness_state=CapabilityReadinessState.BLOCKED,
                health_state="HEALTHY",
                evidence=["EmergencyStop active"],
            )
        },
        resources=ResourceAwareness(degradation_tier="EMERGENCY_MINIMAL"),
    )

    delta = SelfModelDeltaEngine.compute_delta(snap1, snap2)
    change_types = [c.change_type for c in delta.changes]

    assert ChangeType.CAPABILITY_STATE_CHANGED in change_types
    assert ChangeType.EMERGENCY_STOP_CHANGED in change_types
    assert ChangeType.AUTONOMY_STATE_CHANGED in change_types
    assert ChangeType.RESOURCE_STATE_CHANGED in change_types


def test_emergency_stop_fail_closed_behavior():
    """Verifies that activating EmergencyStop immediately sets capabilities to BLOCKED."""
    e_stop = get_emergency_stop_service()
    service = SelfModelService()

    # Before emergency stop: normal reconciliation
    snap_before = service.reconcile()
    assert not snap_before.emergency_stop_state
    assert snap_before.autonomy_mode == AutonomyMode.BOUNDED_AUTONOMY

    # Activate emergency stop
    e_stop.trigger(reason="Test fail-closed behavior")

    snap_after = service.reconcile()
    assert snap_after.emergency_stop_state
    assert snap_after.autonomy_mode == AutonomyMode.EMERGENCY_STOP

    for cap_id, cap in snap_after.capabilities.items():
        assert cap.readiness_state == CapabilityReadinessState.BLOCKED

    # Read-only query cannot run
    assert not service.can_capability_run("code_execution")


def test_grounding_verification():
    """Verifies grounding audit detects when an impossible claim is made."""
    service = SelfModelService()
    snap = service.reconcile()

    # Clean state should be 100% grounded
    grounding = service.verify_grounding()
    assert grounding.is_grounded
    assert grounding.verdict == "GROUNDED"

    # Inject an invariant violation (EmergencyStop active while claiming READY)
    snap.emergency_stop_state = True
    for cap in snap.capabilities.values():
        cap.readiness_state = CapabilityReadinessState.READY

    grounding_bad = service.verify_grounding()
    assert not grounding_bad.is_grounded
    assert len(grounding_bad.violations) > 0


def test_fastapi_rest_endpoints():
    """Verifies that all FastAPI REST endpoints respond correctly."""
    app = create_app()
    client = TestClient(app)

    # 1. Snapshot
    res = client.get("/api/v1/self-model/snapshot")
    assert res.status_code == 200
    data = res.json()
    assert "snapshot_id" in data
    assert "autonomy_mode" in data

    # 2. Reconcile pass
    res_rec = client.post("/api/v1/self-model/reconcile")
    assert res_rec.status_code == 200
    assert res_rec.json()["snapshot_id"] != ""

    # 3. Answers to 15 questions
    res_ans = client.get("/api/v1/self-model/answers")
    assert res_ans.status_code == 200
    ans_data = res_ans.json()
    assert "q1_capabilities" in ans_data
    assert "q15_uncertainties" in ans_data

    # 4. Capabilities
    res_caps = client.get("/api/v1/self-model/capabilities")
    assert res_caps.status_code == 200

    # 5. Limitations
    res_lims = client.get("/api/v1/self-model/limitations")
    assert res_lims.status_code == 200
    assert isinstance(res_lims.json(), list)

    # 6. Uncertainties
    res_uncs = client.get("/api/v1/self-model/uncertainties")
    assert res_uncs.status_code == 200
    assert isinstance(res_uncs.json(), list)

    # 7. Deltas
    res_deltas = client.get("/api/v1/self-model/deltas")
    assert res_deltas.status_code == 200

    # 8. Grounding audit
    res_audit = client.get("/api/v1/self-model/verify-grounding")
    assert res_audit.status_code == 200
    assert "is_grounded" in res_audit.json()

    # 9. Summary
    res_sum = client.get("/api/v1/self-model/summary")
    assert res_sum.status_code == 200
    assert "ready_capabilities" in res_sum.json()


def test_cli_commands():
    """Verifies that the Click CLI commands execute properly."""
    runner = CliRunner()

    res_status = runner.invoke(self_model_cli, ["status"])
    assert res_status.exit_code == 0
    assert "KAIRO SELF-MODEL STATUS" in res_status.output

    res_caps = runner.invoke(self_model_cli, ["capabilities"])
    assert res_caps.exit_code == 0
    assert "CAPABILITY ID" in res_caps.output

    res_lims = runner.invoke(self_model_cli, ["limitations"])
    assert res_lims.exit_code == 0
    assert "ACTIVE SELF-LIMITATIONS" in res_lims.output

    res_uncs = runner.invoke(self_model_cli, ["uncertainties"])
    assert res_uncs.exit_code == 0
    assert "EPISTEMIC UNCERTAINTIES" in res_uncs.output

    res_ans = runner.invoke(self_model_cli, ["answers"])
    assert res_ans.exit_code == 0
    assert "15 CANONICAL INTROSPECTIVE ANSWERS" in res_ans.output

    res_rec = runner.invoke(self_model_cli, ["reconcile"])
    assert res_rec.exit_code == 0
    assert "Reconciliation pass complete" in res_rec.output
