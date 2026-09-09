"""Unit tests for the master CommunicationService orchestrator and FastAPI communication router endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.communication.schemas import (
    CommunicationChannel,
    CommunicationTone,
    MessageCategory,
    MessageStatus,
    RecipientSchema,
    SendRequestSchema,
)
from app.communication.service import CommunicationService
from app.main import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_communication_service_13_stage_pipeline():
    service = CommunicationService()

    raw_email = {
        "from": "colleague@company.com",
        "to": ["user@kairo.internal"],
        "subject": "Deployment sync for Project Titan",
        "body": "Hi team, could you please review the staging deployment by Thursday?\nI will finalize the monitoring metrics.",
    }

    # Run inbound pipeline stages 1 to 8
    res = service.process_inbound_message(
        raw_payload=raw_email,
        channel=CommunicationChannel.EMAIL,
        user_id="user_admin",
        project_id="proj_titan",
    )

    assert res["message"].subject == "Deployment sync for Project Titan"
    assert res["thread"].subject == "Deployment sync for Project Titan"
    assert res["classification"]["primary_category"] in (MessageCategory.QUESTION.value, MessageCategory.REQUEST.value)
    assert res["response_need"]["response_need"].value in ("RECOMMENDED", "REQUIRED")
    assert len(res["commitments"]) >= 1

    # Stage 8: Generate Reply Draft
    thread_id = res["thread"].thread_id
    draft = service.generate_reply_draft(
        thread_id=thread_id,
        user_id="user_admin",
        custom_instructions="Confirmed, we will review the deployment by Thursday morning.",
        tone=CommunicationTone.FORMAL,
    )
    assert draft.status.value == "DRAFT"
    assert "Confirmed" in draft.body_reference

    # Stages 9 to 13: Governed Send via ToolExecutor
    send_req = SendRequestSchema(
        draft_id=draft.draft_id,
        channel=CommunicationChannel.EMAIL,
        recipients=draft.recipients,
        subject=draft.subject,
        content=draft.body_reference,
        idempotency_key="idemp_send_001",
        user_id="user_admin",
        project_id="proj_titan",
    )

    receipt = service.send_communication(send_req, user_id="user_admin", is_user_approved=True)
    assert receipt.status in (MessageStatus.SENT, MessageStatus.DELIVERED)
    assert receipt.read_receipt is False  # Delivery != Read


def test_meeting_preparation_and_followup_without_fabrication():
    service = CommunicationService()

    # Meeting brief preparation
    brief = service.prepare_meeting_brief(
        title="Architecture Sync",
        participants=["Alice", "Bob", "Charlie"],
        agenda_topics=["Database Sharding", "Redis Caching"],
    )
    assert brief["title"] == "Architecture Sync"
    assert len(brief["open_questions"]) >= 1

    # Meeting follow-up extraction
    transcript = (
        "Alice: We decided to proceed with Postgres partitioning.\n"
        "Bob: Action item: Configure the replica connection pool by Friday."
    )
    followup = service.process_meeting_followup(transcript)
    assert len(followup["decisions"]) >= 1
    assert "Postgres partitioning" in followup["decisions"][0]
    assert len(followup["action_items"]) >= 1
    assert followup["action_items"][0]["owner"] == "Bob"


def test_safe_multilingual_translation():
    service = CommunicationService()

    # Translation with negation preserved
    text_with_neg = "Do not deploy to production without approval."
    trans = service.translate_message_safely(text_with_neg, "es")
    assert trans["negation_preserved"] is True
    assert trans["requires_review"] is True


def test_fastapi_communication_endpoints(client: TestClient):
    headers = {"X-User-Id": "user_admin", "X-Project-Id": "proj_titan"}

    # 1. Health check
    res_health = client.get("/api/v1/communication/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"

    # 2. Ingest inbound message
    inbound_payload = {
        "raw_payload": {
            "from": "partner@vendor.com",
            "to": ["user@kairo.internal"],
            "subject": "SLA Update",
            "body": "Could you please confirm receipt of the updated SLA terms?",
        },
        "channel": "EMAIL",
        "user_id": "user_admin",
        "project_id": "proj_titan",
    }
    res_inbound = client.post("/api/v1/communication/messages/inbound", json=inbound_payload, headers=headers)
    assert res_inbound.status_code == 200
    data = res_inbound.json()
    assert data["status"] == "processed"
    thread_id = data["thread_id"]

    # 3. List threads
    res_threads = client.get("/api/v1/communication/threads", headers=headers)
    assert res_threads.status_code == 200
    threads_list = res_threads.json()
    assert len(threads_list) >= 1

    # 4. Get thread details & rolling summary
    res_td = client.get(f"/api/v1/communication/threads/{thread_id}", headers=headers)
    assert res_td.status_code == 200
    assert "summary" in res_td.json()

    # 5. Generate reply draft
    draft_req = {
        "custom_instructions": "We have received the SLA terms and agree with Section 4.",
        "tone": "FORMAL",
        "user_id": "user_admin",
    }
    res_draft = client.post(f"/api/v1/communication/threads/{thread_id}/draft", json=draft_req, headers=headers)
    assert res_draft.status_code == 200
    draft_data = res_draft.json()
    draft_id = draft_data["draft_id"]
    assert draft_data["status"] == "DRAFT"

    # 6. List drafts
    res_drafts = client.get("/api/v1/communication/drafts", headers=headers)
    assert res_drafts.status_code == 200
    assert any(d["draft_id"] == draft_id for d in res_drafts.json())

    # 7. Approve draft
    res_approve = client.post(
        f"/api/v1/communication/drafts/{draft_id}/approve",
        json={"approver_identity": "user_admin"},
        headers=headers,
    )
    assert res_approve.status_code == 200
    assert res_approve.json()["status"] == "APPROVED"

    # 8. Send message
    send_payload = {
        "draft_id": draft_id,
        "channel": "EMAIL",
        "recipients": [{"identity": "partner@vendor.com", "address": "partner@vendor.com"}],
        "subject": "Re: SLA Update",
        "content": "We have received the SLA terms and agree with Section 4.",
        "idempotency_key": "send_test_1001",
        "user_id": "user_admin",
    }
    res_send = client.post("/api/v1/communication/send?is_user_approved=true", json=send_payload, headers=headers)
    assert res_send.status_code == 200
    assert res_send.json()["status"] in ("SENT", "DELIVERED")

    # 9. Add and list contacts
    res_add_contact = client.post(
        "/api/v1/communication/contacts",
        json={
            "identity": "sam_alt",
            "address": "sam@openai.internal",
            "display_name": "Sam Alt",
            "is_external": True,
        },
        headers=headers,
    )
    assert res_add_contact.status_code == 200

    res_contacts = client.get("/api/v1/communication/contacts", headers=headers)
    assert res_contacts.status_code == 200
    assert any(c["address"] == "sam@openai.internal" for c in res_contacts.json())

    # 10. Metrics telemetry
    res_metrics = client.get("/api/v1/communication/metrics", headers=headers)
    assert res_metrics.status_code == 200
    metrics_data = res_metrics.json()
    assert metrics_data["messages_processed"] >= 1
    assert metrics_data["sends_attempted"] >= 1
