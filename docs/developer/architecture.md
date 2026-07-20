# A3 Architecture

> **Version**: v7.1.1 | **Tests**: 2640

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Streamlit UI  │  │ FastAPI v2   │  │  Desktop .exe    │  │
│  │ web/app.py    │  │ src/api/     │  │  desktop/        │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         │                 │                    │            │
│         ▼                 ▼                    ▼            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              A3APIClient (web/utils/api.py)           │   │
│  │         REST client → all endpoints on port 8000       │   │
│  └──────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                     Security Layer                          │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │ Auth     │  │ Permission   │  │ Token Budget       │   │
│  │ JWT-like │  │ Role (free/  │  │ Daily limits per   │   │
│  │ token    │  │ pro/teacher/ │  │ user (SQLite)      │   │
│  │ SQLite   │  │ admin)       │  │                    │   │
│  └──────────┘  └──────────────┘  └────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                     Pipeline Layer                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         LearningPipelineService                       │   │
│  │  POST /api/v2/learning/run                            │   │
│  │          ↓                                            │   │
│  │         A3Workflow.run()                              │   │
│  └──────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                      Agent Layer                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐             │
│  │ Profile  │→ │ Planner  │→ │  ContentGen  │             │
│  │ Agent    │  │ Agent    │  │  Agent       │             │
│  └──────────┘  └──────────┘  └──────┬───────┘             │
│          ┌──────────┐  ┌──────────┐ │                      │
│          │ Resource │← │ Review   │←┘                      │
│          │ Agent    │  │ Gate     │                        │
│          └────┬─────┘  └────┬─────┘                        │
│               ▼             ▼                              │
│          ┌──────────┐  ┌──────────┐                        │
│          │Reflection│  │ Memory   │                        │
│          │ Agent    │  │ Manager  │                        │
│          └──────────┘  └──────────┘                        │
│                                                             │
│  All agents emit through EventBus → TraceCollector          │
├─────────────────────────────────────────────────────────────┤
│                      Data Layer                             │
│  ┌──────────────┐  ┌────────────────────────────────┐      │
│  │ SQLite       │  │ Filesystem Workspace             │      │
│  │ a3.db        │  │ ~/.a3-agent/workspace/{uid}/    │      │
│  │              │  │  ├── artifacts/                  │      │
│  │  users       │  │  ├── history/                    │      │
│  │  sessions    │  │  ├── usage/                      │      │
│  │  profiles    │  │  ├── memory/                     │      │
│  │  records     │  │  └── security/audit.jsonl        │      │
│  │  chat_*      │  │                                  │      │
│  └──────────────┘  └────────────────────────────────┘      │
│                                                             │
│  ┌──────────────────────────────────────┐                  │
│  │ Veritas Memory                       │                  │
│  │ storage/memory/students/{uid}.json   │                  │
│  └──────────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Components

### API Layer (`src/api/`)

- **Server**: FastAPI on port 8000
- **v2 Routes**: learning, chat, profile, resources, evaluation, settings, users
- **v1 Routes**: deprecated, auth-protected
- **Dependencies**: `require_auth`, `require_role`, `check_token_limit`

### Auth (`src/auth/`)

- Token-based (PBKDF2-SHA256 hashed passwords)
- Sessions stored in SQLite `sessions` table
- 24-hour token expiry
- Logout invalidates session immediately

### A3Workflow (`src/workflow/__init__.py`)

Central orchestrator — 1002 lines:

```python
workflow = A3Workflow(student_id="user_1")
result = workflow.run(user_goal="Learn Python async")
# result: profile, learning_plan, content, resources, evaluation,
#         reflection, trace, memory_saved
```

### Security (`src/security/`)

- `audit.py` — AuditLogger (JSONL per user)
- `middleware.py` — Security middleware

### Workspace (`src/workspace/manager.py`)

Per-user isolated filesystem storage:
- `save_artifact()` / `load_artifact()`
- `list_artifacts()` with category filter
- `get_workspace_info()` for metadata

---

## Data Flow

```
User Input (goal text)
    ↓
POST /api/v2/learning/run  (Bearer token)
    ↓
Auth → Permission → TokenBudget
    ↓
LearningPipelineService.run()
    ↓
A3Workflow.run()
    ├── ProfileAgent.extract()         → profile
    ├── PlannerAgent.plan()            → learning plan
    ├── ContentGeneratorAgent.generate() → materials
    ├── ResourceAgent.recommend()      → resources
    ├── ReviewGate.evaluate()          → quality score
    ├── ReflectionAgent.reflect()       → insights
    └── Memory.save()                  → persist all
    ↓
EventBus → TraceCollector
    ↓
WorkspaceManager.save_artifact() × 5 artifacts
    ↓
Response → UI renders tabs
```

---

## Directory Map

```
A3-Multi-Agent-System/
├── web/               # Streamlit UI (presentation layer)
│   ├── app.py         # Main entry (6-tab dashboard)
│   ├── theme.py       # Dark theme system
│   ├── components/    # Auth, Chat, Quiz, Material panels
│   ├── dashboard/     # Dashboard data providers
│   ├── v1/            # Legacy V1 pipeline components
│   └── utils/api.py   # A3APIClient (REST client)
├── src/               # Backend (business logic)
│   ├── api/           # FastAPI server + routes
│   ├── auth/          # Authentication + authorization
│   ├── workflow/      # A3Workflow orchestrator
│   ├── services/      # LearningPipelineService
│   ├── agents/        # 7 AI agents
│   ├── platform/      # TokenBudget, errors
│   ├── security/      # Audit logging
│   ├── user/          # User management + permissions
│   ├── workspace/     # Per-user filesystem workspace
│   ├── data/          # SQLite database layer
│   └── orchestration/ # OrchestratorRuntime (unused)
├── tests/             # 2640 tests
├── storage/           # SQLite db + memory store
├── docs/              # Documentation
├── desktop/           # PyInstaller launcher
├── Dockerfile
└── Makefile
```

---

## Related Docs

- [API Reference](api.md)
- [Security Report](../product/security-production-readiness.md)
- [Persistence Audit](../product/phase10-persistence-audit.md)
- [Runtime Map](../product/phase10-runtime-final-map.md)
