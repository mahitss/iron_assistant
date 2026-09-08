# Kairo — Autonomous Personal AI Assistant

Kairo is an autonomous personal AI assistant designed to execute complex tasks, manage workflows, and interface seamlessly across voice, text, tools, memory, and autonomous agent loops.

> **Status: Phase 6 — Intelligent Memory Layer**  
> This repository is currently in **Phase 6**. Kairo now features an intelligent, automated long-term memory layer:
> 1. **Automated Memory Extraction**: After a conversation turn, a dedicated fast model extracts durable candidate memories (preferences, facts, projects, instructions) without blocking the user response.
> 2. **Deterministic Memory Policy**: Candidate memories are strictly validated and sanitized. Secrets, tokens, transient arithmetic, and casual banter are strictly rejected.
> 3. **Semantic Deduplication**: Before persisting, candidates are compared against existing memories. If similarity is above the configurable threshold (default `0.90`), the existing record is updated rather than duplicated.
> 4. **User Control Endpoints**: Safe `GET /api/v1/memories` and `DELETE /api/v1/memories/{memory_id}` endpoints allow users to inspect and delete persisted memories.
> 5. **Core Philosophy**: *"The model proposes memories; the application validates and persists them."*
> 
> **Important**: Voice STT/TTS, browser automation, GitHub tools, computer control, autonomous background tasks, and frontend UI are **NOT implemented yet** and will be introduced incrementally in future phases.

---

## Architecture Overview

```text
kairo/
├── backend/                  # Python FastAPI agent service & core runtime
│   ├── alembic.ini           # Alembic database migration configuration
│   ├── app/
│   │   ├── agents/           # Autonomous agent routines & decision logic
│   │   │   └── core.py       # KairoAgent core persona, tool iteration loop, memory integration
│   │   ├── api/              # API endpoints, routers, and request handlers
│   │   │   ├── routes/
│   │   │   │   ├── chat.py   # POST /api/v1/chat & POST /api/v1/chat/stream
│   │   │   │   └── memory.py # Internal dev memory endpoints (/api/v1/internal/memories)
│   │   │   └── health.py     # GET /health
│   │   ├── core/             # Application configuration, settings, security
│   │   │   └── config.py     # Pydantic BaseSettings & environment variables
│   │   ├── db/               # Relational persistence & migrations
│   │   │   ├── session.py    # Async SQLAlchemy 2.x engine and sessionmaker
│   │   │   └── migrations/   # Alembic versioned migrations (0001_initial)
│   │   ├── memory/           # Memory layer components
│   │   │   ├── extractor.py  # MemoryExtractor: LLM candidate extraction via fast capability
│   │   │   ├── policies.py   # MemoryPolicy: deterministic safety, relevance, and bounds checks
│   │   │   ├── models.py     # SQLAlchemy models: Conversation, Message, Memory (pgvector)
│   │   │   ├── schemas.py    # Pydantic models: MemoryCandidate, MemoryResponse, MemoryType
│   │   │   ├── repository.py # ConversationRepository & MemoryRepository (pgvector search)
│   │   │   ├── service.py    # MemoryService: candidate processing, dedup, ranking & context
│   │   │   ├── embeddings.py # EmbeddingProvider abstraction (OpenAI, OpenRouter, Deterministic)
│   │   │   ├── sanitizer.py  # MemorySanitizer: regex defense-in-depth secret detection
│   │   │   └── session.py    # SessionManager: Redis cache with TTL & in-memory fallback
│   │   ├── models/           # Model provider, registry, and router layer
│   │   │   ├── health.py     # Healthcheck schemas
│   │   │   ├── openrouter.py # OpenRouter OpenAI-compatible client with tool calling
│   │   │   ├── provider.py   # ModelProvider protocol, ChatMessage, ProviderResponse
│   │   │   ├── registry.py   # ModelCapability, ModelDefinition, ModelRegistry
│   │   │   └── router.py     # ModelRouter (capability matching, priority, fallback)
│   │   ├── tools/            # Tool framework & built-in safe starters
│   │   │   ├── base.py       # BaseTool contract & ToolDefinition
│   │   │   ├── executor.py   # ToolExecutor (validation, permission check, verification)
│   │   │   ├── permissions.py# PermissionLevel (READ, WRITE, EXTERNAL, DESTRUCTIVE)
│   │   │   ├── registry.py   # ToolRegistry & schema generator
│   │   │   ├── schemas.py    # ToolCall & ToolResult schemas
│   │   │   └── builtin/      # Safe starter tools (calculator, datetime, system_info)
│   │   └── main.py           # FastAPI application factory & router registration
│   ├── tests/                # Pytest unit and integration test suite (90 tests)
│   ├── pyproject.toml        # Python project metadata & tool configurations
│   └── requirements.txt      # Backend dependencies (FastAPI, SQLAlchemy, pgvector, Redis, Alembic)
├── frontend/                 # Reserved for Next.js + TypeScript web UI
├── infra/                    # Cloud infrastructure & deployment scripts
├── docker/                   # Docker container definitions
│   └── Dockerfile.backend    # Backend container definition (Python 3.12+ slim)
├── .env.example              # Environment variables template (no hardcoded secrets)
├── .gitignore                # Git ignore rules for Python, Node, IDEs, envs
├── docker-compose.yml        # Docker Compose configuration (Postgres+pgvector, Redis, Backend)
└── README.md                 # Project documentation
```

