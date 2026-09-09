# Kairo Unified Notification, Communication, Delivery, Priority, and Alerting Layer

## Overview
The **Unified Notification Layer** provides Kairo with ONE centralized communication system for delivering prioritized, meaningful, and actionable signals to authorized users across multiple interfaces (Web Command Center, Desktop Companion, Voice, Push, Email).

## Core Principles
1. **Events $\neq$ Notifications**: An event is an internal system state transition (e.g. `task.completed`). A notification is an attention-oriented, user-facing communication. Many events may result in zero notifications, one notification, or a grouped summary.
2. **Priority Integrity**: System policy dictates priority (`LOW`, `NORMAL`, `HIGH`, `URGENT`). Model-generated claims or text cannot override policy.
3. **Safe Interactive Actions**: Notification action buttons NEVER execute direct raw database mutations. They delegate to authoritative subsystems (`ApprovalManager`, `TaskEngine`) after full authentication and authorization.
4. **Storm & Spam Defenses**: Rapid event storms are automatically collapsed into high-level summaries without suppressing urgent security or approval alerts.
5. **Privacy by Design**: Lock screens and external push payloads receive safe minimal previews without secrets, tokens, or private credentials.

## Subsystem Architecture
```
notifications/
├── __init__.py           # Module exports
├── models.py             # SQLAlchemy models (notifications, actions, deliveries, preferences)
├── schemas.py            # Pydantic schemas and enums
├── priority.py           # PriorityResolver (Priority Integrity)
├── dedupe.py             # NotificationDeduplicator (deterministic dedupe_key)
├── grouping.py           # NotificationGrouper (event coalescing)
├── throttling.py         # NotificationThrottler (rate limits & storm detection)
├── policy.py             # NotificationPolicy (delivery decisions)
├── preferences.py        # NotificationPreferencesManager (quiet hours)
├── channels.py           # Channel abstraction & capabilities (Web, Desktop, Voice, Push, Email)
├── delivery.py           # NotificationDeliveryCoordinator (presence & fallback routing)
├── templates.py          # Safe typed templates (HTML & prompt injection sanitization)
├── actions.py            # NotificationActionDispatcher (idempotent, safe execution)
├── escalation.py         # PriorityEscalationPolicy
├── digest.py             # Periodic digest generation
├── retry.py              # DeliveryRetryManager (bounded exponential backoff)
├── retention.py          # NotificationRetentionManager (expiration & cleanup)
├── service.py            # UnifiedNotificationService facade
├── router.py             # FastAPI REST endpoints
└── README.md
```
