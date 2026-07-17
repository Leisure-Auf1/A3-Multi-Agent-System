# Phase 9 — A3 Product Application Layer: Design Document

> **Version:** 1.0 | **Phase:** 9.0 Design | **Date:** 2026-07-17  
> **Constraint:** Zero Veritas-Core modifications | Zero Runtime changes | Zero repo splits  
> **Baseline:** 1015 tests passing, Veritas-Core 7.0.0 dependency

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                   A3 Application Layer                    │
│                                                          │
│  ┌──────────┐  ┌───────────┐  ┌───────────────────────┐ │
│  │ Web UI   │  │ REST API  │  │  Agent Workflow        │ │
│  │ (Stream- │  │ (FastAPI) │  │  (A3Workflow + Agents) │ │
│  │  lit)    │  │           │  │                        │ │
│  └────┬─────┘  └─────┬─────┘  └───────────┬───────────┘ │
│       │              │                     │             │
│       └──────────────┼─────────────────────┘             │
│                      │                                   │
│  ┌───────────────────┼────────────────────────────────┐  │
│  │            Data Layer (A3-specific)                 │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────┐    │  │
│  │  │ User DB  │ │ Course   │ │ Learning Records │    │  │
│  │  │ (auth)   │ │ KB       │ │ (history)        │    │  │
│  │  └──────────┘ └──────────┘ └──────────────────┘    │  │
│  └───────────────────┬────────────────────────────────┘  │
│                      │                                   │
└──────────────────────┼───────────────────────────────────┘
                       │  pip install veritas-core
                       ▼
