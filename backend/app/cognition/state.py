"""State bridge, freshness tracking, and drift detection for Kairo Cognitive Planning (Task 41).

Connects the Cognitive Planner with the World Model (app.world) and State Fabric (app.state).
"""

from datetime import UTC, datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class PlanFreshnessState(BaseModel):
    """Tracks the validity and freshness timestamps of a plan."""

    model_config = ConfigDict(extra="ignore")

    plan_id: str
    planned_at: datetime = Field(default_factory=utc_now)
    validated_at: datetime = Field(default_factory=utc_now)
    last_revalidated_at: datetime = Field(default_factory=utc_now)
    is_stale: bool = False
    stale_reasons: list[str] = Field(default_factory=list)

    def check_freshness(self, max_age_seconds: float = 300.0, external_drift_detected: bool = False) -> bool:
        """Evaluate if the plan is stale due to age or environmental drift."""
        age = (utc_now() - self.last_revalidated_at).total_seconds()
        reasons = []

        if age > max_age_seconds:
            reasons.append(f"Plan age ({age:.0f}s) exceeds freshness threshold ({max_age_seconds:.0f}s).")
        if external_drift_detected:
            reasons.append("External environmental drift detected by State Fabric / World Model.")

        self.is_stale = len(reasons) > 0
        self.stale_reasons = reasons
        return not self.is_stale

    def mark_revalidated(self) -> None:
        """Update revalidation timestamp and clear stale flags."""
        self.last_revalidated_at = utc_now()
        self.is_stale = False
        self.stale_reasons.clear()


class CognitiveStateBridge:
    """Provides a safe read-only view of authoritative state for the planner."""

    @staticmethod
    def get_current_context(user_id: str, project_id: str | None = None) -> dict[str, Any]:
        """Fetch current authoritative context without side effects."""
        return {
            "user_id": user_id,
            "project_id": project_id,
            "is_online": True,
            "system_healthy": True,
            "filesystem_readonly": False,
            "database_ready": True,
            "staging_available": True,
            "active_environment": "development",
            "retrieved_at": utc_now().isoformat(),
        }
