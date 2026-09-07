# Kairo — Autonomous Personal AI Assistant

Kairo is an autonomous personal AI assistant designed to execute complex tasks, manage workflows, and interface seamlessly across voice, text, tools, and autonomous agent loops.

> **Status: Phase 1 — Repository Bootstrap**  
> This repository is currently in **Phase 1**. The core application structure and backend skeleton are bootstrapped. Functionality including multi-agent orchestration, voice processing, persistent memory, tool execution, database models, and the web interface will be added incrementally in upcoming phases.

---

## Architecture Overview

Kairo is structured as a modular monorepo cleanly separating the backend agent core, future web frontend, deployment infrastructure, and containerization assets:

```text
kairo/
├── backend/                  # Python FastAPI agent service & core runtime
│   ├── app/
│   │   ├── agents/           # Autonomous agent routines & decision logic
│   │   ├── api/              # API endpoints, routers, and request handlers
│   │   ├── core/             # Application configuration, settings, security
│   │   ├── memory/           # Short-term and long-term memory management
│   │   ├── models/           # Pydantic data schemas & state definitions
│   │   ├── tools/            # Tool definitions, function calling, execution
│   │   └── main.py           # Application factory & server entry point
│   ├── tests/                # Pytest unit and integration test suite
│   ├── pyproject.toml        # Python project metadata & tool configurations
│   └── requirements.txt      # Minimal backend dependencies
├── frontend/                 # Reserved for Next.js + TypeScript web UI (Phase 2)
├── infra/                    # Cloud infrastructure & deployment scripts
├── docker/                   # Dockerfiles for containerized environments
│   └── Dockerfile.backend    # Backend container definition (Python 3.12+ slim)
├── .env.example              # Environment variables template (no hardcoded secrets)
├── .gitignore                # Git ignore rules for Python, Node, IDEs, envs
├── docker-compose.yml        # Docker Compose configuration for multi-service setup
└── README.md                 # Project documentation
```

### High-Level Planned Request Pipeline

```text
🎙️ User (Voice / Text)
       ↓
  Kairo API (FastAPI)
       ↓
  Model Router
       ↓
  OpenRouter Gateway
       ↓
  Tool Decision / Planning
       ↓
  Tool Execution Sandbox
       ↓
  Verification & Reflection
       ↓
  Streamed Response (Audio / Text)
```

---

## Getting Started

### Prerequisites

- **Python 3.12+** (Python 3.13 supported)
- **Git**
- *(Optional)* **Docker & Docker Compose**

---

### Local Backend Setup

#### 1. Navigate to the backend directory
```bash
cd backend
```

#### 2. Create and activate a virtual environment

**On Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**On macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### 3. Install dependencies
```bash
pip install -r requirements.txt
```

#### 4. Configure environment variables
From the project root:
```bash
cp .env.example .env
```
*(On Windows PowerShell: `Copy-Item .env.example .env`)*

#### 5. Run the FastAPI development server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The application will be available at:
- **Health Check Endpoint**: [http://localhost:8000/health](http://localhost:8000/health)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

### Running Tests

Execute the test suite using `pytest` from the `backend/` directory:

```bash
cd backend
pytest
```

---

### Running with Docker Compose

To start the backend containerized:

```bash
docker compose up --build
```

Verify the health check:
```bash
curl http://localhost:8000/health
```

---

## Roadmap

- [x] **Phase 1: Bootstrap** — Minimal repository layout, clean backend architecture, config, health check, testing.
- [ ] **Phase 2: OpenRouter & Model Router** — LLM gateway integration, model selection routing.
- [ ] **Phase 3: Tool Execution & Verification** — Function calling sandbox, validation loop.
- [ ] **Phase 4: Memory System** — Short-term context buffer and persistent vector memory.
- [ ] **Phase 5: Voice Pipeline** — STT & TTS streaming audio pipeline.
- [ ] **Phase 6: Frontend Interface** — Next.js + TypeScript dashboard with audio waveform visualization.