┌──────────────────────────────────────────────────────────┐
│                 Veritas-Core (unchanged)                  │
│  RuntimeEngine | SDK | Plugins | Security | Memory       │
│  Recovery | Lifecycle | Distributed | Benchmark | CLI    │
└──────────────────────────────────────────────────────────┘
```

**Key Boundary:** All new code lives in A3's `src/`. It calls Veritas-Core via `veritas.*` imports ONLY. Veritas-Core is read-only for this phase.

---

## 2. Existing Code vs Phase 9 Requirements

### 2.1 Agents — Gap Analysis

| Agent | Current Status | Phase 9 Need | Action |
|:------|:---------------|:-------------|:-------|
| **ProfileAgent** | ✅ EXISTS (rule+LLM dual mode) | Works, needs user persistence | Add profile save/load to User DB |
| **PlannerAgent** | ✅ EXISTS (LearningPlan generation) | Works, needs course KB integration | Connect to enriched KB |
| **ReflectionAgent** | ✅ EXISTS (post-lesson reflection) | Rename/refocus to EvaluationAgent | Rename + add knowledge assessment |
| **ResourceAgent** | ✅ EXISTS (resource recommendations) | Works, needs media cards in UI | Enrich resource data with media URLs |
| **ResourceGenerationAgent** | ✅ EXISTS (document/video/exercise gen) | Works | Keep as-is, expose via API |
| **ResourceRecommendationAgent** | ✅ EXISTS (personalized recs) | Works | Keep as-is |
| **ConversationProfileAgent** | ✅ EXISTS (conversational profiling) | Works | Keep as-is |
| **TutorAgent** | ❌ MISSING | Conversational tutor — explain concepts, answer questions | **NEW** — build |
| **EvaluationAgent** | ❌ MISSING | Knowledge assessment, quiz generation, scoring | **NEW** — build from ReflectionAgent |

### 2.2 User System — Gap Analysis

| Feature | Current | Phase 9 Need | Action |
|:--------|:-------:|:-------------|:-------|
| Login / Auth | ❌ NONE | Email/password or guest mode | **NEW** — `src/auth/` |
| Student profile | ⚠️ In-memory (Veritas MemoryManager) | Persistent per-user profile | **NEW** — `src/data/student_store.py` |
| Learning history | ❌ NONE | Track all sessions, plans, results | **NEW** — `src/data/learning_log.py` |
| Session management | ❌ NONE | Resume previous sessions | **NEW** — session persistence |

### 2.3 Web UI — Gap Analysis

| Feature | Current | Phase 9 Need | Action |
|:--------|:-------:|:-------------|:-------|
| Landing page | ⚠️ 3-tab dashboard | Full chat interface + sidebar | Redesign `web/app_v4.py` |
| Streaming chat | ❌ NONE | ChatGPT-style token streaming | **NEW** — SSE streaming |
| Markdown rendering | ⚠️ Basic Streamlit | Syntax highlighting, tables, math | **NEW** — custom renderer |
| Multimodal cards | ❌ NONE | Video/image/exercise cards | **NEW** — `web/components/` |
| Chat history | ❌ NONE | Persistent chat threads | **NEW** — thread storage |
| Responsive design | ⚠️ Streamlit default | Mobile-friendly layout | Improve CSS |

### 2.4 Data Layer — Gap Analysis

| Component | Current | Phase 9 Need | Action |
|:----------|:-------:|:-------------|:-------|
| User DB | ❌ NONE | User accounts, auth tokens | **NEW** — SQLite via `src/data/user_db.py` |
| Course KB | ⚠️ 2 JSON files | Enriched course content, search | Expand `src/data/kb_manager.py` |
| Learning records | ❌ NONE | Lesson history, quiz results, progress | **NEW** — `src/data/learning_records.py` |
| File storage | ❌ NONE | Generated content, uploads | **NEW** — `storage/content/` |

### 2.5 Deployment — Gap Analysis

| Target | Current | Phase 9 Need | Action |
|:--------|:-------:|:-------------|:-------|
| Render (Linux) | ✅ render.yaml | Works (fix dependency resolution) | Update render.yaml |
| Windows | ❌ NONE | Install guide + startup script | **NEW** — `docs/deployment/windows.md` |
| Docker | ❌ NONE | Containerized deployment | **NEW** — `Dockerfile` |

---

## 3. Module Design

### 3.1 User Auth System (`src/auth/`)

```
src/auth/
├── __init__.py
├── models.py          # User, LoginRequest, Token
├── auth_manager.py    # register, login, verify, logout
├── session.py         # SessionStore (cookie/token based)
└── middleware.py      # FastAPI dependency: get_current_user
```

**Design decisions:**
- **SQLite** as user store (no external DB required)
- **Password hashing** via `hashlib` (no bcrypt dependency)
- **Simple token** (UUID-based, not JWT — keeps deps minimal)
- **Guest mode**: Allow anonymous use with auto-generated guest ID
- **Zero external auth providers** (no Google/OAuth in Phase 9)

**API endpoints:**
```
POST /api/v1/auth/register   → {token, user_id}
POST /api/v1/auth/login      → {token, user_id}
POST /api/v1/auth/logout     → {success}
GET  /api/v1/auth/me         → {user}  (requires auth)
```

### 3.2 Data Layer (`src/data/`)

```
src/data/
├── __init__.py
├── user_db.py           # SQLite CRUD for users
├── student_store.py     # Student profile persistence (uses Veritas memory types)
├── kb_manager.py        # Course KB loader + search (extends existing loader)
├── learning_records.py  # CRUD for learning history
└── thread_store.py      # Chat thread persistence
```

**Database:** SQLite (single file, no server)
- `users` table: id, email, password_hash, display_name, created_at
- `learning_records` table: id, user_id, course_id, agent, action, result, timestamp
- `chat_threads` table: id, user_id, title, created_at
- `chat_messages` table: id, thread_id, role, content, timestamp

**Design decisions:**
- **No ORM** — raw SQLite3 via stdlib (zero new deps)
- **Migration-safe** — schema version stored in DB
- **Student profiles** reuse Veritas `StudentMemory` dataclass as serialization contract

### 3.3 New Agents: TutorAgent (`src/agents/tutor_agent.py`)

```
TutorAgent:
  Purpose: Conversational tutor — explain concepts, answer student questions
  Input:   student_profile, learning_context, question
  Output:  TutorResponse (explanation, examples, follow_up_questions)
  
  Features:
  - Concept explanation with difficulty-appropriate language
  - Code examples when relevant (Python, math, etc.)
  - Follow-up question generation (Socratic method)
  - Learning style adaptation (visual/auditory/reading/kinesthetic)
  - Confusion detection (ask clarifying questions)
