"""Command-line interface for running and inspecting Kairo evaluations (Section 40)."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Ensure UTF-8 output encoding across platforms
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
from app.evaluation.baseline import BaselineManager
from app.evaluation.comparison import RegressionDetector
from app.evaluation.registry import ScenarioRegistry
from app.evaluation.report import ReportGenerator
from app.evaluation.runner import EvaluationRunner
from app.evaluation.schemas import EvalMode


def build_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser for kairo eval commands."""
    parser = argparse.ArgumentParser(prog="kairo eval", description="Kairo Evaluation & Benchmarking CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list command
    list_p = subparsers.add_parser("list", help="List registered scenarios and suites")
    list_p.add_argument("--category", "-c", help="Filter by scenario category")
    list_p.add_argument("--suite", "-s", help="Filter by test suite")

    # run command
    run_p = subparsers.add_parser("run", help="Execute evaluation scenarios or benchmark suites")
    run_p.add_argument("--suite", "-s", default="full", help="Suite name to execute (e.g. 'security', 'routing', 'full')")
    run_p.add_argument("--scenario", help="Execute a single scenario ID (e.g. 'github.ci_failure.001')")
    run_p.add_argument("--multi-run", type=int, default=1, help="Run count per scenario for flakiness detection")
    run_p.add_argument("--mode", default="LOCAL", choices=["LOCAL", "CI", "STAGING"], help="Execution mode")
    run_p.add_argument("--report", action="store_true", default=True, help="Generate JSON and Markdown reports")
    run_p.add_argument("--scenarios-dir", default="evals/scenarios", help="Directory of scenarios")

    # compare command
    comp_p = subparsers.add_parser("compare", help="Compare an evaluation run against release baseline")
    comp_p.add_argument("--baseline", default="v1.0.0", help="Baseline release version to compare against")
    comp_p.add_argument("--run-file", help="Path to evaluation run JSON report")

    # report command
    rep_p = subparsers.add_parser("report", help="Generate or view formatted evaluation report")
    rep_p.add_argument("--run-file", required=True, help="Path to evaluation run JSON report")
    rep_p.add_argument("--format", choices=["json", "md"], default="md", help="Output report format")

    return parser


async def handle_list(args: argparse.Namespace, registry: ScenarioRegistry) -> int:
    """Print registered scenarios and available suites."""
    print("=== KAIRO EVALUATION SCENARIOS & SUITES ===")
    print(f"Available Suites: {', '.join(registry.list_suites())}\n")

    scenario = getattr(args, "scenario", None)
    suite = getattr(args, "suite", None)
    category = getattr(args, "category", None)

    if scenario or suite:
        scenarios = registry.list_by_suite(suite) if suite else registry.list_all()
    elif category:
        scenarios = registry.list_by_category(category)
    else:
        scenarios = registry.list_all()

    print(f"Found {len(scenarios)} scenario(s):")
    for s in scenarios:
        sec_marker = "[SECURITY]" if s.category.value == "security" else ""
        print(f"  - {s.id:<32} [{s.category.value:<12}] {sec_marker} {s.name}")
    return 0


async def handle_run(args: argparse.Namespace, registry: ScenarioRegistry) -> int:
    """Run specified scenarios or suite and output results."""
    runner = EvaluationRunner(registry=registry, mode=EvalMode(args.mode), mock_mode=True)

    if args.scenario:
        sc = registry.get(args.scenario)
        if not sc:
            print(f"Error: Scenario '{args.scenario}' not found in registry.", file=sys.stderr)
            return 1
        print(f"Running single scenario: {sc.id} ({sc.name})...")
        res = await runner.run_scenario_multi(sc, runs_count=args.multi_run)
        print(f"Result: {'PASSED ✅' if res.passed else 'FAILED ❌'}")
        print(f"Score: {res.score} | Duration: {res.duration_ms:.1f}ms")
        if not res.passed:
            print(f"Failure Reason: {res.grading.reason}")
        return 0 if res.passed else 1

    print(f"Executing suite: '{args.suite}' (multi-run={args.multi_run})...")
    run = await runner.run_suite(args.suite, multi_run_count=args.multi_run)

    # Print summary to stdout
    m = run.metrics
    print("\n---------------------------------------")
    print(f"KAIRO EVALUATION: {run.suite_name.upper()}")
    print("---------------------------------------")
    print(f"VERSION:             {run.kairo_version}")
    print(f"OVERALL QUALITY:     {m.overall_quality_score:.1f}%")
    print(f"SECURITY PASS RATE:  {m.security_pass_rate * 100:.1f}% {'✅' if run.security_gate_passed else '🛑 BLOCKED'}")
    print(f"TOOL ACCURACY:       {m.tool_selection_accuracy * 100:.1f}%")
    print(f"CONTEXT PRECISION:   {m.context_precision * 100:.1f}%")
    print(f"AGENT SUCCESS:       {m.agent_task_success * 100:.1f}%")
    print(f"RESEARCH GROUNDED:   {m.citation_groundedness * 100:.1f}%")
    print(f"P95 LATENCY:         {m.latency_p95_ms:.1f}ms")
    print(f"EST. COST:           ${m.estimated_cost_usd:.6f}")
    print(f"SCENARIOS:           {m.passed_scenarios}/{m.total_scenarios} passed ({m.pass_rate * 100:.1f}%)")
    print("---------------------------------------")

    if run.release_blocked:
        print("🛑 RELEASE BLOCKED:")
        for r in run.block_reasons:
            print(f"  - {r}")

    if args.report:
        json_path, md_path = ReportGenerator.save_report(run)
        print(f"\nReports generated:\n  - JSON: {json_path}\n  - Markdown: {md_path}")

    return 0 if not run.release_blocked else 2


async def handle_compare(args: argparse.Namespace) -> int:
    """Compare evaluation run report with baseline."""
    bm = BaselineManager()
    base = bm.get_baseline(args.baseline)
    if not base:
        print(f"Error: Baseline '{args.baseline}' not found.", file=sys.stderr)
        return 1

    from app.evaluation.schemas import EvaluationRun
    if args.run_file:
        with open(args.run_file, "r", encoding="utf-8") as f:
            run_data = json.load(f)
        run = EvaluationRun.model_validate(run_data)
    else:
        print("Error: --run-file required for comparison.", file=sys.stderr)
        return 1

    comparison = RegressionDetector.compare(run, base)
    print(f"\n=== COMPARISON vs BASELINE {base.version} ===")
    print(f"Status: {'RELEASE APPROVED ✅' if not comparison.release_blocked else 'RELEASE BLOCKED 🛑'}")
    print(f"Summary: {comparison.summary}\n")
    for d in comparison.deltas:
        print(f"  {d.metric_name:<28} : {d.current_value:.4f} (base: {d.baseline_value:.4f}) [{d.delta:+.4f}] -> {d.status.upper()}")
    return 0 if not comparison.release_blocked else 1


def main() -> None:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args()

    registry = ScenarioRegistry()
    # Discover default scenarios
    scenarios_dir = Path("evals/scenarios")
    if scenarios_dir.exists():
        registry.load_directory(scenarios_dir)

    datasets_dir = Path("evals/datasets")
    if datasets_dir.exists():
        registry.load_directory(datasets_dir)

    if args.command == "list":
        code = asyncio.run(handle_list(args, registry))
    elif args.command == "run":
        code = asyncio.run(handle_run(args, registry))
    elif args.command == "compare":
        code = asyncio.run(handle_compare(args))
    elif args.command == "report":
        with open(args.run_file, "r", encoding="utf-8") as f:
            run_data = json.load(f)
        from app.evaluation.schemas import EvaluationRun
        run = EvaluationRun.model_validate(run_data)
        if args.format == "md":
            print(ReportGenerator.generate_markdown(run))
        else:
            print(run.model_dump_json(indent=2))
        code = 0
    else:
        parser.print_help()
        code = 1

    sys.exit(code)


if __name__ == "__main__":
    main()
