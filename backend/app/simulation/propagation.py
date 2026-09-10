"""Bounded dependency effect propagation with confidence decay and uncertainty tracking."""

from __future__ import annotations

import uuid

from app.simulation.schemas import EffectType, SimulatedEffect


class EffectPropagator:
    """Propagates hypothetical effects through system dependency graphs with strict bounds."""

    def __init__(self, max_depth: int = 4, decay_factor: float = 0.92) -> None:
        self.max_depth = max_depth
        self.decay_factor = decay_factor

    def propagate_effects(
        self,
        primary_effects: list[SimulatedEffect],
        topology: dict[str, list[str]],
        is_topology_incomplete: bool = False,
    ) -> list[SimulatedEffect]:
        """Propagates primary effects through downstream dependency links up to max_depth.

        Decays confidence per hop. If topology is incomplete, confidence is further penalized.
        """
        all_effects: list[SimulatedEffect] = list(primary_effects)
        visited_paths: set[tuple[str, str]] = set()  # (source, target) to prevent cyclic propagation

        # Propagate from each primary effect that impacts HEALTH, LATENCY, or AVAILABILITY
        for effect in primary_effects:
            if effect.effect_type not in (EffectType.HEALTH, EffectType.LATENCY, EffectType.AVAILABILITY, EffectType.ERROR_RATE):
                continue

            current_nodes = [(effect.target, effect.confidence, effect.magnitude, 1)]

            while current_nodes:
                parent, curr_conf, curr_mag, depth = current_nodes.pop(0)

                if depth > self.max_depth:
                    continue

                downstream_children = topology.get(parent, [])
                for child in downstream_children:
                    edge = (parent, child)
                    if edge in visited_paths:
                        continue
                    visited_paths.add(edge)

                    # Compute decayed confidence
                    propagated_conf = curr_conf * self.decay_factor
                    if is_topology_incomplete:
                        propagated_conf *= 0.85  # Prompt #28 & #29: Incomplete dependencies produce uncertainty

                    # Downstream magnitude is scaled or inherited
                    downstream_mag = curr_mag * 0.8

                    propagated_effect = SimulatedEffect(
                        effect_id=f"eff_prop_{uuid.uuid4().hex[:8]}",
                        source=parent,
                        target=child,
                        effect_type=effect.effect_type,
                        magnitude=round(downstream_mag, 2),
                        confidence=round(max(0.1, min(1.0, propagated_conf)), 3),
                        evidence=[
                            f"Downstream dependency of '{parent}' at graph depth {depth}",
                            f"Propagation confidence decayed by factor {self.decay_factor}**{depth}",
                        ],
                        mechanism="Propagated through dependency topology (weakest link decay)",
                    )
                    all_effects.append(propagated_effect)

                    # Continue propagating downstream if depth permits
                    if depth + 1 <= self.max_depth:
                        current_nodes.append((child, propagated_conf, downstream_mag, depth + 1))

        return all_effects
