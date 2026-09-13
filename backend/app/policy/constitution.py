"""Constitutional Reasoning Engine: configurable machine-readable constitution and principles (Task 78)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.policy.governance_schemas import (
    ConstitutionalPrinciple,
    ConstitutionModelSchema,
    PrincipleEvaluationResult,
    PrincipleName,
    PrincipleStrictness,
)

logger = logging.getLogger(__name__)


class ConstitutionalEngine:
    """Evaluates candidate autonomous actions against machine-readable constitutional principles."""

    def __init__(self, initial_constitution: ConstitutionModelSchema | None = None) -> None:
        self.constitution = initial_constitution or self._create_default_constitution()

    def _create_default_constitution(self) -> ConstitutionModelSchema:
        """Create the canonical 11 constitutional principles with calibrated strictness."""
        principles = [
            ConstitutionalPrinciple(
                principle_id="prn_safety",
                name=PrincipleName.SAFETY,
                weight=1.0,
                strictness=PrincipleStrictness.MANDATORY,
                description="Prevent physical, operational, data loss, or systemic infrastructure damage.",
            ),
            ConstitutionalPrinciple(
                principle_id="prn_legality",
                name=PrincipleName.LEGALITY,
                weight=1.0,
                strictness=PrincipleStrictness.MANDATORY,
                description="Comply strictly with applicable laws, contracts, licensing, and terms of service.",
            ),
            ConstitutionalPrinciple(
                principle_id="prn_user_auth",
                name=PrincipleName.USER_AUTHORITY,
                weight=1.0,
                strictness=PrincipleStrictness.MANDATORY,
                description="The human operator is the supreme authority; AI serves verified human intent.",
            ),
            ConstitutionalPrinciple(
                principle_id="prn_transparency",
                name=PrincipleName.TRANSPARENCY,
                weight=0.90,
                strictness=PrincipleStrictness.STRICT,
                description="Autonomous actions must be explainable without deceptive or obfuscated intent.",
            ),
            ConstitutionalPrinciple(
                principle_id="prn_auditability",
                name=PrincipleName.AUDITABILITY,
                weight=0.90,
                strictness=PrincipleStrictness.STRICT,
                description="Every consequential decision and state modification must produce immutable audit logs.",
            ),
            ConstitutionalPrinciple(
                principle_id="prn_reversibility",
                name=PrincipleName.REVERSIBILITY,
                weight=0.95,
                strictness=PrincipleStrictness.MANDATORY,
                description="Destructive or high-risk actions must maintain safe rollback paths or checkpoints.",
            ),
            ConstitutionalPrinciple(
                principle_id="prn_proportionality",
                name=PrincipleName.PROPORTIONALITY,
                weight=0.85,
                strictness=PrincipleStrictness.STRICT,
                description="Resource consumption and operational impact must be proportionate to the objective.",
            ),
            ConstitutionalPrinciple(
                principle_id="prn_privacy",
                name=PrincipleName.PRIVACY,
                weight=1.0,
                strictness=PrincipleStrictness.MANDATORY,
                description="Respect tenant boundaries and prevent unauthorized data exfiltration or leaks.",
            ),
            ConstitutionalPrinciple(
                principle_id="prn_security",
                name=PrincipleName.SECURITY,
                weight=1.0,
                strictness=PrincipleStrictness.MANDATORY,
                description="Defend system integrity; never bypass defense gates or weaken security postures.",
            ),
            ConstitutionalPrinciple(
                principle_id="prn_least_priv",
                name=PrincipleName.LEAST_PRIVILEGE,
                weight=0.90,
                strictness=PrincipleStrictness.STRICT,
                description="Request and exercise only the minimum authority strictly necessary for the task.",
            ),
            ConstitutionalPrinciple(
                principle_id="prn_human_oversight",
                name=PrincipleName.HUMAN_OVERSIGHT,
                weight=1.0,
                strictness=PrincipleStrictness.MANDATORY,
                description="When uncertainty is high or actions are irreversible, defer to human judgment.",
            ),
        ]
        return ConstitutionModelSchema(
            constitution_id=f"const_{uuid.uuid4().hex[:8]}",
            name="Kairo Core Autonomous Constitution",
            version="1.0.0",
            principles=principles,
            is_active=True,
        )

    def get_principle(self, name: PrincipleName) -> ConstitutionalPrinciple | None:
        """Retrieve a principle definition by name."""
        for p in self.constitution.principles:
            if p.name == name and p.enabled:
                return p
        return None

    def update_principle(
        self,
        name: PrincipleName,
        weight: float | None = None,
        strictness: PrincipleStrictness | None = None,
        enabled: bool | None = None,
    ) -> bool:
        """Configure principle weights, strictness, or active status."""
        for p in self.constitution.principles:
            if p.name == name:
                if weight is not None:
                    p.weight = max(0.0, min(1.0, weight))
                if strictness is not None:
                    p.strictness = strictness
                if enabled is not None:
                    p.enabled = enabled
                logger.info("Constitutional principle %s updated: weight=%.2f, strictness=%s", name.value, p.weight, p.strictness.value)
                return True
        return False

    def evaluate_action(
        self,
        action: str,
        resource: str,
        risk_level: str,
        is_irreversible: bool = False,
        is_destructive: bool = False,
        uncertainty_score: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[float, list[PrincipleEvaluationResult], list[str]]:
        """Evaluate candidate action against all active constitutional principles.

        Returns (composite_score, detailed_results, mandatory_violations).
        """
        meta = metadata or {}
        results: list[PrincipleEvaluationResult] = []
        mandatory_violations: list[str] = []
        total_weighted_score = 0.0
        total_weight = 0.0

        for p in self.constitution.principles:
            if not p.enabled:
                continue

            score = 1.0
            findings = "Compliant"
            citation = f"Constitution Principle: {p.name.value}"

            # 1. SAFETY & REVERSIBILITY checks for destructive actions
            if p.name in (PrincipleName.SAFETY, PrincipleName.REVERSIBILITY):
                if is_destructive and is_irreversible:
                    score = 0.0
                    findings = "Destructive action has no reversible rollback path."
                elif is_destructive:
                    score = 0.5
                    findings = "Destructive action requires verified rollback checkpoints."

            # 2. HUMAN_OVERSIGHT check for high uncertainty or irreversible actions
            elif p.name == PrincipleName.HUMAN_OVERSIGHT:
                if uncertainty_score >= 0.70:
                    score = 0.20
                    findings = f"High uncertainty ({uncertainty_score:.2f}) requires human deliberation."
                elif is_irreversible and risk_level in ("R3_HIGH", "R4_CRITICAL"):
                    score = 0.10
                    findings = "Irreversible high-risk operation demands mandatory human confirmation."

            # 3. SECURITY & LEAST_PRIVILEGE checks
            elif p.name == PrincipleName.SECURITY:
                if "disable_security" in action.lower() or "bypass" in action.lower():
                    score = 0.0
                    findings = "Action attempts to disable security or bypass guardrails."
            elif p.name == PrincipleName.LEAST_PRIVILEGE:
                if meta.get("excess_permissions_requested"):
                    score = 0.40
                    findings = "Excess authority requested beyond operational minimum."

            # 4. PROPORTIONALITY check
            elif p.name == PrincipleName.PROPORTIONALITY:
                if meta.get("excessive_resource_use"):
                    score = 0.50
                    findings = "Resource demand is disproportionate to task value."

            # 5. PRIVACY check
            elif p.name == PrincipleName.PRIVACY:
                if meta.get("cross_tenant_access"):
                    score = 0.0
                    findings = "Attempted cross-tenant data boundary traversal."

            is_compliant = score >= 0.70
            if not is_compliant and p.strictness == PrincipleStrictness.MANDATORY:
                if p.name != PrincipleName.HUMAN_OVERSIGHT:
                    mandatory_violations.append(f"{p.name.value}: {findings}")

            results.append(
                PrincipleEvaluationResult(
                    principle=p.name,
                    score=score,
                    compliant=is_compliant,
                    findings=findings,
                    citation=citation,
                )
            )

            total_weighted_score += score * p.weight
            total_weight += p.weight

        composite_score = (total_weighted_score / total_weight) if total_weight > 0 else 1.0
        return round(composite_score, 4), results, mandatory_violations


default_constitutional_engine = ConstitutionalEngine()
