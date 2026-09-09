# Kairo Identity, Session Continuity, Device Trust, Presence, and Cross-Interface Handoff

## 1. Overview and Core Principle

Kairo behaves as **ONE unified assistant** across all authorized client interfaces (Web, Desktop companion, Voice, Mobile, and API). When a user switches between interfaces (e.g. from Web to Desktop, or from Desktop to Voice), Kairo maintains seamless project, task, and conversation continuity without creating contradictory state.

### The Seven Separate Concepts

The system strictly distinguishes between seven distinct concepts:

| Concept | Question Answered | Authority |
| :--- | :--- | :--- |
| **User Identity** | *"Who is this?"* | Authenticated user account (`user_id`). Existing Auth Provider. |
| **Session** | *"What authenticated interaction is this?"* | Interactive session record (`session_id`, `client_type`). |
| **Device** | *"Which client/hardware is being used?"* | Device record (`device_id`, `trust_status`). |
| **Presence** | *"Which interfaces are currently active?"* | Application-level connectivity (`ACTIVE`, `IDLE`, `DISCONNECTED`). |
| **Authorization** | *"What may this identity do?"* | `SecurityCenter` policies, approvals, and permissions. |
| **Conversation** | *"What are we discussing?"* | Conversation thread (`conversation_id`). Spans multiple sessions. |
| **Task** | *"What autonomous work is running?"* | Server-side `AutonomousTaskEngine` (`task_id`). |

---

## 2. Core Security Invariants

1. **Session $\neq$ Authorization**: Authenticating establishing an active session does **not** grant tool execution or computer access.
2. **Device Trust $\neq$ Authorization**: A device marked `TRUSTED` recognizes recognized hardware identity; it does **not** grant tool permissions or security bypasses.
3. **Capability $\neq$ Permission**: Device capability (`SCREEN`, `CAMERA`, etc.) indicates hardware support; `SecurityCenter` must authorize actual runtime access.
4. **Presence $\neq$ Permission**: Application presence tracks connectivity, not physical surveillance. Active presence grants zero elevated privileges.
5. **Replay-Safe Handoff Tokens**: Handoff tickets are single-use, cryptographically hashed, short-lived (5 min), and bound to `user_id`. Token replay and cross-user handoffs are rejected.
6. **Cascading Revocation**: Revoking a device terminates active sessions on that device, halts active computer control, and cancels pending device approvals.
7. **Emergency Stop Primacy**: Emergency Stop overrides all sessions, tasks, and device actions across all interfaces.

---

## 3. Session Architecture

### Lifecycles & Client Types
- **Client Types**: `WEB`, `DESKTOP`, `MOBILE`, `VOICE`, `API`, `LOCAL_COMPANION`.
- **Statuses**: `ACTIVE`, `EXPIRED`, `REVOKED`.
- **Expiration**: Enforces absolute TTL (default 24h) and idle timeout (default 1h).
- **Session Limits**: Enforces a configurable limit of concurrent active sessions per user (default 10). When exceeded, the oldest idle session is retired.

### Revocation & Global Sign-Out
- **Single Revocation**: `POST /api/v1/identity/sessions/{id}/revoke` terminates an individual session.
- **Sign Out Everywhere**: `POST /api/v1/identity/sessions/revoke-all` revokes all active sessions for the user.

---

## 4. Device Trust & Secure Pairing

### Trust Levels
- `UNTRUSTED`: Newly registered companion runtime. Privileged actions require strict step-up approval.
- `PENDING`: Pairing initiated, awaiting code consumption.
- `TRUSTED`: Explicitly trusted by user; trust expires after policy period (default 90 days).
- `REVOKED`: Blocked. Credentials invalidated; sessions terminated.

### Pairing Flow
1. User requests pairing code via Web or CLI: `POST /api/v1/devices/pair`.
2. Backend generates high-entropy, short-lived (10 min) code: `PAIR-XXXX-XXXX`.
3. Companion daemon sends code: `POST /api/v1/devices/pair/consume`.
4. Code is verified constant-time and **immediately consumed** so it cannot be replayed.
5. Permanent credentials are never encoded in plaintext URLs or QR codes.

---

## 5. Application Presence vs. Surveillance Boundary

- **States**: `ACTIVE`, `IDLE`, `DISCONNECTED`.
- **Non-Surveillance Guarantee**: Presence tracks application-level socket/HTTP heartbeats only. It never derives physical location, emotional state, attention, or behavioral profiling.
- **User Online State**: Surfaces `"Kairo session active"` if active sessions exist, never `"User is physically online"`.
- **Heartbeat Rate Limiting**: Minimum 5 seconds between client heartbeats to prevent traffic abuse.

---

## 6. Cross-Interface Handoff & Continuity

### Bounded Context Handoff
When moving from Web to Desktop companion:
1. Source session requests handoff with explicit user consent: `POST /api/v1/identity/handoff`.
2. Minimal relevant context (current conversation, active task, project) is packaged into a ticket. Memory and entire databases are never dumped.
3. Target session consumes the ticket: `POST /api/v1/identity/handoff/{id}/complete`.
4. Ticket is marked `consumed` immediately, preventing replay attacks.

### Task & Approval Continuity
- **Task Continuity**: The `AutonomousTaskEngine` remains server-side authoritative. Disconnecting a UI does not cancel safe background tasks.
- **Approval Continuity**: Approvals belong to `user`, `task`, `step`, and `target` (not one specific UI). An approval requested for a Desktop task can be approved from Web.
- **Stale Approval Invalidation**: If the action or target parameters change before execution, the cryptographic fingerprint mismatches and the approval is rejected.

### Ambiguity Handling
If a user has multiple running tasks or multiple connected devices and issues an ambiguous request like *"Continue"* or *"Share my screen"*, Kairo **does not guess**—it prompts the user to select the intended target.

---

## 7. REST API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/identity/sessions` | List active sessions |
| `POST` | `/api/v1/identity/sessions` | Create new interactive session |
| `POST` | `/api/v1/identity/sessions/{id}/revoke` | Revoke session |
| `POST` | `/api/v1/identity/sessions/revoke-all` | Sign out everywhere |
| `GET` | `/api/v1/identity/presence` | List interface presence |
| `POST` | `/api/v1/identity/presence/heartbeat` | Send rate-limited heartbeat |
| `GET` | `/api/v1/identity/presence/online-status` | Get aggregated online state |
| `POST` | `/api/v1/identity/handoff` | Create single-use handoff ticket |
| `POST` | `/api/v1/identity/handoff/{id}/complete` | Complete handoff with token |
| `GET` | `/api/v1/identity/continuity/task` | Resolve active task continuity |
| `GET` | `/api/v1/identity/continuity/device` | Resolve target device |
| `POST` | `/api/v1/devices/{id}/trust` | Explicitly update device trust |
| `POST` | `/api/v1/devices/pair` | Initiate device pairing |
| `POST` | `/api/v1/devices/pair/consume` | Consume pairing code |
