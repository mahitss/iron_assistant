# Kairo — Autonomous Personal AI Assistant

Kairo is an autonomous personal AI assistant designed to execute complex tasks, manage workflows, and interface seamlessly across voice, text, tools, and autonomous agent loops.

> **Status: Phase 3 — Intelligent Model Router & Capability Layer**  
> This repository is currently in **Phase 3**. Kairo now features a dedicated, provider-agnostic **Model Routing Layer** that dynamically selects the optimal configured AI model based on task capability requirements (e.g., coding, reasoning, fast, vision, general) while maintaining safe fallback behaviors.  
> **Important**: Tools, persistent memory, voice STT/TTS, authentication, multi-agent orchestration, and frontend UI are **NOT implemented yet** and will be introduced incrementally in future phases.

---

## Architecture Overview

```text
kairo/
├── backend/                  # Python FastAPI agent service & core runtime
│   ├── app/
│   │   ├── agents/           # Autonomous agent routines & decision logic
│   │   │   └── core.py       # KairoAgent core persona, heuristic classifier & routing
│   │   ├── api/              # API endpoints, routers, and request handlers
│   │   │   ├── routes/
│   │   │   │   └── chat.py   # POST /api/v1/chat & POST /api/v1/chat/stream
│   │   │   └── health.py     # GET /health
│   │   ├── core/             # Application configuration, settings, security
│   │   │   └── config.py     # Pydantic BaseSettings & environment variables
│   │   ├── memory/           # (Deferred to Phase 4)
│   │   ├── models/           # Model provider, registry, and router layer
│   │   │   ├── health.py     # Healthcheck schemas
│   │   │   ├── openrouter.py # OpenRouter OpenAI-compatible client
│   │   │   ├── provider.py   # ModelProvider protocol & ChatMessage schema
│   │   │   ├── registry.py   # ModelCapability, ModelDefinition, ModelRegistry
│   │   │   └── router.py     # ModelRouter (capability matching, priority, fallback)
│   │   ├── tools/            # (Deferred to Phase 4+)
│   │   └── main.py           # FastAPI application factory & router registration
│   ├── tests/                # Pytest unit and integration test suite (37 tests)
│   ├── pyproject.toml        # Python project metadata & tool configurations
│   └── requirements.txt      # Minimal backend dependencies
├── frontend/                 # Reserved for Next.js + TypeScript web UI
├── infra/                    # Cloud infrastructure & deployment scripts
├── docker/                   # Docker container definitions
│   └── Dockerfile.backend    # Backend container definition (Python 3.12+ slim)
├── .env.example              # Environment variables template (no hardcoded secrets)
├── .gitignore                # Git ignore rules for Python, Node, IDEs, envs
├── docker-compose.yml        # Docker Compose configuration for multi-service setup
└── README.md                 # Project documentation
```

### Request Pipeline (Phase 3 Current State)

```text
User Request (Message + Optional Capability)
       ↓
POST /api/v1/chat  OR  POST /api/v1/chat/stream
       ↓
Resolve Capability (e.g. "coding", "reasoning", "general")
       ↓
ModelRouter (Inspects ModelRegistry)
  ├── 1. Matches highest-priority enabled model for capability
  └── 2. Falls back safely to default target (KAIRO_MODEL) if no match
       ↓
KairoAgent (Injects System Persona + Constructs ChatMessages)
       ↓
ModelProvider Protocol (Provider-Agnostic Interface)
       ↓
OpenRouterProvider (httpx client, streaming SSE parser)
       ↓
OpenRouter API (https://openrouter.ai/api/v1)
       ↓
Response with Model Metadata {"message": "...", "model": "..."}
```

---

## Model Router & Capabilities

### What the Model Router Does

The **Model Router** decouples the agent core and API routes from specific downstream models. Rather than hardcoding model IDs in application code, requests declare or infer an abstract **capability**. The router searches its registry of enabled models, sorts compatible candidates by priority, and selects the best model.

### Supported Capabilities

