"""State reconciliation framework with non-destructive safe repairs (Task 39, Spec 62-69)."""

import logging
import time
from datetime import UTC, datetime
from typing import Any

from app.state.cache import scoped_cache
from app.state.schemas import (
    ReconciliationIssue,
    ReconciliationMode,
    ReconciliationReport,
    StateRecord,
)

logger = logging.getLogger("kairo.state.reconciliation")


class StateReconciler:
    """Reconciles authoritative state vs derived projections, caches, and orphaned records."""

    def __init__(self) -> None:
        self._last_report: ReconciliationReport | None = None

    async def reconcile(
        self,
        mode: ReconciliationMode = ReconciliationMode.CHECK,
        authoritative_records: list[StateRecord] | None = None,
        derived_records: list[dict[str, Any]] | None = None,
    ) -> ReconciliationReport:
        """Runs a state reconciliation pass in the requested mode."""
        start_time = time.perf_counter()
        issues: list[ReconciliationIssue] = []
        repaired = 0

        records = authoritative_records or []
        auth_map = {r.resource_id: r for r in records}

        # 1. Check for orphaned derived records (referencing non-existent authoritative parents)
        if derived_records:
            for derived in derived_records:
                parent_id = derived.get("parent_id") or derived.get("source_id")
                if parent_id and parent_id not in auth_map:
                    issue = ReconciliationIssue(
                        resource=f"derived:{derived.get('id')}",
                        issue="Orphaned derived record without authoritative parent",
                        evidence={"derived_id": derived.get("id"), "missing_parent": parent_id},
                        severity="MEDIUM",
                        recommended_repair="Prune orphaned derived projection record",
                    )
                    issues.append(issue)

        # 2. Check for cache mismatches
        for record in records:
            cached_val = scoped_cache.get(f"{record.domain.value}:{record.resource_id}")
            if cached_val is not None:
                # If cached version differs from authoritative version
                cached_ver = getattr(cached_val, "version", None) if hasattr(cached_val, "version") else None
                if isinstance(cached_val, dict):
                    cached_ver = cached_val.get("version")
                if cached_ver is not None and cached_ver < record.version:
                    issue = ReconciliationIssue(
                        resource=f"{record.domain.value}:{record.resource_id}",
                        issue="Stale cache entry detected",
                        evidence={"authoritative_version": record.version, "cached_version": cached_ver},
                        severity="LOW",
                        recommended_repair="Invalidate stale cache entry",
                    )
                    issues.append(issue)

                    if mode in (ReconciliationMode.SAFE_REPAIR, ReconciliationMode.FULL_REBUILD):
                        scoped_cache.invalidate(f"{record.domain.value}:{record.resource_id}")
                        repaired += 1

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        report = ReconciliationReport(
            mode=mode,
            issues=issues,
            repaired_count=repaired,
            duration_ms=round(duration_ms, 2),
            timestamp=datetime.now(UTC),
        )

        self._last_report = report
        logger.info(
            "Reconciliation finished (%s): %d issues detected, %d repaired in %.1fms",
            mode.value,
            len(issues),
            repaired,
            duration_ms,
        )
        return report

    def get_last_report(self) -> ReconciliationReport | None:
        return self._last_report


# Global reconciler instance
state_reconciler = StateReconciler()
