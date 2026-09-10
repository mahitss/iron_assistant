"""Unit tests for Incident Triage, Severity Derivation, and Urgency Evaluation (Task 61)."""

from app.incident_response.schemas import (
    AutomationLevel,
    IncidentSeverity,
    IncidentUrgency,
)
from app.incident_response.triage import IncidentTriageEngine


def test_triage_production_critical_with_threatened_goals():
    """Verify that a production situation affecting strategic goals triages as CRITICAL with IMMEDIATE urgency."""
    engine = IncidentTriageEngine()

    situation = {
        "situation_id": "sit_prod_01",
        "title": "Payment gateway timeout spike",
        "environment": "production",
        "severity": "CRITICAL",
        "affected_resources": ["payment-gw-1", "payment-gw-2"],
        "affected_services": ["payment-api", "checkout-svc"],
        "affected_goals": ["goal_q3_checkout_sla"],
    }

    triage = engine.triage_situation(situation)

    assert triage["severity"] == IncidentSeverity.CRITICAL
    assert triage["urgency"] == IncidentUrgency.IMMEDIATE
    assert triage["requires_commander"] is True
    assert triage["automation_level"] == AutomationLevel.AUTO_WITH_APPROVAL
    assert triage["confidence"] >= 0.90


def test_triage_urgency_independent_of_severity():
    """Test Invariant 11: Urgency is evaluated independently from severity (deadlines/plans elevate urgency)."""
    engine = IncidentTriageEngine()

    situation = {
        "situation_id": "sit_dev_urgent",
        "title": "Staging build cache missed",
        "environment": "staging",
        "severity": "LOW",
        "affected_resources": ["ci-builder"],
        "affected_services": [],
        "affected_goals": ["goal_release_by_midnight"],
    }

    triage = engine.triage_situation(situation)

    # Severity remains LOW/INFO in non-prod with low raw severity
    assert triage["severity"] in (IncidentSeverity.LOW, IncidentSeverity.INFO)
    # Urgency is elevated to HIGH due to threatened active goal
    assert triage["urgency"] == IncidentUrgency.HIGH


def test_triage_development_non_critical_defaults():
    """Verify development incidents default to lower severity and observe/recommend automation levels."""
    engine = IncidentTriageEngine()

    situation = {
        "situation_id": "sit_local_01",
        "title": "Local debug port closed",
        "environment": "development",
        "severity": "LOW",
        "affected_resources": ["local-node"],
        "affected_services": [],
        "affected_goals": [],
    }

    triage = engine.triage_situation(situation)

    assert triage["severity"] == IncidentSeverity.INFO
    assert triage["urgency"] == IncidentUrgency.LOW
    assert triage["requires_commander"] is False
    assert triage["automation_level"] == AutomationLevel.OBSERVE_ONLY


def test_severity_override_via_arbitrary_payload_is_constrained():
    """Test Invariant 10: Raw text cannot override severity in non-production environments without evidence."""
    engine = IncidentTriageEngine()

    situation = {
        "situation_id": "sit_spoof",
        "title": "Arbitrary alert saying CRITICAL",
        "environment": "development",
        "severity": "CRITICAL",
        "affected_resources": [],
        "affected_services": [],
        "affected_goals": [],
    }

    triage = engine.triage_situation(situation)

    # Even though raw severity said CRITICAL, development environment with 0 affected goals bounds severity to MEDIUM
    assert triage["severity"] == IncidentSeverity.MEDIUM
