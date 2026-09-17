"""Limitation and Uncertainty Reasoning Engine (Task 101).

Computes empirical, evidence-backed limitations and epistemic uncertainties.
Strictly eliminates generic fake humility or fictional self-awareness.
"""

from __future__ import annotations

import uuid
from typing import Dict, List

from app.self_model.schemas import (
    CapabilityAwarenessItem,
    CapabilityReadinessState,
    DependencyAwarenessItem,
    LimitationItem,
    ResourceAwareness,
    SecurityGovernanceAwareness,
    UncertaintyItem,
)


class LimitationReasoningEngine:
    """Evaluates telemetry boundaries to produce grounded limitations and uncertainties."""

    @classmethod
    def evaluate_limitations(
        cls,
        capabilities: Dict[str, CapabilityAwarenessItem],
        dependencies: Dict[str, DependencyAwarenessItem],
        security: SecurityGovernanceAwareness,
        resources: ResourceAwareness,
    ) -> List[LimitationItem]:
        """Derives factual, evidence-backed boundaries."""
        limitations: List[LimitationItem] = []

        # 1. Emergency Stop limitation
        if security.emergency_stop_active:
            limitations.append(
                LimitationItem(
                    limitation_id=f"lim_estop_{uuid.uuid4().hex[:6]}",
                    subject="EMERGENCY_STOP",
                    description="Kairo cannot execute external actions, computer control, or destructive operations.",
                    reason="EmergencyStop kill-switch is actively engaged.",
                    evidence=security.emergency_stop_reason or "EmergencyStop active flag",
                    is_hard_limit=True,
                )
            )

        # 2. Dependency outages
        for dep_name, dep in dependencies.items():
            if dep.status in ("UNAVAILABLE", "DEGRADED"):
                limitations.append(
                    LimitationItem(
                        limitation_id=f"lim_dep_{dep_name}",
                        subject=f"DEPENDENCY_{dep_name.upper()}",
                        description=f"Services relying on {dep_name} are restricted or unavailable.",
                        reason=f"Dependency '{dep_name}' status is {dep.status}.",
                        evidence=dep.evidence,
                        is_hard_limit=dep.status == "UNAVAILABLE",
                    )
                )

        # 3. Capability degradation or failures
        for cap_id, cap in capabilities.items():
            if cap.readiness_state in (CapabilityReadinessState.DEGRADED, CapabilityReadinessState.FAILED, CapabilityReadinessState.BLOCKED):
                reason_detail = cap.last_failure_reason or f"Readiness is {cap.readiness_state.value}"
                limitations.append(
                    LimitationItem(
                        limitation_id=f"lim_cap_{cap_id}",
                        subject=f"CAPABILITY_{cap_id.upper()}",
                        description=f"Capability '{cap.name}' cannot operate at full fidelity.",
                        reason=reason_detail,
                        evidence="; ".join(cap.evidence),
                        is_hard_limit=cap.readiness_state in (CapabilityReadinessState.FAILED, CapabilityReadinessState.BLOCKED),
                    )
                )

        # 4. Resource throttling
        if resources.saturation_pct >= 0.85:
            limitations.append(
                LimitationItem(
                    limitation_id="lim_res_saturation",
                    subject="RESOURCE_ECONOMY",
                    description="High cognitive and resource saturation limits background throughput.",
                    reason=f"Aggregate capacity saturation reached {round(resources.saturation_pct * 100, 1)}%.",
                    evidence=f"Active degradation tier: {resources.degradation_tier}",
                    is_hard_limit=resources.saturation_pct >= 0.95,
                )
            )

        # 5. Governance & Approval boundaries
        if security.approval_required_actions:
            limitations.append(
                LimitationItem(
                    limitation_id="lim_gov_approvals",
                    subject="GOVERNANCE_BOUNDARIES",
                    description=f"Actions [{', '.join(security.approval_required_actions)}] strictly require human approval.",
                    reason="Fail-closed security policy prevents autonomous privilege escalation.",
                    evidence="ApprovalRegistry and SecurityCenter policies",
                    is_hard_limit=True,
                )
            )

        return limitations

    @classmethod
    def evaluate_uncertainties(
        cls,
        capabilities: Dict[str, CapabilityAwarenessItem],
        dependencies: Dict[str, DependencyAwarenessItem],
        security: SecurityGovernanceAwareness,
    ) -> List[UncertaintyItem]:
        """Identifies epistemic uncertainties requiring revalidation or probe evidence."""
        uncertainties: List[UncertaintyItem] = []

        # 1. Capabilities with consecutive failures or degraded state
        for cap_id, cap in capabilities.items():
            if cap.consecutive_failures > 0 and cap.readiness_state != CapabilityReadinessState.FAILED:
                uncertainties.append(
                    UncertaintyItem(
                        uncertainty_id=f"unc_cap_{cap_id}",
                        subject=f"CAPABILITY_{cap_id.upper()}",
                        reason=f"Intermittent failures ({cap.consecutive_failures}) without permanent outage classification.",
                        evidence=f"Last failure reason: {cap.last_failure_reason or 'Transient error'}",
                        affected_capabilities=[cap_id],
                        revalidation_policy="PROBE_ON_NEXT_INVOCATION",
                    )
                )

        # 2. Dependencies with UNKNOWN or unverified state
        for dep_name, dep in dependencies.items():
            if dep.status == "UNKNOWN":
                uncertainties.append(
                    UncertaintyItem(
                        uncertainty_id=f"unc_dep_{dep_name}",
                        subject=f"DEPENDENCY_{dep_name.upper()}",
                        reason=f"Dependency '{dep_name}' health has not been empirically probed.",
                        evidence="Telemetry absence",
                        affected_capabilities=dep.affected_capabilities,
                        revalidation_policy="IMMEDIATE_PING",
                    )
                )

        # 3. Post-EmergencyStop clearing revalidation
        if not security.emergency_stop_active and getattr(security, "_just_cleared", False):
            uncertainties.append(
                UncertaintyItem(
                    uncertainty_id="unc_estop_cleared",
                    subject="SYSTEM_REVALIDATION",
                    reason="EmergencyStop was cleared; operational capability readiness must be individually re-verified.",
                    evidence="Kill-switch state transition",
                    affected_capabilities=list(capabilities.keys()),
                    revalidation_policy="RECONCILIATION_RUN",
                )
            )

        return uncertainties
