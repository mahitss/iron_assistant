"""Kairo Continuous Evaluation, Benchmarking, Regression Testing & Improvement Governance (Task 104)."""

from app.evaluation.baseline import BaselineManager
from app.evaluation.comparison import RegressionDetector
from app.evaluation.domain import (
    BaselineType,
    EvaluationBaseline,
    EvaluationCase,
    EvaluationComparison,
    EvaluationDataset,
    EvaluationDatasetVersion,
    EvaluationEvidence,
    EvaluationFixture,
    EvaluationGate,
    EvaluationReview,
    EvaluationRun as DomainEvaluationRun,
    EvaluationRunCase,
    EvaluationScenario as DomainEvaluationScenario,
    EvaluationSuite,
    ExecutionMode,
    GateStatus,
    ImprovementExperiment,
    ImprovementProposal,
    MetricMeasurement,
    MetricType,
    RegressionCategory,
    RegressionFinding,
    RegressionSeverity,
    ReplayReproducibility,
    ReviewStatus,
    RunStatus,
    ScenarioClass,
)
from app.evaluation.grader import (
    CitationGrader,
    ContextAndMemoryGrader,
    DeterministicGrader,
    JudgeRubric,
    RoutingGrader,
)
from app.evaluation.improvement_governance import ImprovementGovernanceEngine
from app.evaluation.metrics import MetricsCalculator
from app.evaluation.metrics_engine import StatisticalMetricsCalculator, SubsystemMetricsScorer
from app.evaluation.regression_engine import ContinuousRegressionEngine
from app.evaluation.registry import ScenarioRegistry
from app.evaluation.report import ReportGenerator
from app.evaluation.report_generator import ComprehensiveReportGenerator
from app.evaluation.run_engine import ContinuousRunEngine
from app.evaluation.runner import EvaluationRunner
from app.evaluation.safety import EvaluationSandbox, TraceSanitizer
from app.evaluation.scenario import ScenarioBuilder, ScenarioLoader
from app.evaluation.scenario_engine import ScenarioEngine
from app.evaluation.schemas import (
    BaselineComparisonResult,
    BaselineDelta,
    BaselineMetrics,
    ContinuousEvaluationDashboardDTO,
    EvalMode,
    EvalRunStatus,
    EvaluationCaseResult,
    EvaluationRun,
    EvaluationScenario,
    GradingMethod,
    GradingResult,
    ImprovementProposalCreateRequest,
    ImprovementReviewRequest,
    MetricSummary,
    ScenarioCategory,
    SecurityExpectations,
)
from app.evaluation.service import ContinuousEvaluationService

__all__ = [
    # Legacy interfaces
    "BaselineComparisonResult",
    "BaselineDelta",
    "BaselineManager",
    "BaselineMetrics",
    "CitationGrader",
    "ContextAndMemoryGrader",
    "DeterministicGrader",
    "EvalMode",
    "EvalRunStatus",
    "EvaluationCaseResult",
    "EvaluationRun",
    "EvaluationRunner",
    "EvaluationSandbox",
    "EvaluationScenario",
    "GradingMethod",
    "GradingResult",
    "JudgeRubric",
    "MetricSummary",
    "MetricsCalculator",
    "RegressionDetector",
    "ReportGenerator",
    "RoutingGrader",
    "ScenarioBuilder",
    "ScenarioCategory",
    "ScenarioLoader",
    "ScenarioRegistry",
    "SecurityExpectations",
    "TraceSanitizer",
    # Task 104 continuous evaluation additions
    "ContinuousEvaluationService",
    "ContinuousRunEngine",
    "ContinuousRegressionEngine",
    "ImprovementGovernanceEngine",
    "ScenarioEngine",
    "StatisticalMetricsCalculator",
    "SubsystemMetricsScorer",
    "ComprehensiveReportGenerator",
    "ExecutionMode",
    "ReplayReproducibility",
    "ScenarioClass",
    "RunStatus",
    "GateStatus",
    "ReviewStatus",
    "RegressionCategory",
    "RegressionSeverity",
    "BaselineType",
    "MetricType",
    "EvaluationSuite",
    "EvaluationCase",
    "EvaluationDataset",
    "EvaluationDatasetVersion",
    "EvaluationFixture",
    "EvaluationBaseline",
    "EvaluationRunCase",
    "MetricMeasurement",
    "EvaluationComparison",
    "RegressionFinding",
    "ImprovementProposal",
    "ImprovementExperiment",
    "EvaluationEvidence",
    "EvaluationGate",
    "EvaluationReview",
    "ContinuousEvaluationDashboardDTO",
    "ImprovementProposalCreateRequest",
    "ImprovementReviewRequest",
]
