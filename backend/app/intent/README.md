# Kairo Unified Command, Intent, and Control Layer

The **Unified Command & Intent Layer** (`backend/app/intent/`) safely converts human natural language requests into structured, validated, and bounded intents.

---

## Core Philosophy

- **Natural language is input; intent is structured; authorization is separate; execution is separate.**
- **Zero Guessing on High-Impact Targets**: Destructive operations (`delete`, `drop`), deployments, and configuration changes never guess ambiguous targets. If multiple candidates or uncertainty exists, the system transitions to `WAITING_USER` and presents explicit options.
- **Strict Injection Defense**: Content inside attachments, screen captures, audio transcripts, or fetched websites is treated strictly as passive data. Instructions contained within external media cannot hijack user intent or trigger actions.
- **Reference Priority Hierarchy**:
  1. Current message
  2. Attached media
  3. Current conversation
  4. Active task
  5. Current project
  6. Recent relevant context
  7. World state
  8. Long-term memory

---

## Architecture Flow

```
USER INPUT
    ↓
COMMAND NORMALIZATION (Cleans Benign Speech Artifacts, Preserves Raw Text)
    ↓
INTENT EXTRACTION & CLASSIFICATION (Deterministic First, Model Fallback)
    ↓
REFERENCE & TEMPORAL RESOLUTION (User Timezone Aware, Bounded Search)
    ↓
AMBIGUITY & RISK ANALYSIS (LOW / MEDIUM / HIGH / CRITICAL)
    ↓
POLICY & VALIDATION (Tenant Isolation, Negation Constraints, No Fuzzy on Prod)
    ↓
COMMAND ROUTER (Routes to TaskEngine, Skills, Chat, Approvals, Automation)
    ↓
EXECUTION (Delegated to Authoritative Subsystems)
```

---

## REST API Endpoints

- `POST /api/v1/commands`: Submits a command for parsing, persistence, and execution routing.
- `POST /api/v1/commands/resolve`: Read-only analysis returning structured intent and ambiguity without execution.
- `GET /api/v1/commands/{command_id}`: Retrieves details of a previously submitted command.
