"""Capability matching, requirement extraction, and multi-factor explainable scoring (Task 59)."""

from __future__ import annotations

import logging
from typing import Any

from app.orchestration.capability_registry import CapabilityRegistry, default_capability_registry
from app.orchestration.safety import sanitize_orchestration_directive
from app.orchestration.schemas import (
    CapabilityDefinition,
    CapabilityStatus,
    MatchingScore,
    ProviderType,
    RiskSeverity,
    TaskCapabilityRequirement,
)

logger = logging.getLogger(__name__)


class CapabilityMatcher:
    """Matches task capability requirements against registered capabilities and evaluates multi-factor suitability."""

    def __init__(self, capability_registry: CapabilityRegistry | None = None) -> None:
        self._registry = capability_registry or default_capability_registry

    def extract_task_requirements(
        self,
        task: dict[str, Any],
        default_environment: str = "development",
    ) -> TaskCapabilityRequirement:
        """Extract and sanitize capability requirements from a task dictionary."""
        task_id = str(task.get("task_id", task.get("id", "task_unknown")))
        title = sanitize_orchestration_directive(str(task.get("title", task.get("name", ""))))
        env = str(task.get("environment", default_environment)).strip().lower()

        raw_caps = task.get("required_capabilities", task.get("capabilities", []))
        if isinstance(raw_caps, str):
            raw_caps = [raw_caps]

        # Sanitize capabilities list
        capabilities = [sanitize_orchestration_directive(str(c)) for c in raw_caps if str(c).strip()]

        # If no explicit capability declared, attempt inference from task action/name if standard
        if not capabilities and title:
            lowered = title.lower()
            if "deploy" in lowered:
                capabilities.append("deploy_service")
            elif "test" in lowered:
                capabilities.append("run_tests")
            elif "sql" in lowered or "database" in lowered:
                capabilities.append("execute_sql")
            elif "backup" in lowered:
                capabilities.append("create_backup")
            elif "search" in lowered:
                capabilities.append("web_search")
            elif "calculate" in lowered:
                capabilities.append("calculate")

        resources = task.get("required_resources", [])
        permissions = task.get("required_permissions", [])
        verifications = task.get("verification_criteria", task.get("acceptance_criteria", []))
        is_irreversible = bool(task.get("is_irreversible", False))
        priority = int(task.get("priority", 1))

        return TaskCapabilityRequirement(
            task_id=task_id,
            title=title,
            required_capabilities=capabilities,
            required_resources=resources,
            required_permissions=permissions,
            environment=env,
            verification_criteria=verifications,
            is_irreversible=is_irreversible,
            priority=priority,
        )

    def score_candidate(
        self,
        requirement: TaskCapabilityRequirement,
        candidate: CapabilityDefinition,
        granted_permissions: set[str] | None = None,
        historical_stats: dict[str, Any] | None = None,
    ) -> MatchingScore:
        """Evaluate a candidate capability provider against task requirements."""
        granted = granted_permissions or set()

        # Determine provider type
        p_name = candidate.provider
        if p_name.startswith("Tool:"):
            p_type = ProviderType.TOOL
        elif p_name.startswith("Agent:"):
            p_type = ProviderType.AGENT
        elif p_name.startswith("Service:") or p_name.startswith("Kairo"):
            p_type = ProviderType.SERVICE
        else:
            p_type = ProviderType.TOOL

        # 1. Environment compatibility
        env_compat = requirement.environment.lower() in candidate.supported_environments

        # 2. Authorization check: Capability != Authorization
        missing_perms = [
            perm for perm in candidate.required_permissions
            if perm not in granted
        ]
        # Also check task-level required permissions
        for perm in requirement.required_permissions:
            if perm not in granted and perm not in missing_perms:
                missing_perms.append(perm)

        is_authorized = len(missing_perms) == 0

        # 3. Status check: UNKNOWN != AVAILABLE
        is_available = candidate.status == CapabilityStatus.AVAILABLE

        # 4. Multi-factor scoring
        # Reliability (0.0 to 1.0)
        rel_score = candidate.reliability
        if historical_stats and "success_rate" in historical_stats:
            # Blend verified historical rate without overriding hard zero
            hist_rate = float(historical_stats["success_rate"])
            rel_score = (rel_score * 0.5) + (hist_rate * 0.5)

        # Cost score (inverse linear scale)
        cost = candidate.cost_estimate
        cost_score = max(0.0, 1.0 - (cost / 10.0))

        # Latency score
        latency = candidate.latency_ms
        latency_score = max(0.0, 1.0 - (latency / 5000.0))

        # Risk score
        risk_multipliers = {
            RiskSeverity.LOW: 1.0,
            RiskSeverity.MEDIUM: 0.75,
            RiskSeverity.HIGH: 0.4,
            RiskSeverity.CRITICAL: 0.1,
        }
        risk_score = risk_multipliers.get(candidate.risk_level, 0.5)

        # Strict gating: if not compatible with environment or not available, score is 0.0
        if not env_compat or not is_available:
            overall = 0.0
        elif not is_authorized:
            # Capability exists but unauthorized -> overall is zeroed for execution
            overall = 0.0
        else:
            overall = (
                (rel_score * 0.40)
                + (risk_score * 0.25)
                + (latency_score * 0.20)
                + (cost_score * 0.15)
            )

        # Rationale string
        rationale_parts = []
        if not env_compat:
            rationale_parts.append(f"Incompatible environment: requires '{requirement.environment}', supports {candidate.supported_environments}")
        if not is_authorized:
            rationale_parts.append(f"Missing required authorization: {missing_perms}")
        if not is_available:
            rationale_parts.append(f"Provider status is {candidate.status.value}")
        if env_compat and is_authorized and is_available:
            rationale_parts.append(
                f"Candidate matched (reliability={rel_score:.2f}, risk={candidate.risk_level.value}, cost={cost_score:.2f})"
            )

        return MatchingScore(
            provider_name=candidate.provider,
            provider_type=p_type,
            capability_id=candidate.capability_id,
            overall_score=round(overall, 4),
            capability_match_score=1.0,
            environment_compatibility=env_compat,
            reliability_score=round(rel_score, 4),
            cost_score=round(cost_score, 4),
            latency_score=round(latency_score, 4),
            risk_score=round(risk_score, 4),
            is_authorized=is_authorized,
            missing_permissions=missing_perms,
            rationale="; ".join(rationale_parts),
        )

    def rank_candidates(
        self,
        requirement: TaskCapabilityRequirement,
        granted_permissions: set[str] | None = None,
        historical_stats_map: dict[str, dict[str, Any]] | None = None,
    ) -> list[MatchingScore]:
        """Find and rank all candidate capabilities for a given requirement."""
        scores: list[MatchingScore] = []
        hist_map = historical_stats_map or {}

        for cap_name in requirement.required_capabilities:
            candidates = self._registry.find_candidates(
                capability_name=cap_name,
                environment=requirement.environment,
                allow_degraded=True,
            )
            for cand in candidates:
                cand_hist = hist_map.get(cand.provider, {})
                score = self.score_candidate(
                    requirement=requirement,
                    candidate=cand,
                    granted_permissions=granted_permissions,
                    historical_stats=cand_hist,
                )
                scores.append(score)

        # Sort descending: authorized and compatible first, then highest overall score
        scores.sort(key=lambda s: (s.is_authorized, s.environment_compatibility, s.overall_score), reverse=True)
        return scores


capability_matcher = CapabilityMatcher()
