"""Experience Mining Engine for Kairo Strategy Engine (Task 106).

Mines verified experiences from Task 103 (Lifelong Memory), Task 104 (Evaluations),
and Task 105 (Governed Experiments) to identify candidate recurring operational patterns.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
import logging
from typing import Any, Dict, List, Optional

from app.strategy.domain import (
    EvidenceSourceType,
    StrategyEvidence,
    utc_now,
)

logger = logging.getLogger("kairo.strategy.experience_miner")


class MinedExperienceCluster:
    """Cluster of related experiences sharing contextual patterns."""

    def __init__(
        self,
        cluster_key: str,
        category: str,
        domain_scope: str,
        conditions: Dict[str, Any],
        approach_summary: str,
    ) -> None:
        self.cluster_key = cluster_key
        self.category = category
        self.domain_scope = domain_scope
        self.conditions = conditions
        self.approach_summary = approach_summary
        self.successes: List[Dict[str, Any]] = []
        self.failures: List[Dict[str, Any]] = []
        self.counterexamples: List[Dict[str, Any]] = []
        self.evidences: List[StrategyEvidence] = []

    @property
    def total_count(self) -> int:
        return len(self.successes) + len(self.failures)

    @property
    def success_rate(self) -> float:
        if self.total_count == 0:
            return 0.0
        return len(self.successes) / self.total_count


class ExperienceMiningEngine:
    """Mines verified experiences and clusters them into candidates for pattern detection."""

    def __init__(self, min_cluster_samples: int = 3) -> None:
        self.min_cluster_samples = min_cluster_samples
        self._mined_clusters: Dict[str, MinedExperienceCluster] = {}

    def mine_experiences(
        self,
        experiences: List[Dict[str, Any]],
        evaluations: Optional[List[Dict[str, Any]]] = None,
        experiments: Optional[List[Dict[str, Any]]] = None,
    ) -> List[MinedExperienceCluster]:
        """Mine and cluster experiences across decisions, actions, recoveries, and evaluations."""
        clusters: Dict[str, MinedExperienceCluster] = {}

        # 1. Process Task 103 Experiences
        for exp in experiences:
            outcome = str(exp.get("outcome", "SUCCESS")).upper()
            category = exp.get("category", "DECISION")
            domain_scope = exp.get("scope", "SYSTEM")
            task_type = exp.get("task_type", exp.get("source_type", "GENERAL"))
            capability = exp.get("capability", "general_reasoning")
            approach = exp.get("approach", exp.get("summary", "Standard execution"))

            cluster_key = f"{category}:{domain_scope}:{task_type}:{capability}"
            if cluster_key not in clusters:
                clusters[cluster_key] = MinedExperienceCluster(
                    cluster_key=cluster_key,
                    category=category,
                    domain_scope=domain_scope,
                    conditions={
                        "task_type": task_type,
                        "capability": capability,
                        "environment": exp.get("environment", "prod"),
                    },
                    approach_summary=approach,
                )

            cluster = clusters[cluster_key]
            evidence = StrategyEvidence(
                strategy_id="",
                source_type=EvidenceSourceType.TASK_103_EXPERIENCE,
                source_id=exp.get("id", f"exp_{len(cluster.evidences)}"),
                is_counterexample=(outcome != "SUCCESS"),
                claim=f"Observed {outcome} under {task_type} using {capability}",
                observed_metrics=exp.get("metrics", {}),
                environmental_context=exp.get("environment_context", {}),
                capability_version=exp.get("capability_version", "1.0.0"),
                confidence_weight=float(exp.get("confidence", 0.8)),
                verified=bool(exp.get("verified", True)),
            )
            evidence.seal()
            cluster.evidences.append(evidence)

            if outcome == "SUCCESS":
                cluster.successes.append(exp)
            else:
                cluster.failures.append(exp)
                cluster.counterexamples.append(exp)

        # 2. Process Task 104 Evaluations
        if evaluations:
            for ev in evaluations:
                suite = ev.get("suite_name", "evaluation_suite")
                verdict = ev.get("verdict", "INCONCLUSIVE")
                cluster_key = f"VERIFICATION:SYSTEM:{suite}:evaluator"
                if cluster_key not in clusters:
                    clusters[cluster_key] = MinedExperienceCluster(
                        cluster_key=cluster_key,
                        category="VERIFICATION",
                        domain_scope="SYSTEM",
                        conditions={"evaluation_suite": suite},
                        approach_summary=f"Automated benchmark evaluation for {suite}",
                    )
                cluster = clusters[cluster_key]
                evidence = StrategyEvidence(
                    strategy_id="",
                    source_type=EvidenceSourceType.TASK_104_EVALUATION,
                    source_id=ev.get("run_id", "eval_run"),
                    is_counterexample=(verdict == "FAIL" or verdict == "REGRESSED"),
                    claim=f"Evaluation verdict: {verdict}",
                    observed_metrics=ev.get("metrics", {}),
                    verified=True,
                )
                evidence.seal()
                cluster.evidences.append(evidence)
                if verdict == "PASS":
                    cluster.successes.append(ev)
                else:
                    cluster.failures.append(ev)
                    cluster.counterexamples.append(ev)

        # 3. Filter clusters meeting minimum threshold to reject one-offs
        viable_clusters = [
            c for c in clusters.values() if c.total_count >= self.min_cluster_samples
        ]

        logger.info(
            f"Mined {len(experiences)} experiences into {len(clusters)} raw clusters; {len(viable_clusters)} meet threshold ({self.min_cluster_samples}+ samples)."
        )
        return viable_clusters
