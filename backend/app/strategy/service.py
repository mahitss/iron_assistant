"""Master Coordinator Service for KAIRO Strategy Engine (Task 106).

Coordinates:
- Experience mining (Task 103), Evaluations (Task 104), Governed Experiments (Task 105)
- Statistical pattern detection and candidate synthesis
- Counterexample tracking and boundary condition analysis
- Applicability evaluation against real-time world-state and capability health
- Conflict detection between candidate strategies
- Multi-factor confidence scoring, temporal decay, and drift detection
- Bounded strategy composition
- Typed candidate advisory bridge to Task 94 Decision Intelligence
- Governance review, strategy versioning, and lifecycle promotion
- Canonical audit event dispatching
"""

from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.events.bus import get_event_bus
from app.events.schemas import Event
from app.security.emergency_stop import EmergencyStopService, get_emergency_stop_service
from app.strategy.applicability_engine import ApplicabilityEngine
from app.strategy.candidate_generator import CandidateGenerationEngine
from app.strategy.composition_engine import CompositionEngine, StrategyChain
from app.strategy.confidence_engine import ConfidenceAndDecayEngine, StrategyHealthReport
from app.strategy.conflict_engine import ConflictDetectionEngine
from app.strategy.counterexample_engine import CounterexampleEngine
from app.strategy.decision_bridge import DecisionBridge, DecisionCandidateBundle
from app.strategy.domain import (
    ApplicabilityStatus,
    ConflictType,
    EvidenceSourceType,
    ProposalStatus,
    ReviewDecision,
    Strategy,
    StrategyApplicability,
    StrategyCategory,
    StrategyCondition,
    StrategyConflict,
    StrategyContraindication,
    StrategyEvaluation,
    StrategyEvent,
    StrategyEvidence,
    StrategyFailureMode,
    StrategyFeedback,
    StrategyOutcome,
    StrategyPrecondition,
    StrategyProposal,
    StrategyReview,
    StrategyStatus,
    StrategySupersession,
    StrategyUsage,
    StrategyVersion,
    generate_id,
    utc_now,
)
from app.strategy.experience_miner import ExperienceMiningEngine
from app.strategy.meta_evaluator import MetaStrategyEvaluator
from app.strategy.pattern_detector import PatternDetectionEngine
from app.strategy.schemas import (
    StrategyCandidateContract,
    StrategyCreateRequest,
    StrategyDashboardResponse,
    StrategyFeedbackRequest,
    StrategyProposalCreateRequest,
    StrategyProposalReviewRequest,
    StrategySearchRequest,
    StrategyUpdateRequest,
)

logger = logging.getLogger("kairo.strategy.service")


