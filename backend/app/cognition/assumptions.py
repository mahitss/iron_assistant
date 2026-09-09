"""Assumption tracking and validation for Kairo Cognitive Planning (Task 41)."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
import uuid
from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class AssumptionCriticality(str, Enum):
    """Impact level if assumption is invalid."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AssumptionValidationStatus(str, Enum):
    """Validation status of an assumption."""

    UNVALIDATED = "UNVALIDATED"
    VALID = "VALID"
    INVALID = "INVALID"
    INDETERMINATE = "INDETERMINATE"


class PlanAssumption(BaseModel):
    """An explicit assumption relied upon by one or more steps in a plan."""

    model_config = ConfigDict(extra="ignore")

    assumption_id: str = Field(default_factory=lambda: f"asmp_{uuid.uuid4().hex[:10]}")
    plan_id: str
    statement: str = Field(..., min_length=5, description="Clear factual statement assumed true")
    criticality: AssumptionCriticality = Field(default=AssumptionCriticality.MEDIUM)
    validation_method: str = Field(default="STATE_CHECK", description="STATE_CHECK, TOOL_QUERY, API_PING, USER_CONFIRM")
    status: AssumptionValidationStatus = Field(default=AssumptionValidationStatus.UNVALIDATED)
    evidence: str | None = Field(default=None, description="Observed evidence verifying or refuting assumption")
    validated_at: datetime | None = Field(default=None)

    def mark_validated(self, is_valid: bool, evidence: str) -> None:
        """Update assumption status with observed evidence."""
        self.status = AssumptionValidationStatus.VALID if is_valid else AssumptionValidationStatus.INVALID
        self.evidence = evidence
        self.validated_at = utc_now()


class AssumptionValidator:
    """Validates plan assumptions against reality/world state before step execution."""

    @staticmethod
    def validate_assumptions(
        assumptions: list[PlanAssumption],
        current_state: dict[str, Any],
    ) -> tuple[bool, list[PlanAssumption]]:
        """Validate list of assumptions against known state. Returns (all_valid, failed_assumptions)."""
        failed: list[PlanAssumption] = []
        for asmp in assumptions:
            # Example state validation: inspect if target resource/env is marked available
            statement_lower = asmp.statement.lower()
            if "staging" in statement_lower and current_state.get("staging_available") is False:
                asmp.mark_validated(False, "Staging environment is reported offline in current world state.")
                failed.append(asmp)
            elif "database" in statement_lower and current_state.get("database_ready") is False:
                asmp.mark_validated(False, "Database connection is unready in current health probe.")
                failed.append(asmp)
            elif asmp.status == AssumptionValidationStatus.INVALID:
                failed.append(asmp)
            else:
                asmp.mark_validated(True, "Consistent with current authoritative state.")

        all_valid = len(failed) == 0
        return all_valid, failed