| Capability | Description | Example Target |
|---|---|---|
| `general` | Everyday chat, general inquiries, general synthesis | `meta-llama/llama-3.3-70b-instruct` |
| `reasoning` | Multi-step logic, math problems, theorem validation | `deepseek/deepseek-r1` |
| `coding` | Software engineering, debugging, code generation | `qwen/qwen-2.5-coder-32b-instruct` |
| `vision` | Visual input understanding, OCR, document inspection | `google/gemini-2.0-flash-001` |
| `fast` | Ultra-low-latency responses, lightweight summarization | `openrouter/free` |
| `tool_calling` | Function invocation and structured tool arguments | `google/gemini-2.0-flash-001` |
| `structured_output` | Strict JSON schema generation | `qwen/qwen-2.5-coder-32b-instruct` |

### Default Fallback Behavior

- If a requested capability has compatible enabled models, the model with the **highest priority** is chosen.
- If no compatible model is registered or enabled for that capability, the router **falls back to the configured default model** (`KAIRO_MODEL`, default: `openrouter/free`).
- If `KAIRO_ROUTING_ENABLED=false`, all requests immediately route to `KAIRO_MODEL`.
- Disabled models are never returned.
- If the fallback model itself is disabled or missing, a clean `NoUsableModelError` (HTTP 503) is raised.

### Dynamic Catalog vs. Hardcoded Free Models

We deliberately **do NOT hardcode a permanent list of "free models"**:
1. Upstream providers frequently add, rename, rate-limit, or retire specific free model endpoints.
2. `openrouter/free` is treated as a **dynamic router target** on OpenRouter that resolves to current available free models upstream, rather than pretending it is a static single model.
3. The `ModelRegistry` allows adding, disabling, or re-prioritizing models dynamically at startup or via configuration without touching business logic.

---

## Environment Configuration

1. Copy `.env.example` to create your local `.env`:
   ```bash
   cp .env.example .env
   ```

2. Configure environment variables in `.env`:
   ```env
   # Required for live OpenRouter API calls
   OPENROUTER_API_KEY=your_openrouter_api_key_here

   # Default model fallback (defaults to openrouter/free)
   KAIRO_MODEL=openrouter/free

   # Enable/disable capability routing (default: true)
   KAIRO_ROUTING_ENABLED=true

   # Optional metadata sent with OpenRouter headers
   OPENROUTER_SITE_URL=http://localhost:3000
   OPENROUTER_APP_NAME=Kairo
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

### 2. General Chat (`POST /api/v1/chat`)
Omitting `capability` automatically defaults to `general`:

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello Kairo"}'
```

**Response (includes selected `model` metadata):**
```json
{
  "message": "Hello! How can I help?",
  "model": "meta-llama/llama-3.3-70b-instruct"
}
```

### 3. Capability-Routed Chat (`capability: "coding"`)
Request a coding specialist model:

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Write a binary search in Python", "capability": "coding"}'
```

**Response:**
```json
{
  "message": "def binary_search(arr, target): ...",
  "model": "qwen/qwen-2.5-coder-32b-instruct"
}
```

### 4. Streaming with Model Metadata (`POST /api/v1/chat/stream`)
The initial SSE event emits the selected `model`, followed by text `content` chunks, and terminates with `[DONE]`:

```bash
curl -N -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Explain recursion", "capability": "coding"}'
```

**SSE Stream Output:**
```text
data: {"model": "qwen/qwen-2.5-coder-32b-instruct"}

data: {"content": "Recursion"}

data: {"content": " is"}

data: {"content": " a"}

data: {"content": " method"}

data: [DONE]
```

---

## Running Tests

All 37 unit and integration tests execute with zero external network dependencies using mocked providers:

```bash
cd backend
pytest -v
```

---

## Incremental Roadmap

- [x] **Phase 1: Bootstrap** — Minimal repository layout, clean architecture, config, health endpoint, tests.
- [x] **Phase 2: AI Brain (OpenRouter Integration)** — Provider protocol, OpenRouter sync/stream completions, KairoAgent persona.
- [x] **Phase 3: Model Router** — Capability taxonomy, ModelDefinition, ModelRegistry, ModelRouter priority matching & fallback, model response metadata.
- [ ] **Phase 4: Tool Execution & Verification** — Function calling sandbox, tool reflection loop.
- [ ] **Phase 5: Memory System** — Short-term context window and persistent vector memory.
- [ ] **Phase 6: Voice Pipeline** — STT & TTS streaming audio pipeline.
- [ ] **Phase 7: Frontend Interface** — Next.js + TypeScript dashboard with audio waveform visualizer.
