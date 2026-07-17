# Phase 10.1 — Deployment Infrastructure Design

> **Version:** 1.0 | **Date:** 2026-07-17 | **Type:** Design-Only  
> **Constraint:** Zero Veritas-Core modifications | Architecture documentation  
> **Current:** A3 1130 tests | Veritas-Core 558 tests | render.yaml (Streamlit-only)

---

## 1. Production Deployment Architecture

### 1.1 Target Architecture

```
                          Internet
                             │
                             ▼
                  ┌──────────────────┐
                  │   Nginx / Caddy   │  ← Reverse proxy (optional)
                  │   Port 80/443     │
                  └────────┬─────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ Streamlit│ │ FastAPI  │ │ FastAPI  │
        │ :8501    │ │ :8000 (1)│ │ :8000 (2)│  ← Multiple workers
        │ (Web UI) │ │ (API)    │ │ (API)    │
        └────┬─────┘ └────┬─────┘ └────┬─────┘
             │            │            │
             └────────────┼────────────┘
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ SQLite   │ │ Knowledge│ │ Generated│
        │ (a3.db)  │ │ Base     │ │ Content  │
        │          │ │ (JSON)   │ │ (storage)│
        └──────────┘ └──────────┘ └──────────┘
                          │
                          ▼
              ┌──────────────────────┐
              │   Veritas-Core 7.0   │  ← Read-only framework
              │   (pip dependency)   │
              └──────────────────────┘

External APIs (optional):
  DeepSeek (LLM) · FAL.ai (Images) · Edge TTS (Audio)
```

### 1.2 Component Responsibilities

| Component | Port | Role | Depends On |
|:----------|:----:|:-----|:-----------|
| Streamlit | 8501 | Web UI — student-facing interface | FastAPI (API calls) |
| FastAPI | 8000 | REST API — all business logic | Veritas-Core, SQLite |
| SQLite | — | Application data (users, resources, records) | — |
| Knowledge Base | — | Course JSON files (read-only at runtime) | — |
| Veritas-Core | — | Agent Runtime Framework (pip dependency) | — |

### 1.3 Veritas-Core Dependency Boundary

```
┌─────────────────────────────────────────────────────────────┐
│  A3-Multi-Agent-System                                      │
│                                                             │
│  app.py          → Streamlit launcher                       │
│  src/api/        → FastAPI server + routes                  │
│  src/agents/     → 9 agents (Profile, Planner, Tutor, ...)  │
│  src/multimodal/ → Gateway + Providers                      │
│  src/data/       → SQLite + KB manager                      │
│  src/auth/       → User authentication                      │
│  web/            → Streamlit UI components                  │
│                                                             │
│  requirements.txt:                                          │
│    veritas-core>=7.0.0    ← FROM PyPI or git                │
│    streamlit>=1.28.0                                        │
│    fastapi>=0.115.0                                         │
│    uvicorn>=0.30.0                                          │
└──────────────────────────┬──────────────────────────────────┘
                           │ pip install
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Veritas-Core 7.0.0 (Read-Only)                             │
│                                                             │
│  veritas/runtime/     → RuntimeEngine, hooks, events        │
│  veritas/sdk/         → RuntimeClient, TaskRequest          │
│  veritas/memory/      → MemoryManager, StudentMemory        │
│  veritas/security/    → PermissionMatrix, AuditLogger       │
│  veritas/llm/         → LLMProvider, create_provider        │
│  veritas/plugins/     → Plugin system                       │
│  veritas/recovery/    → RecoveryManager                     │
│  veritas/lifecycle/   → AgentLifecycle                      │
│  veritas/distributed/ → NodeRegistry, DistributedEventBus   │
│  veritas/benchmark/   → BenchmarkRunner                     │
│  veritas/cli/         → veritas CLI                         │
└─────────────────────────────────────────────────────────────┘
```

**Key rule:** Veritas-Core is a pip dependency. It is NEVER modified by A3 deployment. All deployment concerns (env vars, DB, API keys) are handled by A3 and passed to Veritas-Core at runtime via constructor injection.

---

## 2. Docker Architecture

### 2.1 Dockerfile

```dockerfile
# A3-Multi-Agent-System Dockerfile
# Multi-stage build for production deployment

# ── Stage 1: Build ──────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# System deps for python-pptx (optional)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libc-dev && \
    rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ── Stage 2: Runtime ────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 a3 && chown -R a3:a3 /app
USER a3

# Expose ports
EXPOSE 8000 8501

# Default command: run both Streamlit + FastAPI via start script
COPY scripts/start.sh /app/scripts/start.sh
RUN chmod +x /app/scripts/start.sh
CMD ["/app/scripts/start.sh"]
```

### 2.2 docker-compose.yml

