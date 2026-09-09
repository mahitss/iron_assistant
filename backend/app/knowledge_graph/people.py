"""Person entities, work attributes, and anti-surveillance & anti-profiling guards."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class SensitiveProfilingError(Exception):
    """Raised when an attempt is made to infer or persist sensitive personal characteristics."""
    pass


class PeopleManager:
    """Manages person entities strictly within professional, authorized work context.

    INVARIANTS 38, 41, 147, 235, 236: Prohibits social surveillance and sensitive profiling.
    """

    FORBIDDEN_ATTRIBUTES = {
        "political_views",
        "religion",
        "sexual_orientation",
        "medical_condition",
        "mental_health",
        "race",
        "ethnicity",
        "disability",
        "financial_standing",
    }

    def __init__(self) -> None:
        # person_id -> dict
        self._people: Dict[str, Dict[str, Any]] = {}

    def register_person(
        self,
        person_id: str,
        name: str,
        organization: Optional[str] = None,
        role: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        attr = attributes or {}
        self._audit_no_profiling(attr)

        record = {
            "person_id": person_id,
            "name": name,
            "organization": organization,
            "role": role,
            "attributes": attr,
        }
        self._people[person_id] = record
        return record

    def get_person(self, person_id: str) -> Optional[Dict[str, Any]]:
        return self._people.get(person_id)

    def _audit_no_profiling(self, data: Dict[str, Any]) -> None:
        for key in data.keys():
            if key.lower() in self.FORBIDDEN_ATTRIBUTES:
                raise SensitiveProfilingError(
                    f"Forbidden attribute '{key}' detected. Kairo strictly prohibits sensitive personal profiling."
                )
