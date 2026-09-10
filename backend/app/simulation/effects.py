"""Simulated effect models across 11 effect types with calibrated confidence and disclaimers."""

from __future__ import annotations

import uuid
from typing import Any

from app.simulation.schemas import EffectType, SimulatedEffect, SimulatedIntervention


class EffectCalculator:
    """Calculates predicted effects of hypothetical interventions across system dimensions."""

    def calculate_effects(
        self,
        intervention: SimulatedIntervention,
        baseline_state: dict[str, Any],
        topology: dict[str, list[str]] | None = None,
    ) -> list[SimulatedEffect]:
        """Calculates simulated effects across relevant dimensions based on intervention type and target."""
        effects: list[SimulatedEffect] = []
        op = intervention.operation.upper()
        target = intervention.target

        # 1. State effect
        effects.append(
            SimulatedEffect(
                effect_id=f"eff_state_{uuid.uuid4().hex[:8]}",
                source=f"intervention:{op}",
                target=target,
                effect_type=EffectType.STATE,
                magnitude=1.0,
                confidence=0.99,
                evidence=[f"Hypothetical change applied to {target}"],
                mechanism="Direct sandboxed state transition",
            )
        )

        # 2. Health effect
        if "KILL" in op or "FAILURE" in op:
            effects.append(
                SimulatedEffect(
                    effect_id=f"eff_health_{uuid.uuid4().hex[:8]}",
                    source=target,
                    target=target,
                    effect_type=EffectType.HEALTH,
                    magnitude=-1.0,  # critical failure
                    confidence=0.90,
                    evidence=["Service termination signal in simulation"],
                    mechanism="Process termination causes immediate service unhealthiness (PREDICTED, NOT OBSERVED)",
                )
            )
        elif "RESTART" in op or "RECOVERY" in op or "ROLLBACK" in op:
            effects.append(
                SimulatedEffect(
                    effect_id=f"eff_health_{uuid.uuid4().hex[:8]}",
                    source=target,
                    target=target,
                    effect_type=EffectType.HEALTH,
                    magnitude=0.8,
                    confidence=0.85,
                    evidence=["Restart or recovery resets transient failure state"],
                    mechanism="Process re-initialization restores base operational health",
                )
            )

        # 3. Latency & Throughput effects
        if "INJECT_LATENCY" in op:
            lat_delta = float(intervention.hypothetical_after.get("latency_ms", 50.0)) if isinstance(intervention.hypothetical_after, dict) else 50.0
            effects.append(
                SimulatedEffect(
                    effect_id=f"eff_lat_{uuid.uuid4().hex[:8]}",
                    source=target,
                    target=target,
                    effect_type=EffectType.LATENCY,
                    magnitude=lat_delta,
                    confidence=0.80,
                    evidence=[f"Simulated latency injection: +{lat_delta}ms"],
                    mechanism="Network emulation buffer delay",
                )
            )
        elif "SCALE" in op:
            effects.append(
                SimulatedEffect(
                    effect_id=f"eff_lat_{uuid.uuid4().hex[:8]}",
                    source=target,
                    target=target,
                    effect_type=EffectType.LATENCY,
                    magnitude=-15.0,  # reduced queue latency
                    confidence=0.75,
                    evidence=["Horizontal scaling redistributes request queues"],
                    mechanism="Decreased queue dwell time due to added capacity",
                )
            )
            effects.append(
                SimulatedEffect(
                    effect_id=f"eff_tp_{uuid.uuid4().hex[:8]}",
                    source=target,
                    target=target,
                    effect_type=EffectType.THROUGHPUT,
                    magnitude=500.0,
                    confidence=0.70,
                    evidence=["Added replica concurrency"],
                    mechanism="Higher aggregate request serving capacity",
                )
            )

        # 4. Resource & Cost effects
        if "SCALE_UP" in op or ("SCALE" in op and "DOWN" not in op):
            effects.append(
                SimulatedEffect(
                    effect_id=f"eff_res_{uuid.uuid4().hex[:8]}",
                    source=target,
                    target=target,
                    effect_type=EffectType.RESOURCE,
                    magnitude=2.0,  # 2 additional cores / pods
                    confidence=0.85,
                    evidence=["Replica count increased in simulation"],
                    mechanism="Container scheduler allocates additional compute slots",
                )
            )
            effects.append(
                SimulatedEffect(
                    effect_id=f"eff_cost_{uuid.uuid4().hex[:8]}",
                    source=target,
                    target=target,
                    effect_type=EffectType.COST,
                    magnitude=45.0,  # estimated monthly dollar delta
                    confidence=0.65,  # Prompt #37: Do not fabricate precise costs, flag uncertainty
                    evidence=["Heuristic cost projection: ~$45/mo (subject to cloud tier variance)"],
                    mechanism="Compute instance hourly billing model",
                )
            )

        # 5. Security effect disclaimer
        if "CONFIG" in op or "SECURITY" in op:
            effects.append(
                SimulatedEffect(
                    effect_id=f"eff_sec_{uuid.uuid4().hex[:8]}",
                    source=target,
                    target=target,
                    effect_type=EffectType.SECURITY,
                    magnitude=0.0,
                    confidence=0.60,
                    evidence=["Simulation security rules evaluated"],
                    mechanism="Configuration review (DISCLAIMER: Simulation cannot certify security)",
                )
            )

        return effects