```yaml
# docker-compose.yml — A3 production stack
version: "3.8"

services:
  # ── FastAPI Backend ──────────────────────────────────
  api:
    build: .
    image: a3-api:latest
    container_name: a3-api
    ports:
      - "8000:8000"
    environment:
      - PYTHONUNBUFFERED=1
      - A3_ENV=production
      # Provider config
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY:-}
      - FAL_KEY=${FAL_KEY:-}
      - LLM_PROVIDER=${LLM_PROVIDER:-mock}
      - A3_PROVIDER=${A3_PROVIDER:-mock}
    volumes:
      - a3_data:/app/storage
      - a3_kb:/app/knowledge_base:ro
    command: uvicorn src.api.server:app --host 0.0.0.0 --port 8000 --workers 2
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 3

  # ── Streamlit Frontend ───────────────────────────────
  web:
    build: .
    image: a3-web:latest
    container_name: a3-web
    ports:
      - "8501:8501"
    environment:
      - PYTHONUNBUFFERED=1
      - A3_API_URL=http://api:8000
    depends_on:
      api:
        condition: service_healthy
    command: streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
    restart: unless-stopped

  # ── Optional: PostgreSQL (for production scale) ─────
  postgres:
    image: postgres:16-alpine
    container_name: a3-postgres
    environment:
      - POSTGRES_DB=a3
      - POSTGRES_USER=a3
      - POSTGRES_PASSWORD=${DB_PASSWORD:-a3_secret}
    volumes:
      - pg_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    profiles:
      - production  # Only start with: docker compose --profile production up

volumes:
  a3_data:     # SQLite DB + generated resources + student data
  a3_kb:       # Knowledge base (course JSON files)
  pg_data:     # PostgreSQL data (production profile only)
```

### 2.3 Volume Strategy

| Volume | Mount Point | Content | Persistence |
|:-------|:------------|:--------|:------------|
| `a3_data` | `/app/storage` | `a3.db` (SQLite), generated content, student profiles | ✅ Named volume |
| `a3_kb` | `/app/knowledge_base` | Course JSON files (read-only) | ✅ Named volume |
| `pg_data` | `/var/lib/postgresql/data` | PostgreSQL data (production only) | ✅ Named volume |

**Design decision:** SQLite for default deployment (zero-config, single-file). PostgreSQL as optional `--profile production` for multi-user scale.

### 2.4 Start Script

```bash
#!/bin/bash
# scripts/start.sh — Start both Streamlit + FastAPI

# Start FastAPI in background
uvicorn src.api.server:app --host 0.0.0.0 --port 8000 --workers 2 &

# Start Streamlit in foreground (keeps container alive)
streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
```

---

## 3. Deployment Targets

### 3.1 Render (Cloud — Free Tier)

```
┌──────────────────────────────────────────────────────────┐
│  Render Blueprint (render.yaml)                          │
│                                                          │
│  Service: a3-multi-agent-system                          │
│  Type: Web Service                                       │
│  Runtime: Python 3.12                                    │
│  Plan: Free ($0/mo)                                      │
│                                                          │
│  Build:                                                  │
│    pip install git+https://github.com/Leisure-Auf1/      │
│      Veritas-Core.git@main                               │
│    pip install -r requirements.txt                       │
│                                                          │
│  Start:                                                  │
│    streamlit run app.py --server.port $PORT               │
│      --server.address 0.0.0.0 --server.headless true     │
│                                                          │
│  Limitations (Free):                                     │
│    • Sleeps after 15 min idle (cold start ~30s)          │
│    • Ephemeral filesystem                                │
│    • 512 MB RAM, shared CPU                              │
│    • No persistent disk                                  │
│                                                          │
│  Mitigation:                                             │
│    • Use mock provider (no API key needed)               │
│    • UptimeRobot ping every 5 min to prevent sleep       │
│    • Store critical data as JSON exports                 │
└──────────────────────────────────────────────────────────┘
```

**Updated render.yaml:**

```yaml
services:
  - type: web
    name: a3-multi-agent-system
    runtime: python
    plan: free
    buildCommand: |
      pip install git+https://github.com/Leisure-Auf1/Veritas-Core.git@main
      pip install -r requirements.txt
    startCommand: streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
    healthCheckPath: /
    envVars:
      - key: PYTHON_VERSION
        value: 3.12.7
      - key: LLM_PROVIDER
        value: mock
      - key: DEEPSEEK_API_KEY
        sync: false
      - key: FAL_KEY
        sync: false
      - key: STREAMLIT_BROWSER_GATHER_USAGE_STATS
        value: "false"
```

### 3.2 HuggingFace Spaces

