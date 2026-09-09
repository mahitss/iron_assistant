"""Tests for IntentService Master Pipeline and REST API Endpoints (Task 48, Spec 1-70, 186-190)."""

import pytest

from app.intent.schemas import GoalStatus, IntentStatus, IntentType, UrgencyLevel
from app.intent.service import IntentService


def test_service_parse_and_understand_clean_request():
    """Verify master understanding pipeline extracts intent, goal, objectives, constraints, and scope."""
    service = IntentService()
    record = service.parse_and_understand(
        raw_text="Deploy kairo-api to staging before 5pm with budget under $200",
        user_id="user_alice",
        project_id="proj_kairo",
        environment="staging",
    )

    assert record["intent_id"].startswith("intent_")
    assert record["intent_type"] in (IntentType.DEPLOY, IntentType.TASK, IntentType.COMMAND)
    assert record["status"] == IntentStatus.INTERPRETED
    assert record["provenance"]["raw_text"] == "EXPLICIT_USER"
    assert record["confidence"] > 0.7

    # Goal formulated automatically when unambiguous
    goal = record["goal"]
    assert goal is not None
    assert goal["status"] == GoalStatus.ACTIVE.value
    assert goal["owner"] == "user_alice"

    # Constraints captured
    assert len(record["constraints"]) >= 1


def test_service_consequence_aware_ambiguity_gating():
    """Verify destructive action with ambiguous pronoun requires clarification (Spec 57, 111)."""
    service = IntentService()
    # Delete 'it' without antecedent
    record = service.parse_and_understand(
        raw_text="Delete it right now",
        user_id="user_bob",
    )

    assert record["status"] == IntentStatus.NEEDS_CLARIFICATION
    assert record["clarification_request"] is not None
    assert record["goal"] is None  # Never formulate goal on ambiguous destructive action


def test_service_answer_clarification():
    """Providing clarification confirms intent and creates goal (Spec 58, 68)."""
    service = IntentService()
    record = service.parse_and_understand(
        raw_text="Delete it right now",
        user_id="user_bob",
    )
    cid = record["clarification_request"]["clarification_id"]

    res = service.answer_clarification(cid, "scratch_temp.txt")
    assert res["status"] == "ANSWERED"
    assert res["updated_intent_status"] == IntentStatus.CONFIRMED.value

    updated_intent = service.get_intent(record["intent_id"])
    assert updated_intent["status"] == IntentStatus.CONFIRMED
    assert updated_intent["goal"] is not None


def test_service_non_defensive_user_correction():
    """Handle 'That's not what I meant' non-defensively and update intent (Spec 67-69)."""
    service = IntentService()
    initial = service.parse_and_understand(
        raw_text="Build the package",
        session_id="session_test",
    )

    # User corrects
    correction_res = service.apply_user_correction(
        session_id="session_test",
        intent_id=initial["intent_id"],
        correction_text="That's not what I meant. I meant clean the build artifacts.",
        revised_objective="Clean build artifacts",
    )

    assert correction_res["correction_result"]["status"] == "CORRECTION_ACCEPTED"
    revised = correction_res["revised_intent"]
    assert revised["intent_id"] != initial["intent_id"]


def test_service_intent_revocation():
    """Revoke intent and propagate cancellation down to planned goals (Spec 186, 187)."""
    service = IntentService()
    record = service.parse_and_understand(
        raw_text="Run test suite",
        user_id="user_charlie",
    )

    # Revoke
    rev_res = service.revoke_intent(
        intent_id=record["intent_id"],
        user_id="user_charlie",
        reason="User requested cancellation",
    )
    assert rev_res["status"] == IntentStatus.CANCELLED.value

    # Verifying goal cancellation
    g_id = record["goal"]["goal_id"]
    g = service.goals.get_goal(g_id)
    assert g.status == GoalStatus.CANCELLED


def test_rest_api_intent_parse_and_lifecycle(client):
    """Test REST API endpoints: /parse, /intents, /clarify, /health, /tradeoffs."""
    # 1. Parse intent
    parse_resp = client.post(
        "/api/v1/intent/parse",
        headers={"x-user-id": "user_api_tester"},
        json={
            "raw_text": "Deploy frontend service to production",
            "environment": "production",
        },
    )
    assert parse_resp.status_code == 200
    p_data = parse_resp.json()
    assert "intent_id" in p_data
    intent_id = p_data["intent_id"]

    # 2. Get intent by id
    get_resp = client.get(
        f"/api/v1/intent/intents/{intent_id}",
        headers={"x-user-id": "user_api_tester"},
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["intent_id"] == intent_id

    # 3. List intents
    list_resp = client.get(
        "/api/v1/intent/intents",
        headers={"x-user-id": "user_api_tester"},
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1

    # 4. Tradeoff analysis endpoint
    tradeoff_resp = client.post(
        "/api/v1/intent/tradeoffs",
        headers={"x-user-id": "user_api_tester"},
        json={
            "goal_a": "Fast release",
            "goal_b": "Exhaustive tests",
            "cost_a": 10.0,
            "cost_b": 60.0,
        },
    )
    assert tradeoff_resp.status_code == 200
    assert "preferred_goal" in tradeoff_resp.json()

    # 5. Health endpoint
    health_resp = client.get(
        "/api/v1/intent/health",
        headers={"x-user-id": "user_api_tester"},
    )
    assert health_resp.status_code == 200
    assert "intents_total" in health_resp.json()