---

## Memory System Architecture

Kairo maintains strict architectural separation between three memory categories:

```text
User Request
     ↓
Kairo Core Agent
 ├── 1. Short-Term Memory (Redis)
 │      └── Ephemeral session state, active context metadata, TTL-based.
 │
 ├── 2. Conversation History (PostgreSQL)
 │      └── Authoritative multi-turn history: user, assistant, and tool messages.
 │
 ├── 3. Long-Term Memory (PostgreSQL + pgvector)
 │      └── Curated persistent memories retrieved via semantic similarity search.
 │
 └── 4. Model Router → Model Provider → Tool Loop
```

### 1. Short-Term Memory vs Long-Term Memory

| Feature | Short-Term Memory | Conversation History | Long-Term Memory |
| :--- | :--- | :--- | :--- |
| **Storage Engine** | Redis | PostgreSQL | PostgreSQL + pgvector |
| **Nature** | Ephemeral, cached | Persistent log of turns | Persistent curated facts/prefs |
| **Lifespan** | Configurable TTL (default 1 hr) | Persistent per session | Survives across all sessions |
| **Retrieval** | Key lookup by `session_id` | Chronological bounded query | Semantic vector cosine similarity |
| **Fault Tolerance** | In-memory fallback if down | Authoritative source of truth | Fails gracefully if unconfigured |

### 2. Semantic Retrieval & Ranking
When a user query arrives, `MemoryService` performs semantic retrieval:
1. Generates query vector embedding via `EmbeddingProvider`.
2. Computes cosine distance against candidate memory vectors using `pgvector` (`<->` operator) in PostgreSQL (or Python fallback in SQLite/tests).
3. Applies a **deterministic, explainable composite score**:
   $$\text{Score} = 0.70 \times \text{Similarity} + 0.20 \times \text{Importance} + 0.10 \times \text{Recency}$$
   - **Similarity** ($0.0 - 1.0$): Vector semantic proximity.
   - **Importance** ($0.0 - 1.0$): Explicit priority assigned at creation.
   - **Recency** ($0.0 - 1.0$): Linear decay over 30 days based on `updated_at`.
4. Ranks candidates and returns the top $K$ memories (bounded by `KAIRO_MEMORY_TOP_K`, default 5).
5. Updates `last_accessed_at` timestamp on retrieved records.

### 3. Memory Context Formatting
Retrieved memories are injected cleanly into the model prompt without exposing database IDs, vector embeddings, or internal metadata:
```text
Relevant memories:
- User prefers concise technical explanations.
- Kairo backend uses FastAPI and PostgreSQL with pgvector.
- Current project phase is memory integration.
```

### 4. Memory Safety & Secret Sanitization
Before any persistent memory is saved, `MemorySanitizer` runs a defense-in-depth regex filter checking for sensitive values:
- OpenAI / OpenRouter / generic API keys (`sk_...`, `pk_...`)
- GitHub access tokens (`ghp_...`, `gho_...`)
- AWS access keys (`AKIA...`)
- Private cryptographic keys (`-----BEGIN PRIVATE KEY-----`)
- Explicit passwords or credentials (`password: ...`, `api_key is ...`)
- Bearer tokens and session cookies

