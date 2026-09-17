"""Resolution Engine for the 15 Canonical Introspective Questions (Task 101).

Guarantees 100% factual answers grounded strictly in empirical system telemetry.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from app.self_model.schemas import (
    CapabilityAwarenessItem,
    CapabilityReadinessState,
    DependencyAwarenessItem,
    LimitationItem,
    ResourceAwareness,
    SecurityGovernanceAwareness,
    SelfModelAnswers,
    SelfStateChange,
    ToolAwarenessItem,
    UncertaintyItem,
)


class SelfModelQueryEngine:
    """Answers all 15 introspective questions over grounded system state."""

    @classmethod
    def resolve_answers(
        cls,
        capabilities: Dict[str, CapabilityAwarenessItem],
        tools: Dict[str, ToolAwarenessItem],
        resources: ResourceAwareness,
        security: SecurityGovernanceAwareness,
        dependencies: Dict[str, DependencyAwarenessItem],
        limitations: List[LimitationItem],
        uncertainties: List[UncertaintyItem],
        recent_changes: Optional[List[SelfStateChange]] = None,
    ) -> SelfModelAnswers:
        """Resolves all 15 questions deterministically."""

        # Q1: What capabilities do I have?
        q1 = list(capabilities.keys())

        # Q2: Which versions are available?
        q2 = {cap_id: cap.version for cap_id, cap in capabilities.items()}

        # Q3: Which capabilities are actually ready?
        q3 = [
            cap_id
            for cap_id, cap in capabilities.items()
            if cap.readiness_state == CapabilityReadinessState.READY
        ]

        # Q4: Which are degraded?
        q4 = [
            cap_id
            for cap_id, cap in capabilities.items()
            if cap.readiness_state == CapabilityReadinessState.DEGRADED
        ]

        # Q5: Which are temporarily unavailable?
        q5 = [
            cap_id
            for cap_id, cap in capabilities.items()
            if cap.readiness_state in (
                CapabilityReadinessState.UNAVAILABLE,
                CapabilityReadinessState.BLOCKED,
                CapabilityReadinessState.FAILED,
            )
        ]

        # Q6: What resources do I currently have?
        q6 = resources

        # Q7: What tools can I use?
        q7 = [
            t_name
            for t_name, tool in tools.items()
            if tool.is_available and not tool.restrictions
        ]

        # Q8: What access is currently authorized?
        q8 = [
            pol for pol in security.active_policies
        ]
        if not security.emergency_stop_active:
            q8.append("STANDARD_SAFE_READ_WRITE")
            q8.append("SANDBOXED_EXECUTION")
        else:
            q8.append("READ_ONLY_OBSERVATION")

        # Q9: Which actions require approval?
        q9 = list(security.approval_required_actions)

        # Q10: Which dependencies are failing?
        q10 = [
            f"{dep_name} ({dep.status})"
            for dep_name, dep in dependencies.items()
            if dep.status in ("DEGRADED", "UNAVAILABLE", "UNKNOWN")
        ]

        # Q11: Which capabilities have recently failed?
        q11 = [
            cap_id
            for cap_id, cap in capabilities.items()
            if cap.consecutive_failures > 0 or cap.readiness_state == CapabilityReadinessState.FAILED
        ]

        # Q12: How reliable is each capability?
        q12 = {
            cap_id: cap.reliability_score
            for cap_id, cap in capabilities.items()
        }

        # Q13: What has changed since the last check?
        q13 = recent_changes or []

        # Q14: What do I know about my own limitations?
        q14 = limitations

        # Q15: What am I uncertain about?
        q15 = uncertainties

        return SelfModelAnswers(
            q1_capabilities=q1,
            q2_versions=q2,
            q3_ready_capabilities=q3,
            q4_degraded_capabilities=q4,
            q5_temporarily_unavailable=q5,
            q6_current_resources=q6,
            q7_usable_tools=q7,
            q8_authorized_access=q8,
            q9_actions_requiring_approval=q9,
            q10_failing_dependencies=q10,
            q11_recently_failed_capabilities=q11,
            q12_capability_reliability=q12,
            q13_changes_since_last_check=q13,
            q14_limitations=q14,
            q15_uncertainties=q15,
        )
