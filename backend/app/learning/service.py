"""Central LearningService coordinator for Kairo Adaptive Learning & Strategy Optimization (Task 43)."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from app.learning.decay import EnvironmentalDecayManager
from app.learning.evaluator import StrategyEvaluator
from app.learning.experiences import Experience, ExperienceType
from app.learning.experimentation import Experiment, ExperimentStatus
from app.learning.failures import FailureManager, PreFlightWarning
from app.learning.feedback import FeedbackIngestor, FeedbackItem
from app.learning.optimizer import RankedStrategy, StrategyOptimizer
from app.learning.patterns import FailurePattern
from app.learning.personalization import PersonalizationManager, UserPreferenceProfile
from app.learning.promotion import PromotionRecord, StrategyPromoter
from app.learning.provenance import StrategyProvenanceRecord
from app.learning.reliability import ReliabilityTracker
from app.learning.rollback import RollbackRecord, StrategyRollbacker
from app.learning.safety import LearningSafetyGuard
from app.learning.signals import LearningSignal, SignalSource, SignalType
from app.learning.strategies import Strategy, StrategyStatus
from app.learning.strategy_store import StrategyStore

logger = logging.getLogger("kairo.learning.service")


def utc_now() -> datetime:
    return datetime.now(UTC)


class LearningService:
    """Enterprise coordinator for continuous learning, strategy optimization, and governed promotion."""

    def __init__(self) -> None:
        # Core Subsystems
        self.strategy_store = StrategyStore()
        self.optimizer = StrategyOptimizer()
        self.evaluator = StrategyEvaluator()
        self.promoter = StrategyPromoter()
        self.rollbacker = StrategyRollbacker()
        self.reliability = ReliabilityTracker()
        self.failure_manager = FailureManager()
        self.feedback_ingestor = FeedbackIngestor()
        self.decay_manager = EnvironmentalDecayManager()
        self.personalization = PersonalizationManager()

        # In-memory primary registries
        self._experiences: dict[str, Experience] = {}
        self._signals: dict[str, LearningSignal] = {}
        self._experiments: dict[str, Experiment] = {}
        self._provenance: dict[str, list[StrategyProvenanceRecord]] = {}

        # Pre-populate default canonical strategies
        self._seed_default_strategies()

    def _seed_default_strategies(self) -> None:
        """Seed baseline active strategies for core domains."""
        defaults = [
            Strategy(
                strategy_id="strat-default-coding",
                domain="coding",
                description="Test-driven incremental patch with automated verification and linting.",
                status=StrategyStatus.ACTIVE,
                success_rate=0.92,
                verification_rate=0.95,
                sample_size=45,
                confidence="HIGH",
            ),
            Strategy(
                strategy_id="strat-default-deployment",
                domain="deployment",
                description="Zero-downtime deployment with health check triangulation and canary probe.",
                status=StrategyStatus.ACTIVE,
                success_rate=0.94,
                verification_rate=0.96,
                sample_size=38,
                confidence="HIGH",
            ),
            Strategy(
                strategy_id="strat-default-research",
                domain="research",
                description="Multi-source triangulation with citation extraction and source existence checks.",
                status=StrategyStatus.ACTIVE,
                success_rate=0.88,
                verification_rate=0.91,
                sample_size=25,
                confidence="MEDIUM",
            ),
        ]
        for s in defaults:
            self.strategy_store.save(s)

    # =========================================================================
    # EXPERIENCES & SIGNAL DERIVATION
    # =========================================================================

    def record_experience(
        self,
        strategy: str,
        actions: list[Any] | None = None,
        observations: list[Any] | None = None,
        verification_result: dict[str, Any] | None = None,
        outcome: ExperienceType | str = ExperienceType.SUCCESS,
        task_id: str | None = None,
        goal_type: str = "GENERAL",
        plan_type: str | None = None,
        context_reference: str | None = None,
        duration_ms: float = 0.0,
        cost: float = 0.0,
        retries: int = 0,
        failures: list[dict[str, Any]] | None = None,
        scope: dict[str, Any] | None = None,
    ) -> Experience:
        """Record task execution experience, sanitize data, update metrics, and derive signals."""
        if isinstance(outcome, str):
            try:
                outcome_enum = ExperienceType(outcome.upper())
            except ValueError:
                outcome_enum = ExperienceType.UNKNOWN
        else:
            outcome_enum = outcome

        v_res = verification_result or {}
        exp = Experience(
            task_id=task_id,
            goal_type=goal_type,
            plan_type=plan_type,
            strategy=strategy,
            context_reference=context_reference,
            actions=actions or [],
            observations=observations or [],
            verification_result=v_res,
            outcome=outcome_enum,
            duration_ms=duration_ms,
            cost=cost,
            retries=retries,
            failures=failures or [],
            scope=dict(scope or {}),
        )
        self._experiences[exp.experience_id] = exp

        # 1. Update Strategy execution metrics if known
        strat_obj = self.strategy_store.get(strategy)
        if strat_obj:
            is_success = outcome_enum in [ExperienceType.SUCCESS, ExperienceType.RECOVERY_SUCCESS]
            is_verified = v_res.get("status") == "PASS" or v_res.get("is_verified") is True
            strat_obj.record_execution(
                was_successful=is_success,
                was_verified=is_verified,
                duration_ms=duration_ms,
                cost=cost,
            )
            self.strategy_store.save(strat_obj)

            # Check regression and trigger rollback if needed
            has_regressed, reg_msg = self.rollbacker.check_regression(strat_obj)
            if has_regressed and strat_obj.status == StrategyStatus.ACTIVE:
                self.rollbacker.rollback(strat_obj, reason=reg_msg)

        # 2. Derive False Success / False Failure Signals (Spec 29, 30)
        is_verif_fail = verification_result.get("status") in ["FAIL", "FAILED"]
        is_verif_pass = verification_result.get("status") in ["PASS", "SUCCESS"]

        if outcome == ExperienceType.SUCCESS and is_verif_fail:
            # False success! Claimed success but verification failed
            sig = LearningSignal.create_false_success_signal(strategy, "SUCCESS", verification_result)
            self._signals[sig.signal_id] = sig
        elif outcome == ExperienceType.FAILURE and is_verif_pass:
            # False failure!
            sig = LearningSignal.create_false_failure_signal(strategy, verification_result)
            self._signals[sig.signal_id] = sig

        # 3. Cluster failures if failed
        if outcome in [ExperienceType.FAILURE, ExperienceType.PLAN_FAILURE, ExperienceType.TOOL_FAILURE]:
            err_msg = "; ".join(str(f.get("error", f)) for f in (failures or [])) or "Execution failure"
            self.failure_manager.record_failure(
                domain=goal_type,
                error_message=err_msg,
                evidence_item={"experience_id": exp.experience_id, "strategy": strategy},
            )

        return exp

    def get_experience(self, experience_id: str) -> Experience | None:
        return self._experiences.get(experience_id)

    def list_experiences(
        self,
        strategy: str | None = None,
        outcome: ExperienceType | None = None,
        goal_type: str | None = None,
    ) -> list[Experience]:
        results = list(self._experiences.values())
        if strategy:
            results = [e for e in results if e.strategy == strategy]
        if outcome:
            results = [e for e in results if e.outcome == outcome]
        if goal_type:
            results = [e for e in results if e.goal_type == goal_type]
        return results

    # =========================================================================
    # SIGNALS & FEEDBACK
    # =========================================================================

    def record_signal(
        self,
        source: SignalSource,
        signal_type: SignalType,
        strength: float = 1.0,
        evidence: dict[str, Any] | None = None,
        confidence: str = "MEDIUM",
        scope: dict[str, Any] | None = None,
    ) -> LearningSignal:
        sig = LearningSignal(
            source=source,
            signal_type=signal_type,
            strength=strength,
            evidence=dict(evidence or {}),
            confidence=confidence,
            scope=dict(scope or {}),
        )
        self._signals[sig.signal_id] = sig
        return sig

    def list_signals(self, signal_type: SignalType | None = None) -> list[LearningSignal]:
        signals = list(self._signals.values())
        if signal_type:
            signals = [s for s in signals if s.signal_type == signal_type]
        return signals

    def submit_user_feedback(
        self,
        user_id: str,
        target_id: str,
        feedback_type: str,
        rating: int | None = None,
        comment: str | None = None,
        project_id: str | None = None,
        scope: dict[str, Any] | None = None,
    ) -> tuple[bool, str]:
        item = FeedbackItem(
            user_id=user_id,
            project_id=project_id,
            target_id=target_id,
            feedback_type=feedback_type,
            rating=rating,
            comment=comment,
            scope=dict(scope or {}),
        )
        accepted, msg = self.feedback_ingestor.ingest(item)
        if accepted:
            # Emit signal
            sig_type = SignalType.POSITIVE if feedback_type in ["positive", "preference"] else SignalType.NEGATIVE
            self.record_signal(
                source=SignalSource.USER_FEEDBACK,
                signal_type=sig_type,
                strength=0.75,
                evidence={"feedback_id": item.feedback_id, "rating": rating, "comment": comment},
                scope=item.scope,
            )
        return accepted, msg

    # =========================================================================
    # STRATEGY LIFECYCLE & OPTIMIZER
    # =========================================================================

    def register_strategy(
        self,
        domain: str,
        description: str,
        prerequisites: list[str] | None = None,
        expected_outcome: dict[str, Any] | None = None,
        scope: dict[str, Any] | None = None,
        status: StrategyStatus = StrategyStatus.CANDIDATE,
    ) -> tuple[Strategy, str]:
        """Register a candidate or active strategy with safety checks (Spec 170, 171)."""
        strat = Strategy(
            domain=domain,
            description=description,
            prerequisites=prerequisites or [],
            expected_outcome=expected_outcome or {},
            scope=dict(scope or {}),
            status=status,
        )

        safe, msg = LearningSafetyGuard.check_strategy_safety(strat)
        if not safe:
            strat.status = StrategyStatus.BLOCKED
            self.strategy_store.save(strat)
            return strat, msg

        self.strategy_store.save(strat)
        # Register provenance
        prov = StrategyProvenanceRecord(
            strategy_id=strat.strategy_id,
            version=strat.version,
            rationale="Initial registration",
        )
        self._provenance.setdefault(strat.strategy_id, []).append(prov)
        return strat, "Strategy registered successfully."

    def get_strategy(self, strategy_id: str) -> Strategy | None:
        strat = self.strategy_store.get(strategy_id)
        if strat:
            # Apply temporal decay check
            self.decay_manager.apply_temporal_decay(strat)
        return strat

    def list_strategies(
        self,
        domain: str | None = None,
        status: StrategyStatus | None = None,
        project_id: str | None = None,
    ) -> list[Strategy]:
        strategies = self.strategy_store.list_strategies(domain=domain, status=status, project_id=project_id)
        for s in strategies:
            self.decay_manager.apply_temporal_decay(s)
        return strategies

    def recommend_strategy(
        self,
        domain: str,
        user_id: str = "default_user",
        project_id: str | None = None,
    ) -> RankedStrategy | None:
        """Get best strategy recommendation considering domain, scope, and user preference."""
        # Check user profile
        profile = self.personalization.get_profile(user_id, project_id)
        preferred_id = profile.preferred_strategies.get(domain)
        if preferred_id:
            preferred = self.strategy_store.get(preferred_id)
            if preferred and preferred.status in [StrategyStatus.ACTIVE, StrategyStatus.EXPERIMENTAL]:
                return RankedStrategy(
                    strategy=preferred,
                    rank_score=1.0,
                    factors={"user_preference": 1.0},
                    explanation="Selected based on explicit user preference for this project.",
                )

        strategies = self.list_strategies(domain=domain, project_id=project_id)
        return self.optimizer.select_best_strategy(strategies, domain=domain)

    def promote_strategy(
        self,
        strategy_id: str,
        approved_by: str,
        reason: str = "Empirical criteria satisfied",
    ) -> tuple[bool, str, PromotionRecord | None]:
        strat = self.strategy_store.get(strategy_id)
        if not strat:
            return False, f"Strategy '{strategy_id}' not found.", None

        success, msg, rec = self.promoter.promote(strat, approved_by=approved_by, reason=reason)
        if success:
            self.strategy_store.save(strat)
        return success, msg, rec

    def rollback_strategy(
        self,
        strategy_id: str,
        rolled_back_by: str = "operator",
        reason: str | None = None,
    ) -> tuple[bool, str, RollbackRecord | None]:
        strat = self.strategy_store.get(strategy_id)
        if not strat:
            return False, f"Strategy '{strategy_id}' not found.", None

        success, msg, rec = self.rollbacker.rollback(strat, rolled_back_by=rolled_back_by, reason=reason)
        if success:
            self.strategy_store.save(strat)
        return success, msg, rec

    # =========================================================================
    # EXPERIMENTS & CANARY
    # =========================================================================

    def create_experiment(
        self,
        name: str,
        domain: str,
        baseline_strategy_id: str,
        candidate_strategy_id: str,
        target_sample_size: int = 50,
    ) -> Experiment:
        exp = Experiment(
            name=name,
            domain=domain,
            baseline_strategy_id=baseline_strategy_id,
            candidate_strategy_id=candidate_strategy_id,
            target_sample_size=target_sample_size,
        )
        self._experiments[exp.experiment_id] = exp
        return exp

    def get_experiment(self, experiment_id: str) -> Experiment | None:
        return self._experiments.get(experiment_id)

    def list_experiments(self, status: ExperimentStatus | None = None) -> list[Experiment]:
        experiments = list(self._experiments.values())
        if status:
            experiments = [e for e in experiments if e.status == status]
        return experiments

    # =========================================================================
    # FAILURES & PRE-FLIGHT
    # =========================================================================

    def check_pre_flight_warning(self, workflow_name: str, domain: str = "system") -> PreFlightWarning | None:
        return self.failure_manager.check_pre_flight(workflow_name, domain)

    def list_failure_patterns(self, domain: str | None = None) -> list[FailurePattern]:
        return self.failure_manager.list_patterns(domain)

    # =========================================================================
    # SUMMARY & METRICS
    # =========================================================================

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_experiences": len(self._experiences),
            "total_signals": len(self._signals),
            "total_strategies": len(self.strategy_store.list_strategies()),
            "total_failure_patterns": len(self.failure_manager.list_patterns()),
            "total_experiments": len(self._experiments),
            "tool_reliabilities": self.reliability.get_all_tool_reliability(),
            "provider_reliabilities": self.reliability.get_all_provider_reliability(),
        }
