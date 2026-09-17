"""State Diffing and Delta Engine for Kairo Self-Model (Task 101).

Implements deterministic diffing answering:
"WHAT HAS CHANGED SINCE THE LAST CHECK?"
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from app.self_model.schemas import (
    ChangeType,
    LimitationItem,
    SelfModelDelta,
    SelfModelSnapshot,
    SelfStateChange,
    UncertaintyItem,
)


class SelfModelDeltaEngine:
    """Computes granular, auditable state deltas between two immutable snapshots."""

    @classmethod
    def compute_delta(
        cls,
        base_snapshot: Optional[SelfModelSnapshot],
        target_snapshot: SelfModelSnapshot,
    ) -> SelfModelDelta:
        """Diffs base and target snapshots producing a SelfModelDelta."""
        if base_snapshot is None:
            # Baseline creation: everything is newly initialized
            return SelfModelDelta(
                base_snapshot_id="none",
                target_snapshot_id=target_snapshot.snapshot_id,
                changes=[
                    SelfStateChange(
                        change_id=f"chg_init_{uuid.uuid4().hex[:6]}",
                        change_type=ChangeType.CAPABILITY_STATE_CHANGED,
                        target_id="system",
                        old_state="UNINITIALIZED",
                        new_state="INITIALIZED",
                        reason="Initial baseline snapshot captured",
                        evidence="Self-model initialization",
                    )
                ],
                added_limitations=list(target_snapshot.limitations),
                resolved_limitations=[],
                added_uncertainties=list(target_snapshot.uncertainties),
                resolved_uncertainties=[],
            )

        changes: List[SelfStateChange] = []

        # 1. Compare Capabilities
        for cap_id, t_cap in target_snapshot.capabilities.items():
            b_cap = base_snapshot.capabilities.get(cap_id)
            if b_cap is None:
                changes.append(
                    SelfStateChange(
                        change_id=f"chg_cap_new_{cap_id}",
                        change_type=ChangeType.CAPABILITY_STATE_CHANGED,
                        target_id=cap_id,
                        old_state="NONE",
                        new_state=t_cap.readiness_state.value,
                        reason="New capability discovered and ingested",
                        evidence=f"Lifecycle: {t_cap.lifecycle_state}",
                    )
                )
            elif b_cap.readiness_state != t_cap.readiness_state:
                changes.append(
                    SelfStateChange(
                        change_id=f"chg_cap_{cap_id}",
                        change_type=ChangeType.CAPABILITY_STATE_CHANGED,
                        target_id=cap_id,
                        old_state=b_cap.readiness_state.value,
                        new_state=t_cap.readiness_state.value,
                        reason=t_cap.last_failure_reason or f"Readiness changed from {b_cap.readiness_state.value} to {t_cap.readiness_state.value}",
                        evidence="; ".join(t_cap.evidence),
                    )
                )

        # 2. Compare Autonomy Mode & Emergency Stop
        if base_snapshot.emergency_stop_state != target_snapshot.emergency_stop_state:
            changes.append(
                SelfStateChange(
                    change_id=f"chg_estop_{uuid.uuid4().hex[:6]}",
                    change_type=ChangeType.EMERGENCY_STOP_CHANGED,
                    target_id="emergency_stop",
                    old_state=base_snapshot.emergency_stop_state,
                    new_state=target_snapshot.emergency_stop_state,
                    reason="Emergency stop kill-switch transitioned",
                    evidence=f"Active state: {target_snapshot.emergency_stop_state}",
                )
            )

        if base_snapshot.autonomy_mode != target_snapshot.autonomy_mode:
            changes.append(
                SelfStateChange(
                    change_id=f"chg_autonomy_{uuid.uuid4().hex[:6]}",
                    change_type=ChangeType.AUTONOMY_STATE_CHANGED,
                    target_id="autonomy_mode",
                    old_state=base_snapshot.autonomy_mode.value,
                    new_state=target_snapshot.autonomy_mode.value,
                    reason="Autonomy mode adapted due to constraint shifts",
                    evidence=f"Mode transitioned to {target_snapshot.autonomy_mode.value}",
                )
            )

        # 3. Compare Dependencies
        for dep_id, t_dep in target_snapshot.dependencies.items():
            b_dep = base_snapshot.dependencies.get(dep_id)
            if b_dep and b_dep.status != t_dep.status:
                changes.append(
                    SelfStateChange(
                        change_id=f"chg_dep_{dep_id}",
                        change_type=ChangeType.DEPENDENCY_STATE_CHANGED,
                        target_id=dep_id,
                        old_state=b_dep.status,
                        new_state=t_dep.status,
                        reason=f"Dependency '{dep_id}' health changed to {t_dep.status}",
                        evidence=t_dep.evidence,
                    )
                )

        # 4. Compare Resource Saturation Tier
        if base_snapshot.resources.degradation_tier != target_snapshot.resources.degradation_tier:
            changes.append(
                SelfStateChange(
                    change_id="chg_res_tier",
                    change_type=ChangeType.RESOURCE_STATE_CHANGED,
                    target_id="resources",
                    old_state=base_snapshot.resources.degradation_tier,
                    new_state=target_snapshot.resources.degradation_tier,
                    reason="Economy degradation tier adapted",
                    evidence=f"Saturation: {target_snapshot.resources.saturation_pct}",
                )
            )

        # 5. Diff Limitations
        base_lim_ids = {l.limitation_id for l in base_snapshot.limitations}
        target_lim_ids = {l.limitation_id for l in target_snapshot.limitations}

        added_limitations = [l for l in target_snapshot.limitations if l.limitation_id not in base_lim_ids]
        resolved_limitations = [l for l in base_snapshot.limitations if l.limitation_id not in target_lim_ids]

        # 6. Diff Uncertainties
        base_unc_ids = {u.uncertainty_id for u in base_snapshot.uncertainties}
        target_unc_ids = {u.uncertainty_id for u in target_snapshot.uncertainties}

        added_uncertainties = [u for u in target_snapshot.uncertainties if u.uncertainty_id not in base_unc_ids]
        resolved_uncertainties = [u for u in base_snapshot.uncertainties if u.uncertainty_id not in target_unc_ids]

        return SelfModelDelta(
            base_snapshot_id=base_snapshot.snapshot_id,
            target_snapshot_id=target_snapshot.snapshot_id,
            changes=changes,
            added_limitations=added_limitations,
            resolved_limitations=resolved_limitations,
            added_uncertainties=added_uncertainties,
            resolved_uncertainties=resolved_uncertainties,
        )
