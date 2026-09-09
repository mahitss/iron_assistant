"""SQLAlchemy ORM models for persisting evaluation runs and benchmark outcomes."""

from datetime import UTC, datetime
from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class EvaluationRunModel(Base):
    """Persisted record of an evaluation or benchmark suite run."""

    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    suite_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    dataset_version: Mapped[str] = mapped_column(String(32), nullable=False)
    kairo_version: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    git_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    # Key aggregated metrics
    pass_rate: Mapped[float] = mapped_column(Float, default=0.0)
    security_pass_rate: Mapped[float] = mapped_column(Float, default=1.0)
    overall_quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    latency_p95_ms: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)

    security_gate_passed: Mapped[bool] = mapped_column(Boolean, default=True)
    release_blocked: Mapped[bool] = mapped_column(Boolean, default=False)

    metrics_json: Mapped[dict] = mapped_column(JSON, default=dict)
    block_reasons_json: Mapped[list] = mapped_column(JSON, default=list)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0)


class EvaluationCaseModel(Base):
    """Persisted outcome of a single evaluation scenario within a run."""

    __tablename__ = "evaluation_cases"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    scenario_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    scenario_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    passed: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    flaky: Mapped[bool] = mapped_column(Boolean, default=False)

    grader_name: Mapped[str] = mapped_column(String(64), default="")
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    grading_json: Mapped[dict] = mapped_column(JSON, default=dict)
    trace_sanitized_json: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