If detected, explicit creation raises an `UnsafeMemoryError` and rejects the persistence attempt.

> [!NOTE]
> `MemorySanitizer` provides basic defense-in-depth. It does not claim to detect every possible secret or custom format.

### 5. Intelligent Memory Extraction Layer

> [!IMPORTANT]
> **"The model proposes memories; the application validates and persists them."**
> The LLM is never given direct access to the database or SQL. `MemoryService` remains the sole persistence authority.

```text
User Message
      ↓
Kairo Core (retrieves top-K existing memories)
      ↓
Generate Assistant Response & Execute Tools
      ↓
Return Response to User (Zero Turn Latency Block)
      ↓
Memory Extractor (Dedicated Fast Capability Model)
      ↓
Candidate Memories (Pydantic Schema: content, memory_type, importance, reason)
      ↓
Memory Policy / Validation (Deterministic safety, length, secret & relevance filters)
      ↓
Semantic Deduplication (pgvector search: similarity >= KAIRO_MEMORY_DEDUP_THRESHOLD)
      ↓
Embed Candidate Vector (Deterministic / OpenAI / OpenRouter)
      ↓
Persist to PostgreSQL + pgvector (Insert new or update existing)
```

#### Why Not Every Message Becomes a Memory
To prevent memory bloat and context pollution, Kairo filters out ephemeral chatter:
- **Remembered**: Durable user preferences (*"I prefer dark mode"*), project facts (*"I'm building Kairo"*), explicit instructions (*"Always write tests in pytest"*), persistent context.
- **Ignored (No Memory Created)**: Transient math (*"What's 25 * 4?"*), casual greetings (*"Hello"*, *"How are you?"*), debugging output, temporary questions, short filler.
- **Rejected (Safety Violation)**: Credentials, API keys, passwords, bearer tokens, and private keys.

#### Semantic Deduplication & Updates
Before persisting a validated candidate:
1. `MemoryService` queries existing memories using vector cosine similarity.
2. If an existing memory has similarity $\ge$ `KAIRO_MEMORY_DEDUP_THRESHOLD` (default `0.90`):
   - The existing record is **updated** in place with the fresh content and refreshed timestamp.
   - Contradictory or stale memories are cleanly replaced without building an overcomplicated knowledge graph.
3. If similarity $< 0.90$, a new memory record is inserted.

#### Asynchronous & Non-Blocking Resilience
- Memory extraction runs **after** the assistant's final response has been formulated and sent.
- If the extraction model fails, times out, or returns malformed JSON:
  - Normal chat **always succeeds** without interruption.
  - A safe warning is logged without exposing user content or credentials.
  - No fake or corrupted memories are written.

---

## Environment Configuration

Copy `.env.example` to create your local `.env`:
```bash
cp .env.example .env
```

Key environment variables:
```env
# OpenRouter & Model Router Configuration (Task 3)
OPENROUTER_API_KEY=your_openrouter_api_key_here
KAIRO_MODEL=openrouter/free
KAIRO_ROUTING_ENABLED=true

# Database & Persistent Memory Configuration (Task 5)
DATABASE_URL=postgresql+asyncpg://kairo:kairo_secret@localhost:5432/kairo
REDIS_URL=redis://localhost:6379/0

# Embedding Provider Configuration (Task 5)
# Options: deterministic (for local testing/zero external deps), openai, or openrouter
KAIRO_EMBEDDING_PROVIDER=
KAIRO_EMBEDDING_MODEL=

# Memory System Context Bounds (Task 5)
KAIRO_MEMORY_TOP_K=5
KAIRO_MAX_CONTEXT_MESSAGES=20
KAIRO_REDIS_TTL_SECONDS=3600

# Intelligent Memory Extraction (Task 6)
KAIRO_MEMORY_EXTRACTION_ENABLED=true
KAIRO_MEMORY_DEDUP_THRESHOLD=0.90
KAIRO_MEMORY_EXTRACTION_CAPABILITY=fast
```

---

## Local Database Setup & Migrations

### 1. Start Services via Docker Compose
Start PostgreSQL (with pgvector) and Redis in the background:
```bash
docker compose up -d postgres redis
```