```
┌──────────────────────────────────────────────────────────┐
│  HuggingFace Spaces                                      │
│                                                          │
│  SDK: Streamlit                                          │
│  Hardware: CPU Basic (free)                              │
│                                                          │
│  Auto-detection:                                         │
│    • Spaces detects app.py as Streamlit entry point      │
│    • requirements.txt auto-installed                     │
│                                                          │
│  Issue: veritas-core dependency                          │
│    Solution: Add to requirements.txt:                    │
│      veritas-core @ git+https://github.com/              │
│        Leisure-Auf1/Veritas-Core.git@main                │
│                                                          │
│  Files needed:                                           │
│    • app.py              (Streamlit entry)               │
│    • requirements.txt    (with veritas-core git dep)     │
│    • packages.txt        (system deps — empty for now)   │
│    • README.md           (Space description)             │
│                                                          │
│  Limitations:                                            │
│    • Sleeps after inactivity                             │
│    • No FastAPI (Streamlit-only)                         │
│    • 16 GB disk, 2 CPU cores                             │
└──────────────────────────────────────────────────────────┘
```

### 3.3 Local Docker

```bash
# Build and run
docker compose up -d

# Access
# Streamlit: http://localhost:8501
# FastAPI:   http://localhost:8000/docs

# With PostgreSQL
docker compose --profile production up -d

# View logs
docker compose logs -f api
docker compose logs -f web

# Stop
docker compose down
```

### 3.4 Deployment Comparison

| Feature | Render Free | HF Spaces | Local Docker |
|:--------|:-----------:|:---------:|:------------:|
| Cost | $0/mo | $0/mo | $0 (own hardware) |
| FastAPI | ❌ Streamlit only | ❌ Streamlit only | ✅ Both |
| Persistent DB | ❌ Ephemeral | ❌ Ephemeral | ✅ Named volumes |
| Sleep/Idle | 15 min | ~30 min | ❌ Always on |
| API keys | ✅ Env vars | ✅ Secrets | ✅ .env file |
| PostgreSQL | ❌ | ❌ | ✅ Optional |
| Best for | Public demo | Community showcase | Self-hosted prod |

---

## 4. Environment Configuration

### 4.1 Environment Variables

```bash
# .env — A3 Configuration
# Copy to .env and fill in values

# ── Provider Selection ──────────────────────────────────
# LLM provider: "mock" | "deepseek" | "openai"
LLM_PROVIDER=mock

# DeepSeek API (for LLM enrichment)
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1

# FAL.ai API (for image generation)
FAL_KEY=

# Edge TTS (free — no key needed)
# TTS_PROVIDER=edge

# ── Application ─────────────────────────────────────────
A3_ENV=development          # development | production
A3_SECRET_KEY=change-me-in-production

# ── Database ────────────────────────────────────────────
# SQLite (default — zero config)
DATABASE_URL=sqlite:///storage/a3.db

# PostgreSQL (production — uncomment to use)
# DATABASE_URL=postgresql://a3:a3_secret@localhost:5432/a3

# ── Server ──────────────────────────────────────────────
API_HOST=0.0.0.0
API_PORT=8000
STREAMLIT_PORT=8501

# ── Cost Control ────────────────────────────────────────
# User tier for cost controller: "free" | "pro"
DEFAULT_USER_TIER=free
```

### 4.2 Config Loading

```python
# src/config.py — Centralized config loader (design reference)

import os
from dataclasses import dataclass

@dataclass
class A3Config:
    env: str = "development"
    llm_provider: str = "mock"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    fal_key: str = ""
    database_url: str = "sqlite:///storage/a3.db"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    streamlit_port: int = 8501
    default_user_tier: str = "free"
    secret_key: str = "change-me"

    @classmethod
    def from_env(cls) -> "A3Config":
        return cls(
            env=os.getenv("A3_ENV", "development"),
            llm_provider=os.getenv("LLM_PROVIDER", "mock"),
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", ""),
            deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
            fal_key=os.getenv("FAL_KEY", ""),
            database_url=os.getenv("DATABASE_URL", "sqlite:///storage/a3.db"),
            api_host=os.getenv("API_HOST", "0.0.0.0"),
            api_port=int(os.getenv("API_PORT", "8000")),
            streamlit_port=int(os.getenv("STREAMLIT_PORT", "8501")),
            default_user_tier=os.getenv("DEFAULT_USER_TIER", "free"),
            secret_key=os.getenv("A3_SECRET_KEY", "change-me"),
        )
```

### 4.3 Provider Selection Strategy

```
Provider Resolution Order:

1. Environment variable: LLM_PROVIDER=deepseek
   → Use DeepSeek API

2. Environment variable: LLM_PROVIDER=mock
   → Use MockLLMProvider (zero API calls)

3. No LLM_PROVIDER set:
   → Check DEEPSEEK_API_KEY → if set, use DeepSeek
   → Fallback: MockLLMProvider

Image Generation:
   FAL_KEY set → FALImageProvider
   FAL_KEY empty → SVGPlaceholderProvider (always available)

Audio:
   Edge TTS (free, no key) → always available
```

