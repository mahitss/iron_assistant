"""Digital Twin simulation adapter for what-if reasoning and counterfactual modeling (Task 55)."""

from __future__ import annotations

from typing import Any

from app.causal.schemas import CounterfactualScenario


class CausalSimulationEngine:
    """Provides what-if simulation integration with Digital Twin while maintaining strict separation from reality."""

    @staticmethod
    def simulate_counterfactual(
        scenario: CounterfactualScenario,
        topology_nodes: list[str] | None = None,
        service_dependencies: dict[str, list[str]] | None = None,
    ) -> dict[str, Any]:
        """Prompt #67, #68, #174: Simulate counterfactual intervention on system topology."""
        deps = service_dependencies or {}
        nodes = topology_nodes or ["api_gateway", "auth_service", "database_cluster"]

        removed_or_changed = scenario.intervention.get("removed_event_or_cause") or scenario.intervention.get("target")

        affected_topology = []
        if removed_or_changed:
            for node, upstream_list in deps.items():
                if removed_or_changed in upstream_list:
                    affected_topology.append(node)

        return {
            "scenario_id": scenario.scenario_id,
            "is_reality": False,  # Prompt #68: Simulation is not reality
            "disclaimer": "Digital Twin simulation reflects model assumptions and is not ground-truth physical reality.",
            "target_mutation": scenario.intervention,
            "nodes_modeled": nodes,
            "simulated_impacted_services": affected_topology,
            "predicted_metrics": {
                "latency_change_pct": -35.0 if affected_topology else 0.0,
                "error_rate_projected": 0.001 if affected_topology else 0.01,
            },
            "confidence": scenario.confidence * 0.9,
        }

    @staticmethod
    def validate_simulation_accuracy(
        predicted_metrics: dict[str, float],
        actual_metrics: dict[str, float],
    ) -> dict[str, Any]:
        """Prompt #175, #176: Compare predictions against real outcomes to calibrate simulation."""
        errors: dict[str, float] = {}
        total_error = 0.0
        count = 0

        for k, pred_val in predicted_metrics.items():
            if k in actual_metrics:
                act_val = actual_metrics[k]
                err = abs(pred_val - act_val)
                errors[k] = round(err, 4)
                total_error += err
                count += 1

        mae = total_error / count if count > 0 else 0.0
        accuracy = max(0.0, 1.0 - (mae / 100.0 if mae > 1.0 else mae))

        return {
            "metrics_compared": count,
            "absolute_errors": errors,
            "mean_absolute_error": round(mae, 4),
            "calibration_accuracy": round(accuracy, 4),
            "is_calibrated": accuracy >= 0.75,
        }