```

**Architecture:**
- Extends `BaseAgent` pattern (same as existing agents)
- Uses `LLMProvider` from Veritas-Core (via `from veritas.llm import LLMProvider`)
- Does NOT modify Runtime — registers as handler like existing agents

### 3.4 New Agents: EvaluationAgent (`src/agents/evaluation_agent.py`)

```
EvaluationAgent:
  Purpose: Knowledge assessment, quiz generation, scoring
  Input:   learning_plan, student_profile, knowledge_gaps
  Output:  EvaluationResult (quiz, answers, score, weak_areas)
  
  Features:
  - Auto-generate multiple-choice questions from learning content
  - Adaptive difficulty based on student mastery level
  - Detailed feedback per question (why correct/incorrect)
  - Weak area identification
  - Progress tracking (improvement over time)
```

**Built from:** Extends patterns from existing `ReflectionAgent` but adds:
- Quiz generation pipeline
- Scoring algorithm
- Progress aggregation

### 3.5 Streaming Chat UI (`web/app_v4.py`)

```
Design: ChatGPT-style interface
┌─────────────────────────────────────────────────────┐
│  A3 Learning Assistant                    [Login]   │
├──────────┬──────────────────────────────────────────┤
│ Threads  │  ┌──────────────────────────────────┐   │
│          │  │ Assistant: Hello! What would you  │   │
│ 📁 Math  │  │ like to learn today?              │   │
│ 📁 Python│  └──────────────────────────────────┘   │
│ 📁 AI    │  ┌──────────────────────────────────┐   │
│          │  │ User: Teach me about Python OOP  │   │
│          │  └──────────────────────────────────┘   │
│          │  ┌──────────────────────────────────┐   │
│          │  │ Assistant: [streaming...]          │   │
│          │  │ ## Object-Oriented Programming    │   │
│          │  │                                   │   │
│          │  │ Python OOP is... [tokens appear]  │   │
│          │  └──────────────────────────────────┘   │
│          │  ┌──────────────────────────────────┐   │
│          │  │ [📹 Tutorial Video]               │   │
│          │  │ [📝 Practice Exercise]            │   │
│          │  │ [📖 Reference Doc]                │   │
│          │  └──────────────────────────────────┘   │
│          │                                         │
│          │ [Type your message...]            [Send]│
└──────────┴──────────────────────────────────────────┘
```

**Components:**
- `web/app_v4.py` — Main Streamlit entry point
- `web/components/chat.py` — Chat message rendering (Markdown + streaming)
- `web/components/cards.py` — Media resource cards
- `web/components/sidebar.py` — Thread list + profile
- `web/streaming.py` — SSE streaming handler (FastAPI endpoint)

**Streaming Architecture:**
```
Browser ←SSE── FastAPI /api/v1/chat/stream ── A3Workflow.stream()
                                                  │
                                                  ▼
                                        TutorAgent.stream_response()
                                                  │
                                                  ▼
                                        LLMProvider.generate(stream=True)
```

### 3.6 Multimedia Resource Cards (`web/components/cards.py`)

```
Card Types:
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ 📹 Video     │  │ 📝 Exercise  │  │ 📖 Article   │  │ 💻 Code Lab  │
│              │  │              │  │              │  │              │
│ [Thumbnail]  │  │ Difficulty:  │  │ 10 min read  │  │ Python 3.10+ │
│ 12 min       │  │ ⭐⭐⭐        │  │              │  │ [Run ▶️]    │
│ [Watch]      │  │ [Start Quiz] │  │ [Read]       │  │              │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
```

---

## 4. Implementation Plan (4 Sprints)

### Sprint 9.1 — Data Foundation (2-3 hours)

```
src/auth/
  models.py, auth_manager.py, session.py, middleware.py
src/data/
  user_db.py, student_store.py, kb_manager.py, learning_records.py, thread_store.py
src/api/routes/
  auth.py (new route file)
```

**Deliverables:**
- [ ] User registration/login/logout API
- [ ] SQLite database with 4 tables
- [ ] Student profile persistence
- [ ] Learning record CRUD
- [ ] Tests: 20+ new tests

### Sprint 9.2 — New Agents (2-3 hours)

```
src/agents/
  tutor_agent.py
  evaluation_agent.py
```

**Deliverables:**
- [ ] TutorAgent with streaming support
- [ ] EvaluationAgent with quiz generation
- [ ] Register both in A3Workflow
- [ ] Tests: 30+ new tests

### Sprint 9.3 — Streaming Web UI (3-4 hours)

```
web/
  app_v4.py
  components/chat.py
  components/cards.py
  components/sidebar.py
  streaming.py
