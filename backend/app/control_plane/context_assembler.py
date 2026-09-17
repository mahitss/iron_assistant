"""Bounded Context Assembly with Provenance & Trust Labeling (Task 102).

Constructs the minimal sufficient context required for planning and decision making.
Strictly separates:
- OBSERVED vs PREDICTED
- USER_AUTHORED vs UNTRUSTED_WEB
- FACT vs AGENT_CLAIM
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.control_plane.domain import ControlCycle, ControlSnapshot, _now_utc


class TrustClass(str):
    OBSERVED = "OBSERVED"
    USER_AUTHORED = "USER_AUTHORED"
    SYSTEM_DERIVED = "SYSTEM_DERIVED"
    MODEL_DERIVED = "MODEL_DERIVED"
    AGENT_DERIVED = "AGENT_DERIVED"
    EXTERNAL_UNTRUSTED = "EXTERNAL_UNTRUSTED"
    TOOL_UNTRUSTED = "TOOL_UNTRUSTED"
    WEB_UNTRUSTED = "WEB_UNTRUSTED"


class BoundedContextItem(BaseModel):
    item_id: str
    category: str
    content: Any
    trust_label: str = TrustClass.SYSTEM_DERIVED
    source_reference: str
    timestamp: str = Field(default_factory=_now_utc)


class BoundedContextBundle(BaseModel):
    bundle_id: str
    cycle_id: str
    items: List[BoundedContextItem] = Field(default_factory=list)
    has_untrusted_content: bool = False
    created_at: str = Field(default_factory=_now_utc)


class ControlContextAssembler:
    """Assembles minimal, bounded, trust-labeled context for deliberation."""

    @classmethod
    def assemble(
        cls,
        cycle: ControlCycle,
        snapshot: ControlSnapshot,
        mission_payload: Optional[Dict[str, Any]] = None,
        situation_payload: Optional[Dict[str, Any]] = None,
        self_model_summary: Optional[Dict[str, Any]] = None,
        recent_observations: Optional[List[Dict[str, Any]]] = None,
    ) -> BoundedContextBundle:
        items: List[BoundedContextItem] = []
        has_untrusted = False

        # 1. User objective / trigger
        trigger_trust = (
            TrustClass.USER_AUTHORED
            if cycle.trigger_type.value == "USER_REQUEST"
            else TrustClass.SYSTEM_DERIVED
        )
        items.append(
            BoundedContextItem(
                item_id="ctx_trigger",
                category="TRIGGER",
                content=cycle.trigger_payload,
                trust_label=trigger_trust,
                source_reference=f"trigger:{cycle.trigger_type.value}",
            )
        )

        # 2. Mission state (if active)
        if mission_payload:
            items.append(
                BoundedContextItem(
                    item_id="ctx_mission",
                    category="MISSION",
                    content={
                        "mission_id": mission_payload.get("mission_id"),
                        "title": mission_payload.get("title"),
                        "status": mission_payload.get("status"),
                        "progress": mission_payload.get("progress_pct", 0.0),
                    },
                    trust_label=TrustClass.OBSERVED,
                    source_reference=f"mission:{mission_payload.get('mission_id')}",
                )
            )

        # 3. Situation awareness (if active)
        if situation_payload:
            items.append(
                BoundedContextItem(
                    item_id="ctx_situation",
                    category="SITUATION",
                    content={
                        "situation_id": situation_payload.get("situation_id"),
                        "type": situation_payload.get("situation_type"),
                        "severity": situation_payload.get("severity"),
                        "title": situation_payload.get("title"),
                    },
                    trust_label=TrustClass.OBSERVED,
                    source_reference=f"situation:{situation_payload.get('situation_id')}",
                )
            )

        # 4. Self-model boundaries & capabilities
        if self_model_summary:
            items.append(
                BoundedContextItem(
                    item_id="ctx_self_model",
                    category="CAPABILITY_BOUNDARIES",
                    content={
                        "ready_capabilities": self_model_summary.get("ready_capabilities", []),
                        "degraded_capabilities": self_model_summary.get("degraded_capabilities", []),
                        "limitations_count": self_model_summary.get("limitation_count", 0),
                        "autonomy_mode": self_model_summary.get("autonomy_mode"),
                    },
                    trust_label=TrustClass.OBSERVED,
                    source_reference="self_model:current_snapshot",
                )
            )

        # 5. World state
        if snapshot and snapshot.world_state_ref:
            items.append(
                BoundedContextItem(
                    item_id="ctx_world_state",
                    category="WORLD_STATE",
                    content={
                        "world_state_ref": snapshot.world_state_ref,
                        "freshness": snapshot.freshness,
                    },
                    trust_label=TrustClass.OBSERVED,
                    source_reference=f"world_state:{snapshot.world_state_ref}",
                )
            )

        # 5. Recent observations (tagged with trust labels)
        if recent_observations:
            for i, obs in enumerate(recent_observations[:5]):
                src = obs.get("source", "tool")
                trust = TrustClass.OBSERVED
                if "web" in src.lower():
                    trust = TrustClass.WEB_UNTRUSTED
                    has_untrusted = True
                elif "tool" in src.lower() and not obs.get("is_verified", False):
                    trust = TrustClass.TOOL_UNTRUSTED
                    has_untrusted = True

                items.append(
                    BoundedContextItem(
                        item_id=f"ctx_obs_{i}",
                        category="OBSERVATION",
                        content=obs.get("data", obs),
                        trust_label=trust,
                        source_reference=f"observation:{src}",
                    )
                )

        bundle_id = f"bundle_{cycle.cycle_id}"
        return BoundedContextBundle(
            bundle_id=bundle_id,
            cycle_id=cycle.cycle_id,
            items=items,
            has_untrusted_content=has_untrusted,
        )
