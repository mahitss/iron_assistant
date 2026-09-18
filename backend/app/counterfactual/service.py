"""Singleton service coordinator for Task 113:
Autonomous Counterfactual, Intervention Analysis, What-If Simulation & Causal Experiment Planning Engine.
"""

from __future__ import annotations

import copy
from datetime import UTC, datetime
import json
import logging
from pathlib import Path
import tempfile
from typing import Any
import uuid

from app.counterfactual.baseline_engine import BaselineEngine
from app.counterfactual.causal_bridge import CausalBridge
from app.counterfactual.comparison_engine import ComparisonEngine
from app.counterfactual.domain import (
    BaselineType,
    CounterfactualAnalysis,
    CounterfactualBaseline,
    CounterfactualLifecycleStage,
    CounterfactualRequest,
    CounterfactualScenario,
    CounterfactualSnapshot,
    CounterfactualType,
    Intervention,
    InterventionVerification,
)
from app.counterfactual.experiment_planner import ExperimentPlanner
from app.counterfactual.intervention_engine import InterventionEngine
from app.counterfactual.sensitivity_engine import SensitivityEngine
from app.counterfactual.simulation_bridge import SimulationBridge
from app.counterfactual.staleness_engine import StalenessEngine
from app.counterfactual.verification_engine import VerificationEngine

logger = logging.getLogger("kairo.counterfactual.service")


