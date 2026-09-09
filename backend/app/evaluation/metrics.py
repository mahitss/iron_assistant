"""Evaluation metrics computation and statistical aggregation."""

import math
from typing import Sequence
from app.evaluation.schemas import EvaluationCaseResult, MetricSummary, ScenarioCategory


# Model pricing rates per 1,000 tokens (for estimation)
MODEL_RATES = {
    "openrouter/free": 0.0,
    "gemini": 0.00015,
    "gpt-4o-mini": 0.00015,
    "gpt-4o": 0.0025,
    "claude-3-5-sonnet": 0.003,
}


class MetricsCalculator:
    """Computes quantitative metrics and percentiles across evaluation runs."""

    @staticmethod
    def percentile(data: Sequence[float], p: float) -> float:
        """Calculate p-th percentile (0.0 to 1.0) using linear interpolation."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * p
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return float(sorted_data[int(k)])
        d0 = sorted_data[int(f)] * (c - k)
        d1 = sorted_data[int(c)] * (k - f)
        return float(d0 + d1)

    @classmethod
    def compute_summary(cls, cases: list[EvaluationCaseResult]) -> MetricSummary:
        """Aggregate list of case results into full MetricSummary."""
        summary = MetricSummary()
        if not cases:
            return summary

        summary.total_scenarios = len(cases)
        summary.passed_scenarios = sum(1 for c in cases if c.passed)
        summary.failed_scenarios = sum(1 for c in cases if not c.passed)
        summary.flaky_scenarios = sum(1 for c in cases if c.flaky)
        summary.pass_rate = round(summary.passed_scenarios / summary.total_scenarios, 4)

        # Categorized metrics
        sec_cases = [c for c in cases if c.category == ScenarioCategory.SECURITY]
        if sec_cases:
            summary.security_pass_rate = round(
                sum(1 for c in sec_cases if c.passed) / len(sec_cases), 4
            )
        else:
            summary.security_pass_rate = 1.0

        tool_cases = [c for c in cases if c.category == ScenarioCategory.TOOLS]
        if tool_cases:
            summary.tool_selection_accuracy = round(
                sum(c.grading.details.get("selection_accuracy", 1.0 if c.passed else 0.0) for c in tool_cases)
                / len(tool_cases),
                4,
            )
            summary.tool_argument_accuracy = round(
                sum(c.grading.details.get("argument_accuracy", 1.0 if c.passed else 0.0) for c in tool_cases)
                / len(tool_cases),
                4,
            )
            summary.tool_efficiency = round(
                sum(c.grading.details.get("efficiency", 1.0) for c in tool_cases) / len(tool_cases), 4
            )
        else:
            summary.tool_selection_accuracy = 1.0
            summary.tool_argument_accuracy = 1.0
            summary.tool_efficiency = 1.0

        routing_cases = [c for c in cases if c.category == ScenarioCategory.ROUTING]
        if routing_cases:
            summary.routing_accuracy = round(
                sum(1 for c in routing_cases if c.passed) / len(routing_cases), 4
            )
            summary.fallback_success_rate = round(
                sum(c.grading.details.get("fallback_success", 1.0) for c in routing_cases) / len(routing_cases),
                4,
            )
        else:
            summary.routing_accuracy = 1.0
            summary.fallback_success_rate = 1.0

        ctx_cases = [c for c in cases if c.category in (ScenarioCategory.CONTEXT, ScenarioCategory.PROJECTS)]
        if ctx_cases:
            summary.context_precision = round(
                sum(c.grading.details.get("precision", 1.0 if c.passed else 0.0) for c in ctx_cases)
                / len(ctx_cases),
                4,
            )
            summary.context_recall = round(
                sum(c.grading.details.get("recall", 1.0 if c.passed else 0.0) for c in ctx_cases)
                / len(ctx_cases),
                4,
            )
        else:
            summary.context_precision = 1.0
            summary.context_recall = 1.0

        mem_cases = [c for c in cases if c.category == ScenarioCategory.MEMORY]
        if mem_cases:
            summary.memory_precision = round(
                sum(c.grading.details.get("precision", 1.0 if c.passed else 0.0) for c in mem_cases)
                / len(mem_cases),
                4,
            )
            summary.memory_recall = round(
                sum(c.grading.details.get("recall", 1.0 if c.passed else 0.0) for c in mem_cases)
                / len(mem_cases),
                4,
            )
        else:
            summary.memory_precision = 1.0
            summary.memory_recall = 1.0

        know_cases = [c for c in cases if c.category == ScenarioCategory.KNOWLEDGE]
        if know_cases:
            summary.knowledge_precision = round(
                sum(c.grading.details.get("precision", 1.0 if c.passed else 0.0) for c in know_cases)
                / len(know_cases),
                4,
            )
        else:
            summary.knowledge_precision = 1.0

        res_cases = [c for c in cases if c.category == ScenarioCategory.RESEARCH]
        if res_cases:
            summary.citation_groundedness = round(
                sum(c.grading.details.get("groundedness", 1.0 if c.passed else 0.0) for c in res_cases)
                / len(res_cases),
                4,
            )
        else:
            summary.citation_groundedness = 1.0

        agent_cases = [c for c in cases if c.category == ScenarioCategory.AGENTS]
        if agent_cases:
            summary.agent_task_success = round(
                sum(1 for c in agent_cases if c.passed) / len(agent_cases), 4
            )
            summary.agent_overhead = round(
                sum(c.grading.details.get("overhead_ratio", 0.0) for c in agent_cases) / len(agent_cases), 4
            )
        else:
            summary.agent_task_success = 1.0
            summary.agent_overhead = 0.0

        auto_cases = [c for c in cases if c.category == ScenarioCategory.AUTOMATION]
        if auto_cases:
            summary.workflow_success_rate = round(
                sum(1 for c in auto_cases if c.passed) / len(auto_cases), 4
            )
        else:
            summary.workflow_success_rate = 1.0

        # Latencies
        latencies = [c.duration_ms for c in cases]
        summary.latency_p50_ms = round(cls.percentile(latencies, 0.50), 2)
        summary.latency_p95_ms = round(cls.percentile(latencies, 0.95), 2)
        summary.latency_p99_ms = round(cls.percentile(latencies, 0.99), 2)

        # Tokens & Cost
        summary.total_tokens = sum(c.tokens_used for c in cases)
        summary.estimated_cost_usd = round(sum(c.cost_usd for c in cases), 6)

        # Overall Quality Score (Weighted Product Quality, Section 69: Security remains separate)
        # 30% task completion, 20% tool accuracy, 15% context, 15% research, 10% agent efficiency, 10% reliability
        overall = (
            0.30 * summary.pass_rate
            + 0.20 * summary.tool_selection_accuracy
            + 0.15 * summary.context_precision
            + 0.15 * summary.citation_groundedness
            + 0.10 * summary.agent_task_success
            + 0.10 * summary.workflow_success_rate
        )
        summary.overall_quality_score = round(overall * 100.0, 1)

        return summary
