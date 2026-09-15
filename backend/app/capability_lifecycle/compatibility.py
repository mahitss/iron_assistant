"""Multi-dimensional capability compatibility evaluator (Task 91 Phase 4)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.capability_lifecycle.models import (
    CapabilityMetadata,
    CompatibilityClassification,
    CompatibilityReport,
    generate_cl_id,
    _now_utc,
)
from app.capability_lifecycle.versioning import parse_semver

logger = logging.getLogger("kairo.capability_lifecycle.compatibility")


class CompatibilityEvaluator:
    """Evaluates multi-dimensional compatibility between capability versions or consumers."""

    @classmethod
    def evaluate_compatibility(
        cls,
        source: CapabilityMetadata,
        target: CapabilityMetadata,
        active_consumers: Optional[List[str]] = None,
    ) -> CompatibilityReport:
        """Compares source (baseline) and target (new) capability specifications."""
        cap_id = source.capability_id
        src_v = source.version
        tgt_v = target.version

        migration_reqs: List[str] = []
        affected = list(active_consumers or [])

        # 1. Evaluate SemVer Major Shift
        try:
            s_maj, s_min, _, _ = parse_semver(src_v)
            t_maj, t_min, _, _ = parse_semver(tgt_v)
        except Exception:
            s_maj, s_min, t_maj, t_min = 1, 0, 1, 0

        is_major_break = t_maj > s_maj

        # 2. Evaluate Input Schema Compatibility (JSON Schema / parameters)
        schema_compatible, schema_notes = cls._check_schema_compatibility(
            source.parameters_schema, target.parameters_schema
        )
        migration_reqs.extend(schema_notes)

        # 3. Evaluate Output Schema Compatibility
        output_compatible, output_notes = cls._check_output_compatibility(
            source.output_schema, target.output_schema
        )
        migration_reqs.extend(output_notes)

        # 4. Evaluate Security & Permission Compatibility
        security_compatible, sec_notes = cls._check_security_compatibility(
            source.required_permissions, target.required_permissions
        )
        migration_reqs.extend(sec_notes)

        # 5. Evaluate Resource Profile Compatibility
        resource_compatible, res_notes = cls._check_resource_compatibility(
            source.resource_profile, target.resource_profile
        )
        migration_reqs.extend(res_notes)

        # 6. Contract compatibility composite
        contract_compatible = schema_compatible and output_compatible

        # 7. Synthesize Classification
        if is_major_break or not contract_compatible:
            if schema_compatible:
                classification = CompatibilityClassification.PARTIALLY_COMPATIBLE
                risk = "MEDIUM"
                rec = "CANARY_RECOMMENDED"
            else:
                classification = CompatibilityClassification.INCOMPATIBLE
                risk = "HIGH"
                rec = "MIGRATION_REQUIRED"
        elif not security_compatible:
            classification = CompatibilityClassification.PARTIALLY_COMPATIBLE
            risk = "HIGH"
            rec = "GOVERNANCE_REVIEW_REQUIRED"
        elif source.composite_fingerprint == target.composite_fingerprint:
            classification = CompatibilityClassification.FULLY_COMPATIBLE
            risk = "LOW"
            rec = "PROCEED"
        else:
            # Minor/patch change with backward compatible contract
            classification = CompatibilityClassification.BACKWARD_COMPATIBLE
            risk = "LOW"
            rec = "PROCEED"

        report = CompatibilityReport(
            report_id=generate_cl_id("comp"),
            capability_id=cap_id,
            source_version=src_v,
            target_version=tgt_v,
            classification=classification,
            contract_compatible=contract_compatible,
            schema_compatible=schema_compatible,
            dependency_compatible=True,
            resource_compatible=resource_compatible,
            security_compatible=security_compatible,
            migration_requirements=migration_reqs,
            affected_consumers=affected,
            risk_level=risk,
            recommendation=rec,
        )

        logger.info(
            "Evaluated compatibility for %s [%s -> %s]: %s (Risk: %s)",
            cap_id,
            src_v,
            tgt_v,
            classification.value,
            risk,
        )
        return report

    @staticmethod
    def _check_schema_compatibility(
        s_schema: Dict[str, Any], t_schema: Dict[str, Any]
    ) -> tuple[bool, List[str]]:
        """Checks whether new parameters schema breaks existing callers (e.g. newly required fields)."""
        notes: List[str] = []
        if not s_schema and not t_schema:
            return True, notes

        s_req = set(s_schema.get("required", []))
        t_req = set(t_schema.get("required", []))

        # Adding a new required parameter is a breaking change for existing callers
        new_required = t_req - s_req
        if new_required:
            notes.append(f"Target schema introduces new mandatory parameters: {sorted(new_required)}")
            return False, notes

        # Removing a supported parameter may break callers relying on it
        s_props = set(s_schema.get("properties", {}).keys())
        t_props = set(t_schema.get("properties", {}).keys())
        removed_props = s_props - t_props
        if removed_props:
            notes.append(f"Target schema removed properties: {sorted(removed_props)}")
            return False, notes

        return True, notes

    @staticmethod
    def _check_output_compatibility(
        s_out: Optional[Dict[str, Any]], t_out: Optional[Dict[str, Any]]
    ) -> tuple[bool, List[str]]:
        """Checks if output contract maintains backward compatible structure."""
        notes: List[str] = []
        if not s_out or not t_out:
            return True, notes

        s_props = set(s_out.get("properties", {}).keys())
        t_props = set(t_out.get("properties", {}).keys())
        removed_out = s_props - t_props
        if removed_out:
            notes.append(f"Target output schema removed fields: {sorted(removed_out)}")
            return False, notes

        return True, notes

    @staticmethod
    def _check_security_compatibility(
        s_perms: List[str], t_perms: List[str]
    ) -> tuple[bool, List[str]]:
        """Checks if target version requests privilege escalation."""
        notes: List[str] = []
        escalated = set(t_perms) - set(s_perms)
        if escalated:
            notes.append(f"Target version requests elevated permissions: {sorted(escalated)}")
            return False, notes
        return True, notes

    @staticmethod
    def _check_resource_compatibility(s_res: Any, t_res: Any) -> tuple[bool, List[str]]:
        """Checks if target version increases resource consumption substantially."""
        notes: List[str] = []
        if t_res.memory_mb > (s_res.memory_mb * 2.0):
            notes.append(f"Target memory requirement doubled ({s_res.memory_mb}MB -> {t_res.memory_mb}MB)")
            return False, notes
        if t_res.cpu_cores > (s_res.cpu_cores * 2.0):
            notes.append(f"Target CPU requirement doubled ({s_res.cpu_cores} -> {t_res.cpu_cores} cores)")
            return False, notes
        return True, notes
