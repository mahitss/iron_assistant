# Kairo Identity, Session Continuity, Device Trust, Presence, and Handoff

The Kairo Identity subsystem enables Kairo to behave as **ONE unified assistant** across all authorized interfaces (Web, Desktop companion, Voice, Mobile, API) while strictly preserving security boundaries and tenant isolation.

---

## 1. Core Architectural Distinctions

Kairo strictly separates the following concepts into separate objects:

| Concept | Answers | Key Model / Attribute |
| :--- | :--- | :--- |
| **Identity** | *"Who is this?"* | `user_id` from existing authenticated identity provider |
| **Session** | *"What authenticated interaction is this?"* | `session_id`, `client_type`, `created_at`, `expires_at`, `status` |
| **Device** | *"Which client/hardware is being used?"* | `device_id`, `trust_status`, `capabilities` |
| **Presence** | *"Which interfaces are currently active?"* | `ACTIVE`, `IDLE`, `DISCONNECTED` (Application-level only) |
| **Authorization** | *"What may this identity do?"* | Strictly governed by `SecurityCenter` |
| **Conversation** | *"What are we discussing?"* | `conversation_id` (spans multiple sessions) |
| **Task** | *"What autonomous work is running?"* | `task_id` (governed by `AutonomousTaskEngine`) |

---

## 2. Invariant Rules & Security Guarantees

1. **Session $\neq$ Authorization**: Authenticating establishing an active session does **not** grant tool or computer access.
2. **Device Trust $\neq$ Authorization**: Recognizing a device as `TRUSTED` does **not** authorize dangerous actions or bypass security policies.
3. **Capability $\neq$ Permission**: Hardware support for `SCREEN` or `CAMERA` does not grant permission to capture media without explicit SecurityCenter policy and approval.
4. **Presence $\neq$ Permission**: Application presence tracks connectivity, never physical surveillance. Active presence grants zero elevated privileges.
5. **No AI Model Privilege Escalation**: Models cannot grant device trust, create devices, or approve handoffs.
6. **Single-Use Replay-Safe Handoff**: Handoff tokens are cryptographically hashed, short-lived (5 min), single-use, and scoped. Replay attempts are rejected.
7. **Cascading Revocation**: Revoking a device terminates all active sessions bound to it, invalidates credentials, halts computer control, and cancels pending approvals.

---

## 3. Subsystem Components

- `models.py`: Declarative SQLAlchemy models (`IdentitySessionModel`, `IdentityPresenceModel`, `HandoffContextModel`).
- `schemas.py`: Pydantic models for client types, session states, device trust levels, presence, and handoff packets.
- `tokens.py`: High-entropy token generation, pairing codes, and constant-time verification.
- `identity.py`: Tenant validation and identity resolution adapter reusing existing auth.
- `sessions.py`: `SessionManager` handling lifecycle, idle timeouts, session limits, and global sign out.
- `devices.py`: `IdentityDeviceManager` for registration, capabilities, and pairing flows.
- `trust.py`: `DeviceTrustManager` for explicit trust transitions and expiration.
- `presence.py`: `PresenceTracker` for rate-limited heartbeats and non-surveillance online state.
- `handoff.py`: `HandoffManager` providing bounded context transfer with replay protection.
- `policies.py`: `IdentityPolicyEnforcer` guaranteeing security invariants across all endpoints.
- `revocation.py`: `RevocationCoordinator` executing cascading revocations.
- `resolver.py`: `IdentityResolver` for cross-interface task continuity and target ambiguity resolution.
