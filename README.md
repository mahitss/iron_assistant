# Kairo — Autonomous Personal AI Assistant

Kairo is an autonomous personal AI assistant designed to execute complex tasks, manage workflows, and interface seamlessly across voice, text, tools, and autonomous agent loops.

> **Status: Phase 4 — Extensible Tool Framework & Safe Starter Tools**  
> This repository is currently in **Phase 4**. Kairo now features a generic, secure, provider-agnostic **Tool Framework** with argument validation (Pydantic), permission checking, lifecycle execution, output verification, and an internal multi-turn tool loop.  
> **Important**: Memory persistence, voice STT/TTS, authentication, multi-agent orchestration, web automation, filesystem writes, and frontend UI are **NOT implemented yet** and will be introduced incrementally in future phases.

---

## Architecture Overview

```text
kairo/
├── backend/                  # Python FastAPI agent service & core runtime
│   ├── app/
│   │   ├── agents/           # Autonomous agent routines & decision logic
│   │   │   └── core.py       # KairoAgent core persona, tool iteration loop (MAX_ITERATIONS=5)
│   │   ├── api/              # API endpoints, routers, and request handlers
│   │   │   ├── routes/
│   │   │   │   └── chat.py   # POST /api/v1/chat & POST /api/v1/chat/stream
│   │   │   └── health.py     # GET /health
│   │   ├── core/             # Application configuration, settings, security
│   │   │   └── config.py     # Pydantic BaseSettings & environment variables
│   │   ├── memory/           # (Deferred to Phase 5)
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
│   │   │   └── builtin/      # Safe starter tools
│   │   │       ├── calculator.py  # AST-based safe arithmetic (no eval/exec)
│   │   │       ├── datetime.py    # Timezone-aware date and time inspector
│   │   │       └── system_info.py # Read-only OS and runtime metadata
│   │   └── main.py           # FastAPI application factory & router registration
│   ├── tests/                # Pytest unit and integration test suite (62 tests)
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

### Tool Execution Lifecycle

```text
User Request ("What is 15 * 4?")
       ↓
KairoAgent (Inspects Available Tool Schemas)
       ↓
Model Provider (OpenRouter with tools payload)
       ↓
LLM emits structured tool call: calculator(expression="15 * 4")
       ↓
ToolExecutor
  ├── 1. Registry Lookup: finds CalculatorTool
  ├── 2. Permissions Check: verifies READ is AUTO_ALLOWED
  ├── 3. Argument Validation: parses expression via Pydantic
  ├── 4. Safe Execution: AST-based evaluator evaluates without eval()
  ├── 5. Output Verification: confirms finite numeric output
  └── 6. Produces structured ToolResult(success=True, result=60)
       ↓
Tool message appended to conversation history
       ↓
LLM receives tool result
       ↓
Final response: "15 * 4 is 60." (with safe tool activity metadata)
```

---

## Tool Framework Architecture

### 1. Tool Contract (`BaseTool` & `ToolDefinition`)
Every tool inherits from `BaseTool` and declares:
- `name`: Unique identifier (e.g. `calculator`)
- `description`: Model-facing prompt explanation
- `permission_level`: Risk level classification
- `args_model`: Pydantic schema for strict input parsing
- `execute(**kwargs)`: Async execution logic
- `verify(result)`: Post-execution output validation hook

### 2. Permission Levels (`PermissionLevel`)
- `READ`: Safe, read-only local operations (automatically permitted)
- `WRITE`: Mutates local files or states (requires approval)
- `EXTERNAL`: Connects to third-party network services or APIs (requires approval)
- `DESTRUCTIVE`: Deletes files or terminates resources (denied by default)

### 3. Built-in Safe Starter Tools
1. **`calculator`** (`PermissionLevel.READ`):
   - Safely parses mathematical expressions using an **AST whitelist** (`ast.BinOp`, `ast.Constant`, `ast.UnaryOp`).
   - Supports: `+`, `-`, `*`, `/`, `%`, `**`, parentheses, and negative numbers.
   - Strictly blocks: `eval()`, `exec()`, `ast.Call`, `ast.Attribute`, `ast.Name`, imports, and variable lookups.
   - Rejects division by zero and guards against exponential denial of service.
2. **`datetime`** (`PermissionLevel.READ`):
   - Returns timezone-aware date and time information.
   - Supports valid IANA timezones (e.g. `UTC`, `Asia/Kolkata`, `America/New_York`).
   - Returns structured `date`, `time`, `timezone`, `iso`, and `day_of_week`.
3. **`system_info`** (`PermissionLevel.READ`):
   - Returns high-level operating system, architecture, and Python version details.
   - Strictly forbids and masks any access to environment variables, credentials, usernames, or filesystem paths.

### 4. Bounded Iterations & Guardrails
- Sequential tool calls are supported up to `MAX_TOOL_ITERATIONS = 5`.
- If a model becomes trapped in a recursive tool loop, Kairo safely stops and returns a clear message.
- Raw Python stack traces are never exposed to the model or user.

### 5. Future Tools Intentionally Not Implemented Yet
To preserve absolute safety in Phase 4, the following are **intentionally not implemented**:
- Arbitrary shell / bash execution
- Dynamic Python code execution
- Browser automation
- Filesystem write/delete
- Outbound emails or communications
- Autonomous background loops

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

### 2. General Chat
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello Kairo"}'
```

**Response:**
```json
{
  "message": "Hello! How can I help?",
  "model": "meta-llama/llama-3.3-70b-instruct",
  "tools_used": null
}
```

### 3. Tool Execution Response (Internal Calculator Tool)
When the model invokes a tool to resolve a user request:

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is 15 * 4?"}'
```

**Response (Includes safe tool metadata):**
```json
{
  "message": "15 * 4 is 60.",
  "model": "google/gemini-2.0-flash-001",
  "tools_used": [
    {
      "tool": "calculator",
      "status": "success",
      "verification_status": "verified"
    }
  ]
}
```

### 4. Streaming Response (`POST /api/v1/chat/stream`)
```bash
curl -N -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the time in UTC?"}'
```

---

## Running Tests

The test suite contains **62 unit and integration tests** verifying tool execution, AST security, permissions, provider continuation, and endpoint behaviors with zero external network calls:

```bash
cd backend
pytest -v
```

---

## Incremental Roadmap

- [x] **Phase 1: Bootstrap** — Minimal repository layout, clean architecture, config, health endpoint, tests.
- [x] **Phase 2: AI Brain (OpenRouter Integration)** — Provider protocol, OpenRouter sync/stream completions, KairoAgent persona.
- [x] **Phase 3: Model Router** — Capability taxonomy, ModelDefinition, ModelRegistry, ModelRouter priority matching & fallback.
- [x] **Phase 4: Tool System & Safe Starters** — BaseTool contract, ToolRegistry, ToolExecutor, permissions (READ/WRITE/EXTERNAL/DESTRUCTIVE), calculator (safe AST), datetime, system_info, tool iteration loop.
- [ ] **Phase 5: Memory System** — Short-term context window and persistent vector memory.
- [ ] **Phase 6: Voice Pipeline** — STT & TTS streaming audio pipeline.
- [ ] **Phase 7: Frontend Interface** — Next.js + TypeScript dashboard with audio waveform visualizer.