class CounterfactualService:
    """Authoritative service coordinating counterfactual reasoning, simulation, and experiment planning."""

    _instance: CounterfactualService | None = None

    def __new__(cls) -> CounterfactualService:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_service()
        return cls._instance

    def _init_service(self) -> None:
        self._analyses: dict[str, CounterfactualAnalysis] = {}
        self._causal_bridge = CausalBridge()
        self._sim_bridge = SimulationBridge()

        # Multi-process disk caching for CLI interoperability
        self._cache_dir = Path(tempfile.gettempdir()) / "kairo_counterfactual_cache"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._load_from_disk()

    def _save_to_disk(self, analysis: CounterfactualAnalysis) -> None:
        try:
            p = self._cache_dir / f"{analysis.analysis_id}.json"
            scenarios_data = []
            for s in analysis.scenarios:
                intvs_data = []
                for i in s.interventions:
                    asms = [{"description": a.description, "status": a.status.value, "sensitivity_weight": a.sensitivity_weight} for a in i.assumptions]
                    intvs_data.append({
                        "intervention_id": i.intervention_id,
                        "name": i.name,
                        "target": i.target,
                        "scope": i.scope.value,
                        "changes": i.changes,
                        "assumptions": asms,
                        "risk_level": i.risk_level,
                        "is_reversible": i.is_reversible,
                    })
                pred_data = {
                    "prediction_id": s.prediction.prediction_id if s.prediction else "",
                    "predicted_state": s.prediction.predicted_state if s.prediction else {},
                    "confidence": s.prediction.confidence if s.prediction else 0.5,
                } if s.prediction else None
                scenarios_data.append({
                    "scenario_id": s.scenario_id,
                    "scenario_name": s.scenario_name,
                    "is_no_action": s.is_no_action,
                    "scenario_type": s.scenario_type.value,
                    "interventions": intvs_data,
                    "prediction": pred_data,
                })

            cmp_data = None
            if analysis.comparison:
                cmp_data = {
                    "comparison_id": analysis.comparison.comparison_id,
                    "tradeoff_summary": analysis.comparison.tradeoff_summary,
                    "recommended_option_for_decision": analysis.comparison.recommended_option_for_decision,
                    "no_action_viable": analysis.comparison.no_action_viable,
                    "items": [
                        {
                            "scenario_id": it.scenario_id,
                            "scenario_name": it.scenario_name,
                            "is_no_action": it.is_no_action,
                            "predicted_summary": it.predicted_summary,
                            "key_assumptions": it.key_assumptions,
                            "risk_level": it.risk_level,
                            "resource_cost_summary": it.resource_cost_summary,
                            "reversibility": it.reversibility,
                            "uncertainty_level": it.uncertainty_level,
                            "confidence": it.confidence,
                        }
                        for it in analysis.comparison.items
                    ],
                }

            sens_data = None
            if analysis.sensitivity:
                sens_data = {
                    "summary": analysis.sensitivity.summary,
                    "influential_parameters": analysis.sensitivity.influential_parameters,
                    "critical_assumptions": analysis.sensitivity.critical_assumptions,
                    "elasticity_map": analysis.sensitivity.elasticity_map,
                }

            rob_data = None
            if analysis.robustness:
                rob_data = {
                    "classification": analysis.robustness.classification.value,
                    "stability_score": analysis.robustness.stability_score,
                    "vulnerabilities": analysis.robustness.vulnerabilities,
                }

            data = {
                "analysis_id": analysis.analysis_id,
                "version": analysis.version,
                "target_entity": analysis.target_entity,
                "question": analysis.question,
                "lifecycle_stage": analysis.lifecycle_stage.value,
                "counterfactual_type": analysis.counterfactual_type.value,
                "baseline": {
                    "baseline_id": analysis.baseline.baseline_id,
                    "baseline_type": analysis.baseline.baseline_type.value,
                    "target_entity": analysis.baseline.target_entity,
                    "state_snapshot": analysis.baseline.state_snapshot,
                    "timestamp": analysis.baseline.timestamp.isoformat(),
                    "uncertainty_summary": analysis.baseline.uncertainty_summary,
                    "is_historical_reconstruction": analysis.baseline.is_historical_reconstruction,
                },
                "scenarios": scenarios_data,
                "comparison": cmp_data,
                "sensitivity": sens_data,
                "robustness": rob_data,
                "is_stale": analysis.is_stale,
                "stale_reason": analysis.stale_reason,
                "environment_label": analysis.environment_label,
                "is_hypothetical": analysis.is_hypothetical,
                "created_at": analysis.created_at.isoformat(),
                "updated_at": analysis.updated_at.isoformat(),
            }
            p.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.debug("Disk save error: %s", e)

    def _load_from_disk(self) -> None:
        try:
            for p in self._cache_dir.glob("*.json"):
                data = json.loads(p.read_text(encoding="utf-8"))
                aid = data["analysis_id"]
                if aid not in self._analyses:
                    b_data = data.get("baseline", {})
                    base = CounterfactualBaseline(
                        baseline_id=b_data.get("baseline_id", "base_default"),
                        baseline_type=BaselineType(b_data.get("baseline_type", "CURRENT")),
                        target_entity=b_data.get("target_entity", data.get("target_entity", "")),
                        state_snapshot=b_data.get("state_snapshot", {}),
                        uncertainty_summary=b_data.get("uncertainty_summary", ""),
                        is_historical_reconstruction=b_data.get("is_historical_reconstruction", False),
                    )

                    scens = []
                    for s_data in data.get("scenarios", []):
                        intvs = []
                        for i_data in s_data.get("interventions", []):
                            from app.counterfactual.domain import InterventionAssumption, AssumptionStatus, InterventionScope
                            asms = [
                                InterventionAssumption(
                                    description=a["description"],
                                    status=AssumptionStatus(a.get("status", "PLAUSIBLE")),
                                    sensitivity_weight=a.get("sensitivity_weight", 0.5),
                                )
                                for a in i_data.get("assumptions", [])
                            ]
                            intvs.append(
                                Intervention(
                                    intervention_id=i_data["intervention_id"],
                                    name=i_data["name"],
                                    target=i_data["target"],
                                    scope=InterventionScope(i_data.get("scope", "SERVICE")),
                                    changes=i_data.get("changes", {}),
                                    assumptions=asms,
                                    risk_level=i_data.get("risk_level", "LOW"),
                                    is_reversible=i_data.get("is_reversible", True),
                                )
                            )

                        pred = None
                        if s_data.get("prediction"):
                            from app.counterfactual.domain import InterventionPrediction
                            p_data = s_data["prediction"]
                            pred = InterventionPrediction(
                                prediction_id=p_data.get("prediction_id", ""),
                                predicted_state=p_data.get("predicted_state", {}),
                                confidence=p_data.get("confidence", 0.5),
                            )

                        scens.append(
                            CounterfactualScenario(
                                scenario_id=s_data["scenario_id"],
                                scenario_name=s_data["scenario_name"],
                                is_no_action=s_data.get("is_no_action", False),
                                scenario_type=CounterfactualType(s_data.get("scenario_type", "RESOURCE")),
                                baseline_id=base.baseline_id,
                                interventions=intvs,
                                prediction=pred,
                            )
                        )

                    cmp = None
                    if data.get("comparison"):
                        from app.counterfactual.domain import InterventionComparison, InterventionComparisonItem
                        c_data = data["comparison"]
                        items = [
                            InterventionComparisonItem(
                                scenario_id=it["scenario_id"],
                                scenario_name=it["scenario_name"],
                                is_no_action=it.get("is_no_action", False),
                                predicted_summary=it.get("predicted_summary", ""),
                                key_assumptions=it.get("key_assumptions", []),
                                risk_level=it.get("risk_level", "LOW"),
                                resource_cost_summary=it.get("resource_cost_summary", ""),
                                reversibility=it.get("reversibility", "REVERSIBLE"),
                                uncertainty_level=it.get("uncertainty_level", "LOW"),
                                confidence=it.get("confidence", 0.8),
                            )
                            for it in c_data.get("items", [])
                        ]
                        cmp = InterventionComparison(
                            comparison_id=c_data.get("comparison_id", ""),
                            baseline_scenario_id=base.baseline_id,
                            items=items,
                            tradeoff_summary=c_data.get("tradeoff_summary", ""),
                            recommended_option_for_decision=c_data.get("recommended_option_for_decision"),
                            no_action_viable=c_data.get("no_action_viable", True),
                        )

                    sens = None
                    if data.get("sensitivity"):
                        from app.counterfactual.domain import SensitivityResult
                        s_data = data["sensitivity"]
                        sens = SensitivityResult(
                            summary=s_data.get("summary", ""),
                            influential_parameters=s_data.get("influential_parameters", []),
                            critical_assumptions=s_data.get("critical_assumptions", []),
                            elasticity_map=s_data.get("elasticity_map", {}),
                        )

                    rob = None
                    if data.get("robustness"):
                        from app.counterfactual.domain import RobustnessAssessment, RobustnessClassification
                        r_data = data["robustness"]
                        rob = RobustnessAssessment(
                            classification=RobustnessClassification(r_data.get("classification", "ROBUST")),
                            stability_score=r_data.get("stability_score", 0.8),
                            vulnerabilities=r_data.get("vulnerabilities", []),
                        )

                    self._analyses[aid] = CounterfactualAnalysis(
                        analysis_id=aid,
                        version=data.get("version", 1),
                        target_entity=data.get("target_entity", ""),
                        question=data.get("question", ""),
                        lifecycle_stage=CounterfactualLifecycleStage(data.get("lifecycle_stage", "PROVISIONAL")),
                        counterfactual_type=CounterfactualType(data.get("counterfactual_type", "RESOURCE")),
                        baseline=base,
                        scenarios=scens,
                        comparison=cmp,
                        sensitivity=sens,
                        robustness=rob,
                        is_stale=data.get("is_stale", False),
                        stale_reason=data.get("stale_reason", ""),
                        environment_label=data.get("environment_label", "SIMULATION_ONLY"),
                        is_hypothetical=data.get("is_hypothetical", True),
                    )
        except Exception as e:
            logger.debug("Disk load error: %s", e)

    def create_analysis(self, req: CounterfactualRequest) -> CounterfactualAnalysis:
        """Executes the full counterfactual evaluation pipeline:
        Baseline -> Causal Subgraph -> Scenarios (including NO_ACTION) -> Simulation -> Comparison -> Sensitivity -> Proposals.
        """
        analysis_id = f"cfa_{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC)

        # 1. Build Factual Baseline
        baseline = BaselineEngine.build_baseline(
            target_entity=req.target_entity,
            baseline_type=req.baseline_type,
            as_of_time=req.baseline_time,
        )

        # 2. Extract Causal Subgraph & Mechanisms
        subgraph = self._causal_bridge.extract_bounded_subgraph(
            target_variable=req.target_variable or req.target_entity,
            max_depth=req.causal_depth_limit,
        )

        scenarios: list[CounterfactualScenario] = []

        # 3. Always Build NO_ACTION Baseline Scenario First
        if req.include_no_action:
            no_action_scen = CounterfactualScenario(
                scenario_id=f"scen_no_action_{uuid.uuid4().hex[:8]}",
                scenario_name="NO_ACTION (Baseline Reference)",
                baseline_id=baseline.baseline_id,
                interventions=[],
                scenario_type=req.counterfactual_type,
                is_no_action=True,
                is_hypothetical=True,
            )
            # Simulate NO_ACTION
            no_action_pred, no_action_out = self._sim_bridge.simulate_scenario(
                baseline=baseline,
                scenario=no_action_scen,
                simulation_budget_seconds=req.simulation_budget_seconds,
            )
            no_action_scen.prediction = no_action_pred
            no_action_scen.outcome = no_action_out
            scenarios.append(no_action_scen)

        # 4. Build Candidate Intervention Scenarios
        for i, change_spec in enumerate(req.candidate_changes or [{"resource_limit_increase": 0.2}]):
            intv_name = change_spec.get("name", f"Candidate Intervention {i + 1}")
            target_var = change_spec.get("target", req.target_variable or req.target_entity)
            intv = InterventionEngine.create_intervention(
                name=intv_name,
                target=target_var,
                changes=change_spec,
                intervention_type=req.counterfactual_type,
                risk_level=change_spec.get("risk_level", "LOW"),
                is_reversible=change_spec.get("is_reversible", True),
                reversibility_plan=change_spec.get("reversibility_plan", ""),
            )

            scen = CounterfactualScenario(
                scenario_id=f"scen_{uuid.uuid4().hex[:8]}",
                scenario_name=intv_name,
                baseline_id=baseline.baseline_id,
                interventions=[intv],
                scenario_type=req.counterfactual_type,
                is_no_action=False,
                is_hypothetical=True,
            )

            # Sandboxed simulation
            pred, out = self._sim_bridge.simulate_scenario(
                baseline=baseline,
                scenario=scen,
                simulation_budget_seconds=req.simulation_budget_seconds,
            )
            scen.prediction = pred
            scen.outcome = out
            scenarios.append(scen)

        # 5. Structured Comparison across NO_ACTION and candidate interventions
        comparison = ComparisonEngine.compare_scenarios(scenarios=scenarios)

        # 6. Sensitivity & Robustness Analysis
        active_scens = [s for s in scenarios if not s.is_no_action]
        eval_scen = active_scens[0] if active_scens else scenarios[0]
        sensitivity = SensitivityEngine.analyze_sensitivity(scenario=eval_scen)
        robustness = SensitivityEngine.assess_robustness(sensitivity=sensitivity, scenario=eval_scen)

        # 7. Information-Gain Analysis & Experiment Proposals
        proposals = ExperimentPlanner.evaluate_information_gain(
            competing_hypotheses=[s.scenario_name for s in scenarios],
            target_entity=req.target_entity,
        )

        analysis = CounterfactualAnalysis(
            analysis_id=analysis_id,
            version=1,
            target_entity=req.target_entity,
            question=req.question,
            lifecycle_stage=CounterfactualLifecycleStage.READY_FOR_DECISION,
            counterfactual_type=req.counterfactual_type,
            baseline=baseline,
            scenarios=scenarios,
            comparison=comparison,
            sensitivity=sensitivity,
            robustness=robustness,
            information_gain_proposals=proposals,
            causal_model_version="v1.0",
            is_stale=False,
            created_at=now,
            updated_at=now,
            environment_label="SIMULATION_ONLY",
            is_hypothetical=True,
        )

        self._analyses[analysis_id] = analysis
        self._save_to_disk(analysis)
        logger.info("Created counterfactual analysis %s for entity %s", analysis_id, req.target_entity)
        return analysis

    def get_analysis(self, analysis_id: str) -> CounterfactualAnalysis | None:
        """Fetches counterfactual analysis by ID."""
        return self._analyses.get(analysis_id)

    def list_analyses(self, limit: int = 50) -> list[CounterfactualAnalysis]:
        """Lists recent counterfactual analyses."""
        return sorted(self._analyses.values(), key=lambda a: a.created_at, reverse=True)[:limit]

    def verify_analysis(
        self,
        analysis_id: str,
        executed_intervention_id: str,
        observed_state: dict[str, Any],
    ) -> InterventionVerification | None:
        """Verifies counterfactual prediction against actual post-intervention observed telemetry."""
        analysis = self.get_analysis(analysis_id)
        if not analysis:
            return None

        ver = VerificationEngine.verify_intervention(
            analysis=analysis,
            executed_intervention_id=executed_intervention_id,
            observed_state=observed_state,
        )
        self._save_to_disk(analysis)
        return ver

    def mark_stale(self, analysis_id: str, reason: str) -> bool:
        """Explicitly marks counterfactual as stale."""
        analysis = self.get_analysis(analysis_id)
        if not analysis:
            return False
        analysis.is_stale = True
        analysis.stale_reason = reason
        analysis.lifecycle_stage = CounterfactualLifecycleStage.STALE
        analysis.updated_at = datetime.now(UTC)
        self._save_to_disk(analysis)
        return True

    def create_snapshot(self, analysis_id: str) -> CounterfactualSnapshot | None:
        """Captures an immutable snapshot of analysis state."""
        analysis = self.get_analysis(analysis_id)
        if not analysis:
            return None
        return CounterfactualSnapshot(
            snapshot_id=f"cf_snap_{uuid.uuid4().hex[:12]}",
            analysis_id=analysis_id,
            version=analysis.version,
            baseline_snapshot=copy.deepcopy(analysis.baseline.state_snapshot),
            scenarios_snapshot=[{"name": s.scenario_name, "is_no_action": s.is_no_action} for s in analysis.scenarios],
            comparison_snapshot={"tradeoffs": analysis.comparison.tradeoff_summary if analysis.comparison else ""},
            causal_model_version=analysis.causal_model_version,
            created_at=datetime.now(UTC),
        )


def get_counterfactual_service() -> CounterfactualService:
    """Singleton getter for CounterfactualService."""
    return CounterfactualService()
