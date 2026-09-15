"""Deterministic cryptographic fingerprinting for capability contracts, implementations, and dependencies (Task 91 Phase 15)."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

from app.capability_lifecycle.models import CapabilityDependency, CapabilityMetadata


def _canonical_json_bytes(data: Any) -> bytes:
    """Produces sorted, deterministic JSON byte representation for hashing."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


class CapabilityFingerprinter:
    """Calculates deterministic SHA-256 fingerprints to detect tampering, drift, and schema changes."""

    @staticmethod
    def compute_contract_fingerprint(
        parameters_schema: Dict[str, Any],
        output_schema: Optional[Dict[str, Any]] = None,
        required_permissions: Optional[List[str]] = None,
        timeout_seconds: float = 30.0,
    ) -> str:
        """Computes cryptographic digest of the API contract, arguments, outputs, and permissions."""
        contract_payload = {
            "parameters_schema": parameters_schema,
            "output_schema": output_schema or {},
            "required_permissions": sorted(required_permissions or []),
            "timeout_seconds": round(timeout_seconds, 2),
        }
        return f"cfp_{hashlib.sha256(_canonical_json_bytes(contract_payload)).hexdigest()[:24]}"

    @staticmethod
    def compute_implementation_fingerprint(
        implementation_descriptor: Dict[str, Any] | str,
        source_revision: str = "HEAD",
    ) -> str:
        """Computes cryptographic digest of the implementation bytecode, path, or descriptor."""
        if isinstance(implementation_descriptor, str):
            raw = implementation_descriptor.encode("utf-8")
        else:
            raw = _canonical_json_bytes(implementation_descriptor)
        hasher = hashlib.sha256(raw)
        hasher.update(source_revision.encode("utf-8"))
        return f"ifp_{hasher.hexdigest()[:24]}"

    @staticmethod
    def compute_dependency_fingerprint(dependencies: List[CapabilityDependency]) -> str:
        """Computes cryptographic digest of declared dependency set and version constraints."""
        dep_items = sorted(
            [f"{d.dependency_type.value}:{d.target_id}:{d.version_constraint}" for d in dependencies]
        )
        return f"dfp_{hashlib.sha256(_canonical_json_bytes(dep_items)).hexdigest()[:24]}"

    @classmethod
    def compute_composite_fingerprint(
        cls,
        capability_id: str,
        version: str,
        contract_fp: str,
        impl_fp: str,
        dep_fp: str,
    ) -> str:
        """Computes unified capability identity fingerprint."""
        composite_payload = {
            "capability_id": capability_id,
            "version": version,
            "contract_fp": contract_fp,
            "impl_fp": impl_fp,
            "dep_fp": dep_fp,
        }
        return f"cmp_{hashlib.sha256(_canonical_json_bytes(composite_payload)).hexdigest()[:24]}"

    @classmethod
    def fingerprint_capability(cls, capability: CapabilityMetadata, implementation_hint: Any = None) -> CapabilityMetadata:
        """Applies all cryptographic fingerprints onto the capability metadata."""
        c_fp = cls.compute_contract_fingerprint(
            parameters_schema=capability.parameters_schema,
            output_schema=capability.output_schema,
            required_permissions=capability.required_permissions,
            timeout_seconds=capability.resource_profile.timeout_seconds,
        )
        i_fp = cls.compute_implementation_fingerprint(
            implementation_descriptor=implementation_hint or capability.owner_source,
            source_revision=capability.provenance.get("commit_sha", "HEAD"),
        )
        d_fp = cls.compute_dependency_fingerprint(capability.dependencies)
        comp_fp = cls.compute_composite_fingerprint(
            capability_id=capability.capability_id,
            version=capability.version,
            contract_fp=c_fp,
            impl_fp=i_fp,
            dep_fp=d_fp,
        )

        capability.contract_fingerprint = c_fp
        capability.implementation_fingerprint = i_fp
        capability.composite_fingerprint = comp_fp
        return capability

    @classmethod
    def verify_fingerprint_integrity(
        cls,
        capability: CapabilityMetadata,
        implementation_hint: Any = None,
    ) -> Tuple[bool, Optional[str]]:
        """Validates that capability metadata has not been tampered with or modified post-activation."""
        expected_c = cls.compute_contract_fingerprint(
            parameters_schema=capability.parameters_schema,
            output_schema=capability.output_schema,
            required_permissions=capability.required_permissions,
            timeout_seconds=capability.resource_profile.timeout_seconds,
        )
        if expected_c != capability.contract_fingerprint:
            return False, f"Contract fingerprint mismatch: expected {expected_c}, got {capability.contract_fingerprint}"

        expected_d = cls.compute_dependency_fingerprint(capability.dependencies)
        expected_comp = cls.compute_composite_fingerprint(
            capability_id=capability.capability_id,
            version=capability.version,
            contract_fp=expected_c,
            impl_fp=capability.implementation_fingerprint,
            dep_fp=expected_d,
        )
        if expected_comp != capability.composite_fingerprint:
            return False, f"Composite identity fingerprint drift detected: expected {expected_comp}, got {capability.composite_fingerprint}"

        return True, None