### 2. Run Database Migrations (Alembic)
Run migrations using Alembic:
```bash
cd backend
alembic upgrade head
```

To rollback a migration:
```bash
alembic downgrade -1
```

To generate a new migration revision:
```bash
alembic revision --autogenerate -m "describe_changes"
```

---

## Running the Backend Locally

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## API Endpoints & Examples

### 1. Health Check
```bash
curl -X GET http://localhost:8000/health
```

### 2. Multi-turn Chat with Session ID (`POST /api/v1/chat`)

**First Turn (creates session):**
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hi, my name is Alice."}'
```
**Response:**
```json
{
  "message": "Hello Alice! How can I assist you today?",
  "session_id": "sess_89f021adbc43",
  "model": "openrouter/free",
  "tools_used": null
}
```

**Second Turn (same session, remembers context):**
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is my name?", "session_id": "sess_89f021adbc43"}'
```
**Response:**
```json
{
  "message": "Your name is Alice.",
  "session_id": "sess_89f021adbc43",
  "model": "openrouter/free",
  "tools_used": null
}
```

### 3. Explicit Memory Creation (`POST /api/v1/internal/memories`)
```bash
curl -X POST http://localhost:8000/api/v1/internal/memories \
  -H "Content-Type: application/json" \
  -d '{
    "content": "User prefers concise Python code examples.",
    "memory_type": "preference",
    "importance": 0.85
  }'
```

### 4. Semantic Memory Search (`GET /api/v1/internal/memories/search`)
```bash
curl -X GET "http://localhost:8000/api/v1/internal/memories/search?q=Python+preferences&top_k=3"
```

### 5. Streaming Response (`POST /api/v1/chat/stream`)
```bash
curl -N -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the time in UTC?", "session_id": "sess_89f021adbc43"}'
```

### 6. User Memory Inspection & Deletion (`GET /api/v1/memories` & `DELETE /api/v1/memories/{id}`)

**List Persisted Memories:**
```bash
curl -X GET "http://localhost:8000/api/v1/memories?limit=10"
```
**Response:**
```json
[
  {
    "id": "c1f2b6e8-3a9d-4e17-b089-1144558899aa",
    "content": "User prefers dark mode.",
    "memory_type": "preference",
    "importance": 0.85,
    "last_accessed_at": "2026-09-08T16:00:00Z",
    "created_at": "2026-09-08T15:30:00Z",
    "updated_at": "2026-09-08T15:30:00Z"
  }
]
```

**Delete a Memory:**
```bash
curl -X DELETE http://localhost:8000/api/v1/memories/c1f2b6e8-3a9d-4e17-b089-1144558899aa
```
**Response:**
```json
{
  "deleted": true,
  "memory_id": "c1f2b6e8-3a9d-4e17-b089-1144558899aa"
}
```

---

## Running Tests

The test suite contains **113 unit and integration tests** verifying repositories, memory sanitization, candidate extraction, safety policies, semantic deduplication, session management, router selection, and tool execution without requiring external network connections or live databases:

```bash
cd backend
pytest -v
```

---

## Incremental Roadmap

- [x] **Phase 1: Bootstrap** — Minimal repository layout, clean architecture, config, health endpoint, tests.
- [x] **Phase 2: AI Brain (OpenRouter Integration)** — Provider protocol, OpenRouter sync/stream completions, KairoAgent persona.
- [x] **Phase 3: Model Router** — Capability taxonomy, ModelDefinition, ModelRegistry, ModelRouter priority matching & fallback.
- [x] **Phase 4: Tool System & Safe Starters** — BaseTool contract, ToolRegistry, ToolExecutor, permissions, calculator (AST safe), datetime, system_info.
- [x] **Phase 5: Memory System** — Redis short-term cache, PostgreSQL conversation history, pgvector semantic long-term memory, composite ranking, Alembic migrations.
- [x] **Phase 6: Intelligent Memory Layer** — Post-turn candidate extraction, deterministic memory policy, semantic deduplication, non-blocking async execution, user inspection and deletion API.
- [ ] **Phase 7: Voice Pipeline** — STT & TTS streaming audio pipeline.
- [ ] **Phase 8: Frontend Interface** — Next.js + TypeScript dashboard with audio waveform visualizer.
