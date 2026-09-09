# Kairo Social & Communication Intelligence Engine (Task 49)

The Social & Communication Intelligence Engine empowers Kairo to understand, track, organize, draft, and coordinate authorized communications across diverse modalities (email, chat, SMS, meetings, voice, comments, collaboration workspaces, and notifications) while strictly enforcing governance, safety, and privacy.

---

## 1. Core Architecture & Pipeline

```text
RECEIVE
   ↓
NORMALIZE
   ↓
THREAD (Anti-False-Merging)
   ↓
UNDERSTAND & PROMPT INJECTION DEFENSE
   ↓
CLASSIFY (14 Categories)
   ↓
EXTRACT ACTIONS (Grounded Commitments & Temporal Deadlines)
   ↓
DETERMINE RESPONSE NEED (NO_RESPONSE, OPTIONAL, RECOMMENDED, REQUIRED)
   ↓
DRAFT / SUGGEST (Tone Adaptation, Provenance, Anti-Hallucination)
   ↓
AUTHORIZATION (Explicit Channel & Recipient Gates)
   ↓
POLICY (High-Risk Gating, Secrets, PII, Quiet Hours)
   ↓
SEND (Strictly Delegated via ToolExecutor; Zero Direct Network Calls)
   ↓
VERIFY (Authoritative Receipts; Delivery != Read; Sent != Completed)
   ↓
RECORD (Immutable Append-Only Audit Trail)
```

---

## 2. Invariants & Security Rules

1. **Zero Direct Dispatch**: The engine NEVER directly connects to SMTP, IMAP, or HTTP endpoints. All dispatches pass through `ToolExecutor`.
2. **Draft $\neq$ Sent**: A draft message is strictly isolated and can never be marked or represented as sent prior to delivery verification.
3. **No Fabricated Commitments**: Never invent commitments for the user or meeting participants. Only explicit first-person and attributed promises are recorded.
4. **No Social/Psychological Profiling**: Sentiment is treated as an uncertain operational heuristic signal, NEVER clinical or psychological certainty. Safe relationship categories only (`TEAMMATE`, `COLLABORATOR`, `CLIENT`, `VENDOR`, `CONTACT`, `FRIEND`, `FAMILY`, `COMMUNITY`, `UNKNOWN`).
5. **Contact & Recipient Ambiguity**: If a contact query or pronoun matches multiple candidates, execution is halted and user confirmation is required before any consequential send.
6. **Anti-False Thread Merging**: Unrelated conversations sharing generic keywords (e.g. "update", "meeting") are never merged into a single thread without explicit references or identical subjects.
7. **Secret & PII Defense**: Outbound content is scanned against credential patterns and secret tokens. Potential leaks trigger immediate blocking.
8. **Quiet Hours & Rate Limiting**: Outbound non-critical communications during quiet hours are blocked unless explicit critical override policy is active.
9. **Immutable History**: Sent messages and audit events are sealed in append-only storage and cannot be rewritten.
10. **Delivery Verification**: `SENT` $\neq$ `DELIVERED`, and `DELIVERED` $\neq$ `READ`. Network failures do not trigger blind resends.
