"""Multi-Source Perception Adapters, Event Normalization, and Adapter Contracts (Task 46)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional
import uuid

from app.perception.events import EventType, InvalidEventError, PerceptionEvent
from app.perception.sources import PerceptionSource, SourceType

logger = logging.getLogger("kairo.perception.adapters")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class BaseSourceAdapter(ABC):
    """Abstract contract for source-specific event adapters (Spec 11, 12)."""

    @abstractmethod
    def adapt(self, raw: Dict[str, Any], source: PerceptionSource) -> PerceptionEvent:
        """Convert a raw heterogeneous event into a normalized PerceptionEvent."""
        pass


class DeviceAdapter(BaseSourceAdapter):
    """Adapts device telemetry (battery, network, active app, power state) (Spec 36, 37)."""

    def adapt(self, raw: Dict[str, Any], source: PerceptionSource) -> PerceptionEvent:
        action = raw.get("action", "STATUS_CHANGED").upper()
        event_type = getattr(EventType, action, EventType.STATUS_CHANGED)
        subject = raw.get("device_id", source.source_id)

        return PerceptionEvent(
            event_id=raw.get("event_id", f"dev_{uuid.uuid4().hex[:10]}"),
            event_type=event_type,
            source_id=source.source_id,
            subject=f"device:{subject}",
            timestamp=raw.get("timestamp", utc_now()),
            sequence=raw.get("sequence", 0),
            payload={
                "battery_level": raw.get("battery_level"),
                "is_charging": raw.get("is_charging"),
                "network_ssid": raw.get("network_ssid"),
                "is_online": raw.get("is_online", True),
                "active_app": raw.get("active_app"),
            },
            scope={"device_id": subject, "user_id": raw.get("user_id", "default_user")},
            correlation_id=raw.get("correlation_id"),
            provenance={"adapter": "DeviceAdapter", "source_type": SourceType.DEVICE.value},
        )


class BrowserAdapter(BaseSourceAdapter):
    """Adapts browser events (navigation, title, DOM state) excluding credentials (Spec 46-48)."""

    def adapt(self, raw: Dict[str, Any], source: PerceptionSource) -> PerceptionEvent:
        action = raw.get("action", "NAVIGATED").upper()
        event_type = getattr(EventType, action, EventType.NAVIGATED)
        url = raw.get("url", "about:blank")

        # Never persist session tokens or password form inputs (Spec 48)
        clean_payload = {
            "url": url,
            "title": raw.get("title", ""),
            "loading_status": raw.get("loading_status", "complete"),
            "tab_id": raw.get("tab_id"),
            "window_id": raw.get("window_id"),
            "has_dom_error": raw.get("has_dom_error", False),
        }

        return PerceptionEvent(
            event_id=raw.get("event_id", f"brw_{uuid.uuid4().hex[:10]}"),
            event_type=event_type,
            source_id=source.source_id,
            subject=f"browser:tab_{raw.get('tab_id', 'unknown')}",
            timestamp=raw.get("timestamp", utc_now()),
            payload=clean_payload,
            scope={"domain": raw.get("domain", ""), "user_id": raw.get("user_id", "default_user")},
            correlation_id=raw.get("correlation_id"),
            provenance={"adapter": "BrowserAdapter", "source_type": SourceType.BROWSER.value},
        )


class FileSystemAdapter(BaseSourceAdapter):
    """Adapts file system change notifications without reading entire files (Spec 49-51)."""

    def adapt(self, raw: Dict[str, Any], source: PerceptionSource) -> PerceptionEvent:
        action = raw.get("action", "UPDATED").upper()
        event_type = getattr(EventType, action, EventType.UPDATED)
        file_path = raw.get("path", "")

        return PerceptionEvent(
            event_id=raw.get("event_id", f"fs_{uuid.uuid4().hex[:10]}"),
            event_type=event_type,
            source_id=source.source_id,
            subject=f"file:{file_path}",
            timestamp=raw.get("timestamp", utc_now()),
            payload={
                "path": file_path,
                "is_directory": raw.get("is_directory", False),
                "size_bytes": raw.get("size_bytes", 0),
                "old_path": raw.get("old_path"),  # for renames
                "hash": raw.get("hash"),
            },
            scope={"path": file_path, "project_id": raw.get("project_id", "default_project")},
            correlation_id=raw.get("correlation_id"),
            provenance={"adapter": "FileSystemAdapter", "source_type": SourceType.FILE_SYSTEM.value},
        )


class GitAdapter(BaseSourceAdapter):
    """Adapts repository commit, push, branch, and merge events (Spec 53, 54)."""

    def adapt(self, raw: Dict[str, Any], source: PerceptionSource) -> PerceptionEvent:
        action = raw.get("action", "COMMITTED").upper()
        event_type = getattr(EventType, action, EventType.COMMITTED)
        repo = raw.get("repository", "unknown_repo")

        return PerceptionEvent(
            event_id=raw.get("event_id", f"git_{uuid.uuid4().hex[:10]}"),
            event_type=event_type,
            source_id=source.source_id,
            subject=f"git:{repo}",
            timestamp=raw.get("timestamp", utc_now()),
            payload={
                "repository": repo,
                "branch": raw.get("branch", "main"),
                "commit_hash": raw.get("commit_hash", ""),
                "author": raw.get("author", ""),
                "message": raw.get("message", "")[:200],
                "files_changed_count": raw.get("files_changed_count", 0),
            },
            scope={"repository": repo, "project_id": raw.get("project_id", "default_project")},
            correlation_id=raw.get("correlation_id", raw.get("commit_hash")),
            provenance={"adapter": "GitAdapter", "source_type": SourceType.GIT.value},
        )


class DeploymentAdapter(BaseSourceAdapter):
    """Adapts CI/CD deployment milestones and health rollouts (Spec 57-59)."""

    def adapt(self, raw: Dict[str, Any], source: PerceptionSource) -> PerceptionEvent:
        action = raw.get("action", "DEPLOYED").upper()
        event_type = getattr(EventType, action, EventType.DEPLOYED)
        service = raw.get("service", "unknown_service")
        env = raw.get("environment", "DEVELOPMENT").upper()

        return PerceptionEvent(
            event_id=raw.get("event_id", f"dep_{uuid.uuid4().hex[:10]}"),
            event_type=event_type,
            source_id=source.source_id,
            subject=f"deployment:{service}:{env}",
            timestamp=raw.get("timestamp", utc_now()),
            payload={
                "service": service,
                "environment": env,
                "version": raw.get("version", ""),
                "commit_hash": raw.get("commit_hash", ""),
                "rollout_percentage": raw.get("rollout_percentage", 100),
                "is_healthy": raw.get("is_healthy", True),
            },
            scope={"environment": env, "project_id": raw.get("project_id", "default_project")},
            correlation_id=raw.get("correlation_id", raw.get("commit_hash")),
            causation_id=raw.get("commit_hash"),
            provenance={"adapter": "DeploymentAdapter", "source_type": SourceType.DEPLOYMENT.value},
        )


class ServiceHealthAdapter(BaseSourceAdapter):
    """Adapts service availability, health checks, and heartbeat signals (Spec 60, 61)."""

    def adapt(self, raw: Dict[str, Any], source: PerceptionSource) -> PerceptionEvent:
        payload_data = raw.get("payload") if isinstance(raw.get("payload"), dict) else {}
        service_name = raw.get("service_name") or payload_data.get("service_name")
        if not service_name and raw.get("subject"):
            subj = str(raw["subject"])
            service_name = subj.split(":", 1)[1] if ":" in subj else subj
        if not service_name:
            service_name = "unknown_service"

        health_status = (raw.get("status") or payload_data.get("status") or "HEALTHY").upper()
        event_type = EventType.HEALTH_CHANGED if (raw.get("is_changed") or raw.get("event_type") == "HEALTH_CHANGED") else EventType.UPDATED

        return PerceptionEvent(
            event_id=raw.get("event_id", f"hlth_{uuid.uuid4().hex[:10]}"),
            event_type=event_type,
            source_id=source.source_id,
            subject=f"service:{service_name}",
            timestamp=raw.get("timestamp", utc_now()),
            payload={
                "service_name": service_name,
                "status": health_status,  # HEALTHY, DEGRADED, UNHEALTHY, UNKNOWN
                "latency_ms": raw.get("latency_ms", payload_data.get("latency", 0.0)),
                "error_rate": raw.get("error_rate", payload_data.get("error_rate", 0.0)),
                "ttl_seconds": raw.get("ttl_seconds", 30),
            },
            scope={"environment": raw.get("environment", "DEVELOPMENT")},
            correlation_id=raw.get("correlation_id"),
            provenance={"adapter": "ServiceHealthAdapter", "source_type": SourceType.SERVICE.value},
        )


class NotificationAdapter(BaseSourceAdapter):
    """Adapts user and system notifications with severity classification (Spec 65-67)."""

    def adapt(self, raw: Dict[str, Any], source: PerceptionSource) -> PerceptionEvent:
        category = raw.get("category", "informational").lower()
        title = raw.get("title", "")
        message = raw.get("message", "")

        return PerceptionEvent(
            event_id=raw.get("event_id", f"notif_{uuid.uuid4().hex[:10]}"),
            event_type=EventType.ALERTED if category in ["warning", "critical"] else EventType.RECEIVED,
            source_id=source.source_id,
            subject=f"notification:{raw.get('notification_id', 'general')}",
            timestamp=raw.get("timestamp", utc_now()),
            payload={
                "title": title,
                "message": message,
                "category": category,  # informational, warning, action_required, critical
                "urgency": raw.get("urgency", "normal"),
                "sender": raw.get("sender", "system"),
            },
            scope={"user_id": raw.get("user_id", "default_user")},
            correlation_id=raw.get("correlation_id"),
            provenance={"adapter": "NotificationAdapter", "source_type": SourceType.NOTIFICATION.value},
        )


class VoiceAdapter(BaseSourceAdapter):
    """Adapts voice events with transcription reference, confidence, and zero persistent raw audio (Spec 43, 44)."""

    def adapt(self, raw: Dict[str, Any], source: PerceptionSource) -> PerceptionEvent:
        action = raw.get("action", "RECEIVED").upper()
        event_type = getattr(EventType, action, EventType.RECEIVED)

        return PerceptionEvent(
            event_id=raw.get("event_id", f"voc_{uuid.uuid4().hex[:10]}"),
            event_type=event_type,
            source_id=source.source_id,
            subject=f"voice:{raw.get('session_id', 'audio_input')}",
            timestamp=raw.get("timestamp", utc_now()),
            payload={
                "transcription": raw.get("transcription", ""),
                "confidence": raw.get("confidence", 0.95),
                "speaker_id": raw.get("speaker_id"),
                "audio_ref": raw.get("audio_ref", "ephemeral://voice/stream"),  # reference only, never raw audio (Spec 44)
            },
            scope={"user_id": raw.get("user_id", "default_user")},
            correlation_id=raw.get("correlation_id"),
            provenance={"adapter": "VoiceAdapter", "source_type": SourceType.VOICE.value},
        )


class VisionAdapter(BaseSourceAdapter):
    """Adapts vision observations distinguishing detected object, meaning, and inference (Spec 45)."""

    def adapt(self, raw: Dict[str, Any], source: PerceptionSource) -> PerceptionEvent:
        action = raw.get("action", "CREATED").upper()
        event_type = getattr(EventType, action, EventType.CREATED)

        return PerceptionEvent(
            event_id=raw.get("event_id", f"vis_{uuid.uuid4().hex[:10]}"),
            event_type=event_type,
            source_id=source.source_id,
            subject=f"vision:{raw.get('target', 'scene')}",
            timestamp=raw.get("timestamp", utc_now()),
            payload={
                "detected_object": raw.get("detected_object", "unknown"),
                "interpreted_meaning": raw.get("interpreted_meaning", ""),
                "inference": raw.get("inference", ""),
                "confidence": raw.get("confidence", 0.9),
                "image_ref": raw.get("image_ref", "ephemeral://vision/capture"),
            },
            scope={"device_id": raw.get("device_id", "camera"), "user_id": raw.get("user_id", "default_user")},
            correlation_id=raw.get("correlation_id"),
            provenance={"adapter": "VisionAdapter", "source_type": SourceType.VISION.value},
        )


class GitHubAdapter(BaseSourceAdapter):
    """Adapts GitHub PRs, issues, checks, workflows, and releases (Spec 55, 56)."""

    def adapt(self, raw: Dict[str, Any], source: PerceptionSource) -> PerceptionEvent:
        action = raw.get("action", "UPDATED").upper()
        event_type = getattr(EventType, action, EventType.UPDATED)
        repo = raw.get("repository", "repo")
        gh_type = raw.get("github_type", "issue")  # issue, pr, check_run, workflow_run
        number = raw.get("number", "1")

        return PerceptionEvent(
            event_id=raw.get("event_id", f"gh_{uuid.uuid4().hex[:10]}"),
            event_type=event_type,
            source_id=source.source_id,
            subject=f"github:{repo}:{gh_type}_{number}",
            timestamp=raw.get("timestamp", utc_now()),
            payload={
                "repository": repo,
                "github_type": gh_type,
                "number": number,
                "title": raw.get("title", ""),
                "state": raw.get("state", "open"),
                "sender": raw.get("sender", "github-bot"),
            },
            scope={"repository": repo, "project_id": raw.get("project_id", "default_project")},
            correlation_id=raw.get("correlation_id"),
            provenance={"adapter": "GitHubAdapter", "source_type": SourceType.GITHUB.value},
        )


class TaskEngineAdapter(BaseSourceAdapter):
    """Adapts Task Engine state transitions (Spec 68)."""

    def adapt(self, raw: Dict[str, Any], source: PerceptionSource) -> PerceptionEvent:
        action = raw.get("action", "PROGRESS").upper()
        mapping = {
            "STARTED": EventType.STARTED,
            "PROGRESS": EventType.UPDATED,
            "BLOCKED": EventType.BLOCKED,
            "COMPLETED": EventType.COMPLETED,
            "FAILED": EventType.FAILED,
        }
        event_type = mapping.get(action, EventType.UPDATED)
        task_id = raw.get("task_id", "unknown_task")

        return PerceptionEvent(
            event_id=raw.get("event_id", f"tsk_{uuid.uuid4().hex[:10]}"),
            event_type=event_type,
            source_id=source.source_id,
            subject=f"task:{task_id}",
            timestamp=raw.get("timestamp", utc_now()),
            payload={
                "task_id": task_id,
                "state": action,
                "step_index": raw.get("step_index", 0),
                "progress_pct": raw.get("progress_pct", 0),
            },
            scope={"task_id": task_id, "project_id": raw.get("project_id", "default_project")},
            correlation_id=task_id,
            provenance={"adapter": "TaskEngineAdapter", "source_type": SourceType.TASK_ENGINE.value},
        )


class AgentAdapter(BaseSourceAdapter):
    """Adapts multi-agent collaboration states (Spec 69)."""

    def adapt(self, raw: Dict[str, Any], source: PerceptionSource) -> PerceptionEvent:
        action = raw.get("action", "WORKING").upper()
        mapping = {
            "STARTED": EventType.STARTED,
            "WORKING": EventType.UPDATED,
            "BLOCKED": EventType.BLOCKED,
            "FAILED": EventType.FAILED,
            "COMPLETED": EventType.COMPLETED,
        }
        event_type = mapping.get(action, EventType.UPDATED)
        agent_id = raw.get("agent_id", "agent")

        return PerceptionEvent(
            event_id=raw.get("event_id", f"ag_{uuid.uuid4().hex[:10]}"),
            event_type=event_type,
            source_id=source.source_id,
            subject=f"agent:{agent_id}",
            timestamp=raw.get("timestamp", utc_now()),
            payload={
                "agent_id": agent_id,
                "status": action,
                "current_task": raw.get("current_task"),
            },
            scope={"agent_id": agent_id, "project_id": raw.get("project_id", "default_project")},
            correlation_id=raw.get("correlation_id"),
            provenance={"adapter": "AgentAdapter", "source_type": SourceType.AGENT.value},
        )


class AutomationAdapter(BaseSourceAdapter):
    """Adapts automation workflow lifecycle (Spec 70)."""

    def adapt(self, raw: Dict[str, Any], source: PerceptionSource) -> PerceptionEvent:
        action = raw.get("action", "STARTED").upper()
        event_type = getattr(EventType, action, EventType.STARTED)
        workflow_id = raw.get("workflow_id", "workflow")

        return PerceptionEvent(
            event_id=raw.get("event_id", f"aut_{uuid.uuid4().hex[:10]}"),
            event_type=event_type,
            source_id=source.source_id,
            subject=f"automation:{workflow_id}",
            timestamp=raw.get("timestamp", utc_now()),
            payload={
                "workflow_id": workflow_id,
                "status": action,
                "trigger": raw.get("trigger", "cron"),
            },
            scope={"project_id": raw.get("project_id", "default_project")},
            correlation_id=workflow_id,
            provenance={"adapter": "AutomationAdapter", "source_type": SourceType.AUTOMATION.value},
        )


class CalendarAdapter(BaseSourceAdapter):
    """Adapts calendar scheduled events within authorized scope (Spec 71, 72)."""

    def adapt(self, raw: Dict[str, Any], source: PerceptionSource) -> PerceptionEvent:
        action = raw.get("action", "SCHEDULED").upper()
        mapping = {
            "UPCOMING": EventType.SCHEDULED,
            "STARTED": EventType.STARTED,
            "CHANGED": EventType.UPDATED,
            "CANCELLED": EventType.CANCELLED,
        }
        event_type = mapping.get(action, EventType.SCHEDULED)
        cal_id = raw.get("event_id", "meeting")

        return PerceptionEvent(
            event_id=f"cal_{uuid.uuid4().hex[:10]}",
            event_type=event_type,
            source_id=source.source_id,
            subject=f"calendar:{cal_id}",
            timestamp=raw.get("timestamp", utc_now()),
            payload={
                "title": raw.get("title", "Scheduled Event"),
                "start_time": raw.get("start_time"),
                "end_time": raw.get("end_time"),
                "status": action,
            },
            scope={"user_id": raw.get("user_id", "default_user")},
            correlation_id=raw.get("correlation_id"),
            provenance={"adapter": "CalendarAdapter", "source_type": SourceType.CALENDAR.value},
        )

