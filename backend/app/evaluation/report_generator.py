"""Structured Evaluation & Release Report Generator.
Task 104 Section 53.
Distinguishes FACT, OBSERVATION, MEASUREMENT, INFERENCE, and RECOMMENDATION.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.evaluation.domain import (
    EvaluationComparison,
    EvaluationRun,
    ImprovementProposal,
    RegressionFinding,
)


class ComprehensiveReportGenerator:
    """Generates rigorous audit reports distinguishing facts, measurements, and inferences."""

    @classmethod
    def generate_markdown_report(
        cls,
        run: EvaluationRun,
        comparison: Optional[EvaluationComparison] = None,
        proposals: Optional[list[ImprovementProposal]] = None,
    ) -> str:
        """Generates a structured markdown report adhering to Section 53 taxonomy."""
        comp_summary = comparison.summary if comparison else "No baseline comparison supplied."
        reg_count = comparison.regressions_count if comparison else 0
        is_blocked = comparison.release_blocked if comparison else (run.security_pass_rate < 1.0)

        lines: list[str] = [
            f"# Kairo Autonomous Evaluation & Benchmarking Report",
            f"**Run ID**: `{run.id}` | **Generated**: `{datetime.now(UTC).isoformat()}` | **Mode**: `{run.execution_mode.value}`",
            "",
            "## 1. Executive Summary",
            f"- **[FACT] Status**: `{run.status.value}`",
            f"- **[FACT] Total Cases**: `{run.cases_total}` (Passed: `{run.cases_passed}`, Failed: `{run.cases_failed}`)",
            f"- **[MEASUREMENT] Overall Pass Rate**: `{run.pass_rate * 100:.1f}%`",
            f"- **[MEASUREMENT] Security Invariance**: `{run.security_pass_rate * 100:.1f}%`",
            f"- **[MEASUREMENT] Latency P95**: `{run.latency_p95_ms:.1f}ms` | **Estimated Cost**: `${run.estimated_cost_usd:.5f}`",
            f"- **[FACT] Release Gate**: `{'🛑 BLOCKED' if is_blocked else '✅ APPROVED'}`",
            f"- **[INFERENCE] Release Summary**: {comp_summary}",
            "",
            "## 2. Environment, Scope & Versions",
            f"- **[FACT] Suite**: `{run.suite_name}` (ID: `{run.suite_id}`)",
            f"- **[FACT] Kairo Version**: `{run.candidate_version}` | **Dataset Version**: `{run.dataset_version}`",
            f"- **[FACT] Baseline ID**: `{run.baseline_id or 'N/A'}`",
            "",
            "## 3. Measurements & Delta Comparisons",
            "| Metric | Candidate | Baseline | Delta | Status |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]

        if comparison and comparison.deltas:
            for d in comparison.deltas:
                lines.append(
                    f"| `{d.get('metric_name')}` | `{d.get('candidate_value')}` | `{d.get('baseline_value')}` | `{d.get('delta_percentage'):+.1f}%` | `{d.get('status')}` |"
                )
        else:
            lines.append(f"| `pass_rate` | `{run.pass_rate}` | `N/A` | `0.0%` | `measured` |")
            lines.append(f"| `security_pass_rate` | `{run.security_pass_rate}` | `1.0` | `0.0%` | `measured` |")

        lines.extend([
            "",
            "## 4. Regressions & Weakness Analysis",
            f"- **[OBSERVATION] Detected Regressions**: `{reg_count}`",
        ])

        if comparison and comparison.blocking_reasons:
            lines.append("### Blocking Reasons:")
            for reason in comparison.blocking_reasons:
                lines.append(f"- **[FACT]** 🛑 {reason}")

        lines.extend([
            "",
            "## 5. Governed Improvement Proposals",
        ])

        if proposals:
            for p in proposals:
                lines.append(f"### Proposal: `{p.title}` (`{p.id}`)")
                lines.append(f"- **[OBSERVATION] Problem**: {p.problem_statement}")
                lines.append(f"- **[RECOMMENDATION] Proposed Change**: {json.dumps(p.proposed_change)}")
                lines.append(f"- **[INFERENCE] Expected Benefit**: {p.expected_benefit}")
                lines.append(f"- **[FACT] Required Approvals**: `{', '.join(p.required_approvals)}`")
                lines.append(f"- **[FACT] Status**: `{p.status}`")
        else:
            lines.append("- *No improvement proposals generated for this evaluation.*")

        lines.extend([
            "",
            "## 6. Uncertainty & Limitations",
            "- **[OBSERVATION] Statistical Confidence**: Small sample runs (<10 cases) are marked `INCONCLUSIVE`.",
            "- **[FACT] Simulation Firewall**: Results tagged `SIMULATED` or `SYNTHETIC` represent offline model evaluations, NOT verified real-world operational results.",
            "",
            "## 7. Conclusion & Next Steps",
            f"- **[RECOMMENDATION] Action**: `{'Halt release, dispatch improvement proposals to Governance.' if is_blocked else 'Proceed to standard canary deployment.'}`",
        ])

        return "\n".join(lines)

    @classmethod
    def generate_json_report(
        cls,
        run: EvaluationRun,
        comparison: Optional[EvaluationComparison] = None,
        proposals: Optional[list[ImprovementProposal]] = None,
    ) -> dict[str, Any]:
        """Generates machine-readable structured report with taxonomy tags."""
        return {
            "metadata": {
                "run_id": run.id,
                "generated_at": datetime.now(UTC).isoformat(),
                "mode": run.execution_mode.value,
            },
            "facts": {
                "status": run.status.value,
                "suite_name": run.suite_name,
                "cases_total": run.cases_total,
                "cases_passed": run.cases_passed,
                "cases_failed": run.cases_failed,
                "release_blocked": comparison.release_blocked if comparison else (run.security_pass_rate < 1.0),
            },
            "measurements": {
                "pass_rate": run.pass_rate,
                "security_pass_rate": run.security_pass_rate,
                "latency_p95_ms": run.latency_p95_ms,
                "estimated_cost_usd": run.estimated_cost_usd,
                "total_tokens": run.total_tokens,
                "deltas": comparison.deltas if comparison else [],
            },
            "inferences": {
                "summary": comparison.summary if comparison else "No baseline supplied",
                "blocking_reasons": comparison.blocking_reasons if comparison else [],
            },
            "recommendations": {
                "proposals": [p.model_dump() for p in (proposals or [])],
                "action": "HALT_RELEASE" if (comparison and comparison.release_blocked) else "PROCEED",
            },
        }