class StrategyService:
    """Master domain coordinator for Kairo's Strategy and Adaptive Policy Engine."""

    def __init__(
        self,
        emergency_stop: Optional[EmergencyStopService] = None,
        db: Optional[Session] = None,
    ) -> None:
        self.emergency_stop = emergency_stop or get_emergency_stop_service()
        self.db = db
        self._lock = threading.RLock()

        # Sub-engines
        self.miner = ExperienceMiningEngine(min_cluster_samples=2)
        self.pattern_detector = PatternDetectionEngine(min_success_rate=0.60)
        self.candidate_generator = CandidateGenerationEngine()
        self.counterexample_engine = CounterexampleEngine()
        self.applicability_engine = ApplicabilityEngine()
        self.conflict_engine = ConflictDetectionEngine()
        self.confidence_engine = ConfidenceAndDecayEngine()
        self.composition_engine = CompositionEngine(max_depth=3)
        self.decision_bridge = DecisionBridge()
        self.meta_evaluator = MetaStrategyEvaluator()

        # In-memory stores
        self._strategies: Dict[str, Strategy] = {}
        self._versions: Dict[str, StrategyVersion] = {}
        self._evidences: Dict[str, StrategyEvidence] = {}
        self._applicabilities: Dict[str, StrategyApplicability] = {}
        self._usages: Dict[str, StrategyUsage] = {}
        self._feedbacks: Dict[str, StrategyFeedback] = {}
        self._conflicts: Dict[str, StrategyConflict] = {}
        self._proposals: Dict[str, StrategyProposal] = {}
        self._reviews: Dict[str, StrategyReview] = {}
        self._events: List[StrategyEvent] = []

    def _emit_event(self, event_type: str, strategy_id: str, payload: Dict[str, Any], version_id: Optional[str] = None) -> None:
        """Record and dispatch canonical strategy audit event."""
        evt = StrategyEvent(
            id=generate_id("sevt"),
            event_type=event_type,
            strategy_id=strategy_id,
            version_id=version_id,
            payload=payload,
            dispatched_at=utc_now(),
        )
        self._events.append(evt)
        try:
            bus = get_event_bus()
            bus.publish_sync(
                Event(
                    type=event_type,
                    source="strategy_service",
                    payload={"strategy_id": strategy_id, **payload},
                )
            )
        except Exception:
            pass  # Test and offline fallback

    # --------------------------------------------------------------------------
    # 1. Experience Mining & Pattern Synthesis
    # --------------------------------------------------------------------------

    def mine_and_synthesize_candidates(
        self,
        experiences: List[Dict[str, Any]],
        evaluations: Optional[List[Dict[str, Any]]] = None,
        experiments: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Strategy]:
        """Mine experiences, extract patterns, and synthesize strategy candidates."""
        with self._lock:
            clusters = self.miner.mine_experiences(experiences, evaluations, experiments)
            patterns = self.pattern_detector.detect_patterns(clusters)

            candidates: List[Strategy] = []
            for pat in patterns:
                # Find matching cluster evidences
                evidences: List[StrategyEvidence] = []
                for c in clusters:
                    if c.cluster_key.replace(":", "_") in pat.pattern_id:
                        evidences = c.evidences
                        break

                strat = self.candidate_generator.generate_candidate_strategy(pat, evidences)
                self._strategies[strat.id] = strat
                for v in strat.versions:
                    self._versions[v.id] = v
                for e in strat.evidences + strat.counterexamples:
                    self._evidences[e.id] = e
                    if e.is_counterexample:
                        self.counterexample_engine.register_counterexample(
                            strat.id,
                            e.claim,
                            e.environmental_context,
                            e.observed_metrics,
                            e.source_id,
                        )

                self._emit_event("strategy.candidate_created", strat.id, {
                    "name": strat.name,
                    "confidence": strat.confidence,
                    "frequency": pat.frequency,
                })
                candidates.append(strat)

            return candidates

    # --------------------------------------------------------------------------
    # 2. Strategy CRUD & Lifecycle Management
    # --------------------------------------------------------------------------

    def create_strategy(self, request: StrategyCreateRequest) -> Strategy:
        """Explicitly define a new Strategy (starts as CANDIDATE or DRAFT)."""
        with self._lock:
            strat_id = generate_id("strat")
            stable_id = f"strat_stable_{strat_id[6:]}"

            strat = Strategy(
                id=strat_id,
                stable_id=stable_id,
                name=request.name,
                category=request.category,
                objective=request.objective,
                recommended_approach=request.recommended_approach,
                lifecycle_status=StrategyStatus.CANDIDATE,
                domain_scope=request.domain_scope,
                tested_domain=request.tested_domain,
                supported_domain=request.supported_domain,
                unknown_domain=request.unknown_domain,
                validity_window_seconds=request.validity_window_seconds,
                is_safety_critical=request.is_safety_critical,
                provenance_type=request.provenance_type,
                provenance_id=request.provenance_id,
                created_at=utc_now(),
                updated_at=utc_now(),
            )

            # Initial Version
            version = StrategyVersion(
                id=generate_id("sver"),
                strategy_id=strat_id,
                version_number=1,
                change_reason="Initial manual creation",
                change_description="Created via API request",
                lifecycle_status=StrategyStatus.CANDIDATE,
                created_at=utc_now(),
            )
            version.calculate_checksum()
            strat.current_version_id = version.id
            strat.versions.append(version)
            self._versions[version.id] = version

            # Add Conditions
            for c in request.conditions:
                cond = StrategyCondition(
                    strategy_id=strat_id,
                    version_id=version.id,
                    condition_type=c.condition_type,
                    operator=c.operator,
                    field_path=c.field_path,
                    target_value=c.target_value,
                    is_mandatory=c.is_mandatory,
                )
                strat.conditions.append(cond)

            # Add Preconditions
            for p in request.preconditions:
                pre = StrategyPrecondition(
                    strategy_id=strat_id,
                    version_id=version.id,
                    precondition_type=p.precondition_type,
                    requirement_description=p.requirement_description,
                    verification_key=p.verification_key,
                    expected_state=p.expected_state,
                    is_hard_requirement=p.is_hard_requirement,
                )
                strat.preconditions.append(pre)

            # Add Contraindications
            for c in request.contraindications:
                contra = StrategyContraindication(
                    strategy_id=strat_id,
                    version_id=version.id,
                    contraindication_type=c.contraindication_type,
                    severity=c.severity,
                    trigger_condition=c.trigger_condition,
                    rationale=c.rationale,
                )
                strat.contraindications.append(contra)

            # Add Outcomes
            for o in request.outcomes:
                out = StrategyOutcome(
                    strategy_id=strat_id,
                    version_id=version.id,
                    dimension=o.dimension,
                    expected_delta=o.expected_delta,
                    variance=o.variance,
                    success_criteria=o.success_criteria,
                    measurement_unit=o.measurement_unit,
                )
                strat.outcomes.append(out)

            # Add Failure Modes
            for f in request.failure_modes:
                fm = StrategyFailureMode(
                    strategy_id=strat_id,
                    version_id=version.id,
                    failure_class=f.failure_class,
                    symptom=f.symptom,
                    known_cause=f.known_cause,
                    frequency=f.frequency,
                    mitigation_strategy_id=f.mitigation_strategy_id,
                )
                strat.failure_modes.append(fm)

            self._strategies[strat.id] = strat
            self._emit_event("strategy.candidate_created", strat.id, {"name": strat.name, "category": strat.category.value})
            return strat

    def get_strategy(self, strategy_id: str) -> Optional[Strategy]:
        """Retrieve strategy and evaluate its current health/staleness."""
        strat = self._strategies.get(strategy_id)
        if strat:
            self.confidence_engine.evaluate_health_and_confidence(strat)
        return strat

    def list_strategies(
        self,
        category: Optional[StrategyCategory] = None,
        status: Optional[StrategyStatus] = None,
        domain_scope: Optional[str] = None,
        is_stale: Optional[bool] = None,
        limit: int = 50,
    ) -> List[Strategy]:
        """List strategies with optional filtering."""
        with self._lock:
            res: List[Strategy] = []
            for s in self._strategies.values():
                self.confidence_engine.evaluate_health_and_confidence(s)
                if category and s.category != category:
                    continue
                if status and s.lifecycle_status != status:
                    continue
                if domain_scope and s.domain_scope != domain_scope:
                    continue
                if is_stale is not None and s.is_stale != is_stale:
                    continue
                res.append(s)
                if len(res) >= limit:
                    break
            return res

    # --------------------------------------------------------------------------
    # 3. Applicability & Decision Support Bridge
    # --------------------------------------------------------------------------

    def evaluate_strategy_applicability(
        self,
        strategy_id: str,
        context: Dict[str, Any],
    ) -> StrategyApplicability:
        """Check applicability for a specific strategy under live or simulated context."""
        strat = self.get_strategy(strategy_id)
        if not strat:
            return StrategyApplicability(
                strategy_id=strategy_id,
                evaluation_context=context,
                applicability_status=ApplicabilityStatus.NOT_APPLICABLE,
                blocking_reasons=["Strategy not found"],
            )

        is_stopped = self.emergency_stop.is_stopped()
        app = self.applicability_engine.evaluate_applicability(strat, context, emergency_stop_active=is_stopped)

        # Also inspect counterexample database for known failure traps
        ce_match = self.counterexample_engine.check_context_against_counterexamples(strat.id, context)
        if ce_match.has_exact_match:
            app.applicability_status = ApplicabilityStatus.BLOCKED
            app.blocking_reasons.append(ce_match.risk_summary)
        elif ce_match.has_partial_match:
            if app.applicability_status == ApplicabilityStatus.APPLICABLE:
                app.applicability_status = ApplicabilityStatus.UNCERTAIN
            app.uncertainty_reasons.append(ce_match.risk_summary)

        self._applicabilities[app.id] = app
        return app

    def get_candidates_for_decision(
        self,
        context: Dict[str, Any],
        category: Optional[StrategyCategory] = None,
    ) -> DecisionCandidateBundle:
        """Return evaluated, ranked candidates to Task 94 Decision Intelligence."""
        with self._lock:
            all_strats = self.list_strategies(category=category, limit=100)
            evaluated_pairs: List[tuple[Strategy, StrategyApplicability]] = []

            for s in all_strats:
                app = self.evaluate_strategy_applicability(s.id, context)
                evaluated_pairs.append((s, app))

            applicable_strats = [s for s, app in evaluated_pairs if app.applicability_status == ApplicabilityStatus.APPLICABLE]
            conflicts = self.conflict_engine.detect_conflicts(applicable_strats, context)
            for c in conflicts:
                self._conflicts[c.id] = c

            bundle = self.decision_bridge.prepare_decision_candidates(
                evaluated_pairs=evaluated_pairs,
                conflicts=[c.model_dump() for c in conflicts],
                context=context,
            )

            # Record telemetry in MetaStrategyEvaluator
            for cand in bundle.ranked_candidates:
                self.meta_evaluator.record_recommendation_outcome(was_useful=True, was_stale=(cand.freshness == "STALE"))

            return bundle

    # --------------------------------------------------------------------------
    # 4. Strategy Usage & Execution Feedback
    # --------------------------------------------------------------------------

    def record_usage(
        self,
        strategy_id: str,
        decision_id: str,
        mission_id: Optional[str] = None,
        situation_id: Optional[str] = None,
        selected: bool = False,
        execution_context: Optional[Dict[str, Any]] = None,
    ) -> StrategyUsage:
        """Record presentation or selection of a strategy."""
        strat = self.get_strategy(strategy_id)
        usage = StrategyUsage(
            strategy_id=strategy_id,
            version_id=strat.current_version_id if strat else None,
            decision_id=decision_id,
            mission_id=mission_id,
            situation_id=situation_id,
            selected=selected,
            execution_context=execution_context or {},
        )
        self._usages[usage.id] = usage
        if strat and selected:
            strat.usage_count += 1
            self._emit_event("strategy.used", strategy_id, {"decision_id": decision_id, "selected": selected})
        return usage

    def record_feedback(
        self,
        strategy_id: str,
        request: StrategyFeedbackRequest,
    ) -> StrategyFeedback:
        """Record operational feedback, updating empirical statistics and detecting drift."""
        with self._lock:
            strat = self.get_strategy(strategy_id)
            if not strat:
                raise ValueError(f"Strategy {strategy_id} not found.")

            feedback = StrategyFeedback(
                strategy_id=strategy_id,
                version_id=strat.current_version_id,
                decision_id=request.decision_id,
                action_id=request.action_id,
                outcome_status=request.outcome_status,
                actual_metrics=request.actual_metrics,
                observed_failure_mode=request.observed_failure_mode,
                resource_cost=request.resource_cost,
                user_intervention=request.user_intervention,
            )
            self._feedbacks[feedback.id] = feedback

            # Update empirical counters
            n = strat.usage_count
            success_count = int(strat.success_rate * n)
            fail_count = int(strat.failure_rate * n)

            if request.outcome_status == "SUCCESS":
                success_count += 1
                strat.last_success_at = utc_now()
            else:
                fail_count += 1
                strat.last_failure_at = utc_now()
                # If failed, capture counterexample in engine
                self.counterexample_engine.register_counterexample(
                    strategy_id=strategy_id,
                    claim=f"Runtime execution failure: {request.observed_failure_mode or 'Outcome degraded'}",
                    failure_context=request.actual_metrics,
                    observed_metrics=request.actual_metrics,
                )

            total = max(1, success_count + fail_count)
            strat.success_rate = round(success_count / total, 4)
            strat.failure_rate = round(fail_count / total, 4)

            # Evaluate confidence, freshness and drift
            report = self.confidence_engine.evaluate_health_and_confidence(strat)

            if report.is_drift_detected:
                self._emit_event("strategy.drift_detected", strat.id, {
                    "recent_success_rate": strat.success_rate,
                    "nominal_confidence": strat.confidence,
                })

            if request.outcome_status != "SUCCESS":
                self._emit_event("strategy.failure", strat.id, {
                    "failure_mode": request.observed_failure_mode,
                    "metrics": request.actual_metrics,
                })
            else:
                self._emit_event("strategy.feedback_recorded", strat.id, {
                    "outcome": request.outcome_status,
                    "new_confidence": strat.confidence,
                })

            return feedback

    # --------------------------------------------------------------------------
    # 5. Revalidation & Versioning
    # --------------------------------------------------------------------------

    def revalidate_strategy(self, strategy_id: str) -> Strategy:
        """Trigger revalidation of a stale or drifted strategy."""
        with self._lock:
            strat = self.get_strategy(strategy_id)
            if not strat:
                raise ValueError(f"Strategy {strategy_id} not found.")

            strat.last_validated_at = utc_now()
            strat.is_stale = False
            strat.lifecycle_status = StrategyStatus.VALIDATING
            self._emit_event("strategy.revalidation_required", strat.id, {"reason": "Manual or automated revalidation trigger"})

            # Re-evaluate confidence
            self.confidence_engine.evaluate_health_and_confidence(strat)
            return strat

    def create_new_version(
        self,
        strategy_id: str,
        change_reason: str,
        change_description: str = "",
        parameters: Optional[Dict[str, Any]] = None,
        rules: Optional[List[Dict[str, Any]]] = None,
    ) -> StrategyVersion:
        """Mint a new immutable version of a strategy upon empirical evolution."""
        with self._lock:
            strat = self.get_strategy(strategy_id)
            if not strat:
                raise ValueError(f"Strategy {strategy_id} not found.")

            new_ver_num = len(strat.versions) + 1
            new_version = StrategyVersion(
                strategy_id=strategy_id,
                version_number=new_ver_num,
                parent_version_id=strat.current_version_id,
                change_reason=change_reason,
                change_description=change_description,
                parameters=parameters or {},
                rules=rules or [],
                lifecycle_status=StrategyStatus.CANDIDATE,
                confidence=strat.confidence,
                uncertainty=strat.uncertainty,
                evidence_count=len(strat.evidences),
                counterexample_count=len(strat.counterexamples),
            )
            new_version.calculate_checksum()

            strat.current_version_id = new_version.id
            strat.versions.append(new_version)
            self._versions[new_version.id] = new_version

            self._emit_event("strategy.version_minted", strategy_id, {
                "version_number": new_ver_num,
                "reason": change_reason,
                "checksum": new_version.checksum_sha256,
            })
            return new_version

    # --------------------------------------------------------------------------
    # 6. Governance Proposals & Reviews
    # --------------------------------------------------------------------------

    def create_proposal(self, request: StrategyProposalCreateRequest) -> StrategyProposal:
        """Submit a strategy promotion proposal for governance review."""
        with self._lock:
            proposal = StrategyProposal(
                proposal_title=request.proposal_title,
                strategy_id=request.strategy_id,
                target_version=request.target_version,
                rationale=request.rationale,
                mined_patterns_summary=request.mined_patterns_summary,
                status=ProposalStatus.SUBMITTED,
            )
            self._proposals[proposal.id] = proposal
            if request.strategy_id:
                self._emit_event("strategy.proposal_created", request.strategy_id, {"proposal_id": proposal.id})
            return proposal

    def review_proposal(self, proposal_id: str, request: StrategyProposalReviewRequest) -> StrategyReview:
        """Conduct governance review on a proposal, promoting strategy if approved."""
        with self._lock:
            prop = self._proposals.get(proposal_id)
            if not prop:
                raise ValueError(f"Proposal {proposal_id} not found.")

            review = StrategyReview(
                proposal_id=proposal_id,
                reviewer=request.reviewer,
                decision=request.decision,
                comments=request.comments,
                governance_approval_id=request.governance_approval_id,
            )
            self._reviews[review.id] = review

            if request.decision == ReviewDecision.APPROVED:
                prop.status = ProposalStatus.APPROVED
                if prop.strategy_id and prop.strategy_id in self._strategies:
                    strat = self._strategies[prop.strategy_id]
                    strat.lifecycle_status = StrategyStatus.AVAILABLE
                    strat.last_validated_at = utc_now()
                    self._emit_event("strategy.validated", strat.id, {"review_id": review.id})
                    self._emit_event("strategy.available", strat.id, {"promoted_by": request.reviewer})
            else:
                prop.status = ProposalStatus.REJECTED

            return review

    # --------------------------------------------------------------------------
    # 7. Dashboards, Coverage & Reporting
    # --------------------------------------------------------------------------

    def get_dashboard(self) -> StrategyDashboardResponse:
        """Generate comprehensive Strategy Console dashboard."""
        with self._lock:
            strats = list(self._strategies.values())
            for s in strats:
                self.confidence_engine.evaluate_health_and_confidence(s)

            total = len(strats)
            avail = sum(1 for s in strats if s.lifecycle_status == StrategyStatus.AVAILABLE)
            cand = sum(1 for s in strats if s.lifecycle_status == StrategyStatus.CANDIDATE)
            val = sum(1 for s in strats if s.lifecycle_status == StrategyStatus.VALIDATING)
            stale = sum(1 for s in strats if s.is_stale)
            susp = sum(1 for s in strats if s.lifecycle_status == StrategyStatus.SUSPENDED)
            conf = sum(1 for s in strats if s.lifecycle_status == StrategyStatus.CONFLICTED)
            props_pending = sum(1 for p in self._proposals.values() if p.status == ProposalStatus.SUBMITTED)

            cov: Dict[str, int] = {}
            for cat in StrategyCategory:
                cov[cat.value] = sum(1 for s in strats if s.category == cat)

            recent = [
                {
                    "id": s.id,
                    "name": s.name,
                    "category": s.category.value,
                    "status": s.lifecycle_status.value,
                    "confidence": s.confidence,
                    "is_stale": s.is_stale,
                    "usage_count": s.usage_count,
                    "success_rate": s.success_rate,
                }
                for s in sorted(strats, key=lambda x: x.created_at, reverse=True)[:10]
            ]

            active_conflicts = [
                {
                    "id": c.id,
                    "strategy_a_id": c.strategy_a_id,
                    "strategy_b_id": c.strategy_b_id,
                    "conflict_type": c.conflict_type.value,
                    "description": c.description,
                }
                for c in list(self._conflicts.values())[:10]
            ]

            return StrategyDashboardResponse(
                total_strategies=total,
                available_count=avail,
                candidate_count=cand,
                validating_count=val,
                stale_count=stale,
                suspended_count=susp,
                conflicted_count=conf,
                revalidation_queue_count=stale,
                proposals_pending_count=props_pending,
                emergency_stop_active=self.emergency_stop.is_stopped(),
                coverage_by_category=cov,
                recent_strategies=recent,
                active_conflicts=active_conflicts,
            )
