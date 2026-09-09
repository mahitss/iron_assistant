"""Unit tests for decisions, preferences, and outcome tracking."""

import pytest

from app.knowledge_graph.decisions import DecisionAgreementError, DecisionManager
from app.knowledge_graph.outcomes import OutcomeManager
from app.knowledge_graph.preferences import PreferenceManager
from app.knowledge_graph.schemas import (
    DecisionStatus,
    PreferenceCategory,
    ScopeType,
)


def test_decision_recording_and_agreement_guard():
    dm = DecisionManager()

    # Invariant 59: Never infer agreement solely from discussion
    with pytest.raises(DecisionAgreementError, match="discussion alone does not constitute verified agreement"):
        dm.record_decision(
            question="Should we migrate to GraphQL?",
            decision="Yes",
            is_only_discussion=True,
        )

    # Invariant 156: If rationale not recorded, says unknown
    dec = dm.record_decision(
        question="Which database for session caching?",
        decision="Redis",
        alternatives=["Memcached", "In-memory"],
        rationale_reference=None,
        owner="architect_alex",
        project_id="proj_backend",
    )

    explanation = dm.explain_decision(dec.decision_id)
    assert explanation["chosen_decision"] == "Redis"
    assert "UNKNOWN" in explanation["rationale"]
    assert "Memcached" in explanation["alternatives_considered"]

    # Invariant 56: Do not silently overwrite old decisions, mark superseded
    dec2 = dm.record_decision(
        question="Which database for session caching?",
        decision="DragonflyDB",
        alternatives=["Redis"],
        rationale_reference="Performance benchmarking report #402",
        owner="architect_alex",
        project_id="proj_backend",
    )
    dm.supersede_decision(dec.decision_id, dec2.decision_id)
    assert dec.status == DecisionStatus.SUPERSEDED


def test_preferences_hierarchy_and_instruction_override():
    pm = PreferenceManager()

    # Invariant 162: Global technical preference (TypeScript for frontend)
    pm.set_preference(
        category=PreferenceCategory.TECHNICAL,
        value={"language": "TypeScript"},
        scope=ScopeType.GLOBAL,
        user_id="dev_user",
        project_id=None,
        confidence=1.0,
    )

    res_global = pm.resolve_preference(
        category=PreferenceCategory.TECHNICAL,
        user_id="dev_user",
    )
    assert res_global["value"]["language"] == "TypeScript"

    # Invariant 163: Project-scoped preference (Rust for specific project)
    pm.set_preference(
        category=PreferenceCategory.TECHNICAL,
        value={"language": "Rust"},
        scope=ScopeType.PROJECT,
        user_id="dev_user",
        project_id="proj_core_engine",
        confidence=1.0,
    )

    res_project = pm.resolve_preference(
        category=PreferenceCategory.TECHNICAL,
        user_id="dev_user",
        project_id="proj_core_engine",
    )
    assert res_project["value"]["language"] == "Rust"
    assert res_project["scope"] == "project"

    # Invariant 71: Current explicit user instruction ALWAYS overrides older preferences
    res_override = pm.resolve_preference(
        category=PreferenceCategory.TECHNICAL,
        user_id="dev_user",
        project_id="proj_core_engine",
        current_instruction_override={"language": "Go"},
    )
    assert res_override["value"]["language"] == "Go"
    assert res_override["source"] == "current_explicit_instruction"


def test_outcome_tracking_and_verification():
    om = OutcomeManager()

    outcome = om.record_outcome(
        related_goal_id="goal_reduce_latency",
        result={"p99_latency_ms": 42},
        evidence=[{"benchmark_run_id": "bench_998"}],
        verified=True,
    )

    assert outcome.verified is True
    assert outcome.result["p99_latency_ms"] == 42
