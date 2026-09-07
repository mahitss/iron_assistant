# Kairo — Autonomous Personal AI Assistant

Kairo is an autonomous personal AI assistant designed to execute complex tasks, manage workflows, and interface seamlessly across voice, text, tools, and autonomous agent loops.

> **Status: Phase 2 — AI Brain & OpenRouter Integration**  
> This repository is currently in **Phase 2**. Kairo now possesses its core AI reasoning loop powered by OpenRouter (supporting non-streaming and streaming responses) with a provider-agnostic model layer.  
> **Important**: Tools, memory, voice, authentication, multi-agent orchestration, and frontend UI are **NOT implemented yet** and will be introduced incrementally in future phases.

---

## Architecture Overview

```text
kairo/
├── backend/                  # Python FastAPI agent service & core runtime
│   ├── app/
│   │   ├── agents/           # Autonomous agent routines & decision logic
│   │   │   └── core.py       # KairoAgent core persona & provider dispatch
│   │   ├── api/              # API endpoints, routers, and request handlers
│   │   │   ├── routes/
│   │   │   │   └── chat.py   # POST /api/v1/chat & POST /api/v1/chat/stream
│   │   │   └── health.py     # GET /health
│   │   ├── core/             # Application configuration, settings, security
│   │   │   └── config.py     # Pydantic BaseSettings & environment variables
│   │   ├── memory/           # (Deferred to Phase 4)
│   │   ├── models/           # Data schemas & model provider layer
│   │   │   ├── health.py     # Healthcheck schemas
│   │   │   ├── openrouter.py # OpenRouter provider implementation
│   │   │   └── provider.py   # ModelProvider protocol & ChatMessage schema
│   │   ├── tools/            # (Deferred to Phase 3)
│   │   └── main.py           # FastAPI application factory & router registration
│   ├── tests/                # Pytest unit and integration test suite
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

### Request Pipeline (Phase 2 Current State)

```text
User Message (Text)
       ↓
POST /api/v1/chat  OR  POST /api/v1/chat/stream
       ↓
KairoAgent (Injects System Persona)
       ↓
ModelProvider Protocol (Provider-Agnostic Interface)
       ↓
OpenRouterProvider (httpx client, streaming SSE parser)
       ↓
OpenRouter API (https://openrouter.ai/api/v1)
       ↓
Response / SSE Stream ("data: ...")
```

---

## Environment Configuration & OpenRouter Setup

1. Copy `.env.example` to create your local `.env`:
   ```bash
   cp .env.example .env
   ```
   *(On Windows PowerShell: `Copy-Item .env.example .env`)*

2. Configure OpenRouter variables in `.env`:
   ```env
   # Required for live OpenRouter API calls
   OPENROUTER_API_KEY=your_openrouter_api_key_here

   # Configurable default model (defaults to openrouter/free)
   KAIRO_MODEL=openrouter/free

   # Optional metadata sent with OpenRouter headers
   OPENROUTER_SITE_URL=http://localhost:3000
   OPENROUTER_APP_NAME=Kairo
   ```

> **Security**: Never commit `.env` or hardcode API keys anywhere in the codebase. `.gitignore` is configured to exclude environment files automatically.

---

## Running the Backend Locally

### Prerequisites
- **Python 3.12+** (Python 3.13 supported)

### 1. Create and activate a virtual environment

**On Windows (PowerShell):**
```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**On macOS / Linux:**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Start the FastAPI application
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## API Endpoints & Examples

### 1. Health Check
```bash
curl -X GET http://localhost:8000/health
```
**Response:**
```json
{
  "status": "healthy",
  "app": "Kairo",
  "version": "0.1.0",
  "environment": "development"
}
```

### 2. Chat Completion (`POST /api/v1/chat`)
Send a message and receive a complete AI response:

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello Kairo"}'
```

**Response:**
```json
{
  "message": "Hello! How can I help?"
}
```

### 3. Streaming Chat Completion (`POST /api/v1/chat/stream`)
Stream tokens via Server-Sent Events (SSE):

```bash
curl -N -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello Kairo"}'
```

**SSE Stream Output:**
```text
data: {"content": "Hello"}

data: {"content": "!"}

data: {"content": " How"}

data: {"content": " can"}

data: {"content": " I"}

data: {"content": " help"}

data: {"content": "?"}

data: [DONE]
```

---

## Running Tests

All unit and integration tests use mocked providers and mock HTTP transports—**no real API keys or external network calls are made during tests**:

```bash
cd backend
pytest
```

To run with verbose output:
```bash
pytest -v
```

---

## Incremental Roadmap

- [x] **Phase 1: Bootstrap** — Minimal repository layout, clean architecture, config, health endpoint, tests.
- [x] **Phase 2: AI Brain (OpenRouter Integration)** — Provider protocol, OpenRouter sync/stream completions, KairoAgent persona, `/api/v1/chat`, `/api/v1/chat/stream`.
- [ ] **Phase 3: Tool Execution & Verification** — Function calling sandbox, tool reflection loop.
- [ ] **Phase 4: Memory System** — Short-term context window and persistent vector memory.
- [ ] **Phase 5: Voice Pipeline** — STT & TTS streaming audio pipeline.
- [ ] **Phase 6: Frontend Interface** — Next.js + TypeScript dashboard with audio waveform visualizer.
