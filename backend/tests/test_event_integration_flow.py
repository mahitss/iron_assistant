"""End-to-end integration tests for Kairo Unified Event Bus and API endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone

from app.events.bus import event_bus
from app.events.handlers import register_default_handlers
from app.events.handlers.activity_handler import get_user_activity, clear_recent_activities
from app.events.handlers.notification_handler import get_recent_notifications, clear_recent_notifications
from app.main import create_app


@pytest.fixture(autouse=True)
def setup_handlers():
    clear_recent_activities()
    clear_recent_notifications()
    register_default_handlers(event_bus)
    yield
    clear_recent_activities()
    clear_recent_notifications()


@pytest.mark.asyncio
async def test_end_to_end_github_ci_failure_flow():
    """Verify that a single event (GitHub CI failure) branches to Notification, Proactive, and Activity feeds."""
    ci_event = event_bus.publisher.create_event(
        event_type="github.ci.failed",
        source="github_webhook",
        payload={
            "repo": "kairo-assistant/backend",
            "workflow_name": "Lint & Test",
            "run_id": "778899",
        },
        user_id="dev_user_1",
    )

    await event_bus.publish(ci_event, persist_log=False)

    # 1. Notification dispatch verification
    recent_notifs = get_recent_notifications()
    assert len(recent_notifs) >= 1
    ci_notif = next((n for n in recent_notifs if n["event_id"] == ci_event.event_id), None)
    assert ci_notif is not None
    assert "Lint & Test" in ci_notif["body"]
    assert ci_notif["severity"] == "warning"

    # 2. Activity Feed verification
    activities = await get_user_activity(user_id="dev_user_1")
    assert len(activities) >= 1
    ci_activity = next((a for a in activities if a["id"] == ci_event.event_id), None)
    assert ci_activity is not None
    assert "CI Workflow Failed" in ci_activity["title"]


@pytest.mark.asyncio
async def test_events_api_endpoints():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. GET /api/v1/events/registry
        reg_res = await client.get("/api/v1/events/registry")
        assert reg_res.status_code == 200
        reg_data = reg_res.json()
        assert reg_data["total"] >= 18
        assert any(e["event_type"] == "github.ci.failed" for e in reg_data["events"])

        # 2. GET /api/v1/events/metrics
        met_res = await client.get("/api/v1/events/metrics")
        assert met_res.status_code == 200
        met_data = met_res.json()
        assert "published_total" in met_data
        assert "latency_ms" in met_data

        # 3. GET /api/v1/events/activity
        act_res = await client.get("/api/v1/events/activity", headers={"x-user-id": "dev_user_1"})
        assert act_res.status_code == 200
        assert "items" in act_res.json()

        # 4. POST /api/v1/events/publish (Allowed event)
        pub_res = await client.post(
            "/api/v1/events/publish",
            json={
                "event_type": "notification.read",
                "source": "api_client",
                "payload": {"notification_id": "notif_42"},
            },
            headers={"x-user-id": "dev_user_1"},
        )
        assert pub_res.status_code == 202
        assert pub_res.json()["status"] == "accepted"

        # 5. POST /api/v1/events/publish (Privileged event forbidden!)
        forged_res = await client.post(
            "/api/v1/events/publish",
            json={
                "event_type": "security.allowed",
                "source": "api_client",
                "payload": {"action": "sudo_bash"},
            },
            headers={"x-user-id": "dev_user_1"},
        )
        assert forged_res.status_code == 403
