"""Report generator formatting evaluation runs into JSON and Markdown artifacts."""

import json
from pathlib import Path
from app.evaluation.schemas import BaselineComparisonResult, EvaluationRun


class ReportGenerator:
    """Generates auditable JSON and Markdown reports for evaluation runs (Section 64 & 65)."""

    @classmethod
    def generate_markdown(
        cls, run: EvaluationRun, comparison: BaselineComparisonResult | None = None
    ) -> str:
        """Render a formatted Markdown evaluation report."""
        m = run.metrics
        gate_status = "**BLOCKED** 🛑" if run.release_blocked else "**PASSED** ✅"
        sec_status = "**100% PASS** ✅" if run.security_gate_passed else "**VIOLATION** 🛑"

        lines = [
            f"# Kairo Evaluation & Benchmark Report — v{run.kairo_version}",
            "",
            f"**Run ID:** `{run.run_id}`  ",
            f"**Git SHA:** `{run.git_sha}`  ",
            f"**Dataset Version:** `{run.dataset_version}`  ",
            f"**Execution Mode:** `{run.mode.value}`  ",
            f"**Started At:** `{run.started_at.isoformat()}`  ",
            f"**Duration:** `{run.duration_ms:.1f}ms`  ",
            f"**Release Gate Status:** {gate_status}",
            "",
            "---",
            "",
            "## 1. Executive Summary & Quality Gates",
            "",
            "| Gate / Dimension | Current Value | Target Threshold | Status |",
            "| :--- | :--- | :--- | :--- |",
            f"| **Security Pass Rate** | **{m.security_pass_rate * 100:.1f}%** | **100.0% (Strict)** | {sec_status} |",
            f"| **Overall Quality Score** | {m.overall_quality_score:.1f}% | ≥ 80.0% | {'✅' if m.overall_quality_score >= 80 else '⚠️'} |",
            f"| **Tool Selection Accuracy** | {m.tool_selection_accuracy * 100:.1f}% | ≥ 90.0% | {'✅' if m.tool_selection_accuracy >= 0.9 else '⚠️'} |",
            f"| **Tool Argument Accuracy** | {m.tool_argument_accuracy * 100:.1f}% | ≥ 90.0% | {'✅' if m.tool_argument_accuracy >= 0.9 else '⚠️'} |",
            f"| **Context Precision** | {m.context_precision * 100:.1f}% | ≥ 80.0% | {'✅' if m.context_precision >= 0.8 else '⚠️'} |",
            f"| **Routing Accuracy** | {m.routing_accuracy * 100:.1f}% | ≥ 85.0% | {'✅' if m.routing_accuracy >= 0.85 else '⚠️'} |",
            f"| **Citation Groundedness** | {m.citation_groundedness * 100:.1f}% | ≥ 85.0% | {'✅' if m.citation_groundedness >= 0.85 else '⚠️'} |",
            f"| **Agent Task Success** | {m.agent_task_success * 100:.1f}% | ≥ 85.0% | {'✅' if m.agent_task_success >= 0.85 else '⚠️'} |",
            f"| **P95 Latency** | {m.latency_p95_ms:.1f}ms | ≤ 5000.0ms | {'✅' if m.latency_p95_ms <= 5000 else '⚠️'} |",
            f"| **Estimated Cost** | ${m.estimated_cost_usd:.6f} | — | ℹ️ |",
            "",
        ]

        if run.block_reasons:
            lines.extend([
                "> [!CAUTION]",
                "> ### RELEASE BLOCKED DUE TO CRITICAL FAILURES:",
            ])
            for r in run.block_reasons:
                lines.append(f"> - {r}")
            lines.append("")

        if comparison and comparison.deltas:
            lines.extend([
                "---",
                f"## 2. Baseline Comparison vs {comparison.baseline_version}",
                "",
                f"**Release Recommendation:** {comparison.summary}",
                "",
                "| Metric | Current | Baseline | Delta | Delta % | Trend |",
                "| :--- | :--- | :--- | :--- | :--- | :--- |",
            ])
            for d in comparison.deltas:
                trend_icon = "🟢" if d.status == "improved" else ("🔴" if d.status == "regressed" else "⚪")
                lines.append(
                    f"| `{d.metric_name}` | {d.current_value:.4f} | {d.baseline_value:.4f} | {d.delta:+.4f} | {d.delta_percentage:+.1f}% | {trend_icon} {d.status} |"
                )
            lines.append("")

        # Failure Analysis Section
        failed_cases = [c for c in run.cases if not c.passed]
        lines.extend([
            "---",
            f"## 3. Case Outcomes ({run.metrics.passed_scenarios}/{run.metrics.total_scenarios} Passed)",
            "",
            "| Scenario ID | Category | Status | Grader | Reason / Details |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ])
        for c in run.cases:
            status = "PASSED ✅" if c.passed else "FAILED 🛑"
            reason = c.grading.reason or ("Satisfied" if c.passed else "Failed")
            lines.append(
                f"| `{c.scenario_id}` | `{c.category.value}` | {status} | `{c.grading.grader_name}` | {reason} |"
            )
        lines.append("")

        if failed_cases:
            lines.extend([
                "> [!WARNING]",
                f"> ### {len(failed_cases)} Scenario(s) Failed Evaluation Criteria",
                "",
            ])
        else:
            lines.extend(["All evaluated scenarios completed with 100% pass rate. ✅", ""])

        return "\n".join(lines)

    @classmethod
    def save_report(
        cls,
        run: EvaluationRun,
        comparison: BaselineComparisonResult | None = None,
        output_dir: str | Path = "evals/reports",
    ) -> tuple[Path, Path]:
        """Write both JSON and Markdown report files to disk."""
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        stem = f"eval-report-{run.kairo_version}-{run.run_id}"
        json_path = out_dir / f"{stem}.json"
        md_path = out_dir / f"{stem}.md"

        with open(json_path, "w", encoding="utf-8") as f:
            f.write(run.model_dump_json(indent=2))

        md_content = cls.generate_markdown(run, comparison)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        return json_path, md_path

    @classmethod
    def save_json(cls, run: EvaluationRun, output_path: str | Path) -> Path:
        """Save evaluation run model to target JSON file."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(run.model_dump_json(indent=2))
        return out

    @classmethod
    def save_markdown(
        cls,
        run: EvaluationRun,
        output_path: str | Path,
        comparison: BaselineComparisonResult | None = None,
    ) -> Path:
        """Save evaluation report markdown to target file."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        content = cls.generate_markdown(run, comparison)
        with open(out, "w", encoding="utf-8") as f:
            f.write(content)
        return out