src/api/routes/
  chat.py (new: SSE streaming endpoint)
```

**Deliverables:**
- [ ] ChatGPT-style streaming chat UI
- [ ] Markdown rendering with syntax highlighting
- [ ] Multimedia resource cards
- [ ] Thread list + sidebar
- [ ] SSE streaming endpoint
- [ ] Tests: 15+ new tests

### Sprint 9.4 — Deployment & Polish (1-2 hours)

```
docs/deployment/
  windows.md
Dockerfile
render.yaml (updated)
```

**Deliverables:**
- [ ] Windows deployment guide (venv + pip + streamlit)
- [ ] Dockerfile for containerized deployment
- [ ] Updated render.yaml for A3 with Veritas-Core
- [ ] Final integration tests

---

## 5. Non-Breaking Constraints

### 5.1 Veritas-Core Boundary

```
✅ ALLOWED:
  from veritas import RuntimeClient, TaskRequest
  from veritas.runtime import RuntimeEngine, AgentState
  from veritas.llm import LLMProvider, create_provider
  from veritas.memory import MemoryManager, StudentMemory
  from veritas.sdk import RuntimeClient, TaskRequest, TaskResult

❌ FORBIDDEN:
  Modifying any Veritas-Core file
  Adding imports inside Veritas-Core that reference A3
  Changing RuntimeEngine behavior
  Adding new Runtime states/hooks
```

### 5.2 Test Guarantee

- All 1015 existing tests must continue passing
- New tests must not break existing tests
- Test isolation: each new module has its own test file

### 5.3 Backward Compatibility

- Old `web/app_v3.py` preserved as `web/app_legacy.py`
- Old `chat_demo.py` preserved
- Old API endpoints unchanged
- New API endpoints use `/api/v2/` prefix

---

## 6. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|:-----|:-----------|:-------|:-----------|
| Streaming breaks Streamlit state | MEDIUM | HIGH | Test with real LLM, add timeout handling |
| SQLite concurrent access (Streamlit sessions) | LOW | MEDIUM | WAL mode + connection pooling |
| TutorAgent hallucination | HIGH | MEDIUM | System prompt constraints + confidence scoring |
| UI complexity explosion | MEDIUM | MEDIUM | Component-based design, one component per file |
| Deployment on Windows fails | MEDIUM | HIGH | Test early on Windows VM |

---

## 7. File Map (Post-Phase 9)

```
A3-Multi-Agent-System/
├── src/
│   ├── agents/              (unchanged + 2 new)
│   │   ├── tutor_agent.py           ← NEW
│   │   └── evaluation_agent.py      ← NEW
│   ├── auth/                ← NEW (4 files)
│   │   ├── models.py
│   │   ├── auth_manager.py
│   │   ├── session.py
│   │   └── middleware.py
│   ├── data/                ← NEW (5 files)
│   │   ├── user_db.py
│   │   ├── student_store.py
│   │   ├── kb_manager.py
│   │   ├── learning_records.py
│   │   └── thread_store.py
│   ├── api/routes/
│   │   ├── auth.py          ← NEW
│   │   └── chat.py          ← NEW
│   ├── core/                (unchanged)
│   ├── workflow/            (minimal changes: add agent handlers)
│   └── ...
├── web/
│   ├── app_v4.py            ← NEW (main UI)
│   ├── app_legacy.py        ← RENAMED (old app_v3.py)
│   ├── components/
│   │   ├── chat.py          ← NEW
│   │   ├── cards.py         ← NEW
│   │   └── sidebar.py       ← NEW
│   └── streaming.py         ← NEW
├── docs/deployment/
│   └── windows.md           ← NEW
├── Dockerfile               ← NEW
└── storage/
    └── a3.db               ← NEW (SQLite)
```

---

## 8. Success Criteria

- [ ] 1100+ tests passing (1015 existing + 85+ new)
- [ ] User can register, login, start a learning session
- [ ] Chat UI shows streaming token-by-token responses
- [ ] TutorAgent explains concepts accurately
- [ ] EvaluationAgent generates and scores quizzes
- [ ] Multimedia cards display in chat
- [ ] Learning history is persistent across sessions
- [ ] Windows deployment guide is usable
- [ ] Zero Veritas-Core modifications
- [ ] Zero broken existing tests