---

## 5. CI/CD Pipeline

### 5.1 GitHub Actions Workflow

```yaml
# .github/workflows/ci.yml
name: A3 CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.12"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install Veritas-Core
        run: |
          git clone https://github.com/Leisure-Auf1/Veritas-Core.git /tmp/veritas-core
          pip install -e /tmp/veritas-core

      - name: Install A3 dependencies
        run: pip install -r requirements.txt pytest pytest-cov

      - name: Run tests
        run: python -m pytest tests/ -v --tb=short --cov=src --cov-report=term-missing

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
          flags: unittests

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v4

      - name: Build Docker image
        run: docker build -t a3-multi-agent-system:latest .

      - name: Verify Docker image
        run: |
          docker run --rm a3-multi-agent-system:latest python -c "from src.api.server import app; print('OK')"

  deploy-render:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    # Render auto-deploys on push to main — no explicit deploy step needed
    steps:
      - name: Trigger Render deploy
        run: |
          curl -X POST "https://api.render.com/deploy/srv-${RENDER_SERVICE_ID}?key=${RENDER_API_KEY}"
```

### 5.2 CI Pipeline Stages

```
Push/PR to main
      │
      ▼
┌─────────────┐
│   Test      │  Python 3.10 + 3.12 matrix
│             │  Install Veritas-Core from git
│             │  pytest + coverage
│   ~6 min    │  Gate: 1130+ tests must pass
└──────┬──────┘
       │ ✓
       ▼
┌─────────────┐
│   Build     │  Docker build
│             │  Image verification
│   ~3 min    │  Gate: image builds + imports work
└──────┬──────┘
       │ ✓
       ▼
┌─────────────┐
│   Deploy    │  Render auto-deploy (on push to main)
│             │  Optional: manual approval gate
│   ~5 min    │
└─────────────┘
```

### 5.3 Test Gate Requirements

| Check | Requirement | Failure Action |
|:------|:------------|:---------------|
| pytest | 1130+ passed | Block merge |
| Coverage | ≥ 70% | Warning, don't block |
| Docker build | Success | Block deploy |
| Import check | All modules importable | Block deploy |
| Veritas-Core boundary | Zero VC file modifications | Block merge |

---

## 6. File Map (Post-Phase 10.1)

```
A3-Multi-Agent-System/
├── Dockerfile                ← NEW: multi-stage build
├── docker-compose.yml        ← NEW: API + Web + optional PostgreSQL
├── .dockerignore             ← NEW: exclude venv, .git, __pycache__
├── render.yaml               ← UPDATE: add Veritas-Core install
├── .github/
│   └── workflows/
│       └── ci.yml            ← NEW: test + build + deploy
├── scripts/
│   └── start.sh              ← NEW: dual-service launcher
├── .env.example              ← UPDATE: full config template
├── packages.txt              ← NEW: HF Spaces system deps
├── requirements.txt          ← UPDATE: veritas-core git dependency
├── docs/
│   └── phase10.1-deployment-design.md  ← THIS FILE
└── ... (existing files unchanged)
```

---

## 7. Implementation Checklist

### Phase 10.1a — Docker (2 hours)
- [ ] Create `Dockerfile` (multi-stage)
- [ ] Create `docker-compose.yml` (API + Web + PostgreSQL profile)
- [ ] Create `.dockerignore`
- [ ] Create `scripts/start.sh`
- [ ] Verify: `docker compose up` → Streamlit + FastAPI accessible

### Phase 10.1b — Render + HF Spaces (1 hour)
- [ ] Update `render.yaml` with Veritas-Core install
- [ ] Update `requirements.txt` with git dependency
- [ ] Create `packages.txt` (HF Spaces)
- [ ] Verify: Render deploy succeeds

### Phase 10.1c — CI/CD (1 hour)
- [ ] Create `.github/workflows/ci.yml`
- [ ] Verify: PR triggers test matrix
- [ ] Verify: main push triggers build

### Phase 10.1d — Config (30 min)
- [ ] Update `.env.example` with full template
- [ ] Verify: `mock` provider mode works in Docker

---

## 8. Constraints Compliance

| Constraint | Compliance |
|:-----------|:-----------|
| Zero Veritas-Core modifications | ✅ VC is pip dependency, never modified |
| No code changes (this phase) | ✅ Design document only |
| Follow existing architecture | ✅ Streamlit + FastAPI pattern preserved |
| 1130 tests must pass | ✅ Tests run in CI, gate merge |
| Veritas-Core boundary | ✅ Explicitly defined in §1.3 |
