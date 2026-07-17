# A3 — AI Personalized Learning System

> **Product-Ready AI Learning Software** | 9 Agents | 1130 Tests | Phase 9.5  
> **Built on:** [Veritas-Core](https://github.com/Leisure-Auf1/Veritas-Core) (Agent Runtime Framework)

*"Students describe what they want to learn. A team of 9 AI agents does the rest — generating personalized resources, tutoring interactively, and evaluating progress."*

---

## What is A3?

A3 is a **complete AI-powered learning application** that combines 9 specialized agents to deliver personalized education. Unlike generic AI chatbots, A3 builds a 6-dimension student profile, generates tailored learning paths, creates 7 types of multimodal resources, tutors interactively, and evaluates understanding — all through a ChatGPT-style streaming interface.

---

## Architecture

```
                            Student
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                    A3 Application Layer                       │
│                                                              │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ Web UI   │  │  REST API v2 │  │   9 AI Agents         │   │
│  │ (Stream) │  │  (FastAPI)   │  │                       │   │
│  │          │  │              │  │ Profile → Planner →   │   │
│  │ ChatGPT  │  │ 20 endpoints │  │ Resource → Tutor →    │   │
│  │ style    │  │              │  │ Evaluation            │   │
│  └──────────┘  └──────────────┘  └───────────┬───────────┘   │
│                                              │               │
│  ┌───────────────────────────────────────────┼───────────┐   │
│  │          Multimodal Gateway (Phase 9.5)                │   │
│  │  📄 Document · 🧠 Mindmap · ✏️ Exercise · 💻 Code     │   │
│  │  📊 Slides · 🖼️ Illustration · 🎬 Video Script        │   │
│  └───────────────────────────┬───────────────────────────┘   │
│                              │                               │
│  ┌───────────────────────────┼───────────────────────────┐   │
│  │          Data Layer (SQLite)                           │   │
│  │  users · profiles · resources · learning_records      │   │
│  └───────────────────────────────────────────────────────┘   │
└──────────────────────────────┬───────────────────────────────┘
                               │ pip install veritas-core
                               ▼
┌──────────────────────────────────────────────────────────────┐
│              Veritas-Core 7.0.0 (Framework)                   │
│  RuntimeEngine · SDK · Plugins · Recovery · Lifecycle        │
│  Security · Memory · Distributed · Benchmark · CLI           │
└──────────────────────────────────────────────────────────────┘
```

---

## Key Features

### 🎯 Personalized Learning
- **6-dimension student profile**: knowledge base, cognitive style, error patterns, learning pace, interaction preference, frustration threshold
- **Adaptive difficulty**: content matches student level automatically
- **3 profile creation methods**: natural language, conversation, quick quiz

### 💬 AI Tutor (Phase 9.2)
- ChatGPT-style streaming chat via SSE
- 5 teaching styles (explanation, Socratic, example-driven, analogy, step-by-step)
- Learning style adaptation (visual, code, reading, auditory)
- Thread-based conversation history

### 📚 Multimodal Resources (Phase 9.5)
- **7 resource types**: documents, mind maps, exercises, code labs, PPT slides, illustrations, video scripts
- **3-level fallback**: API → rule-based → mock (works without API keys)
- **Cost control**: free/pro tiers with daily quotas

### ✏️ Smart Evaluation (Phase 9.2)
- Auto-generated quizzes with multiple-choice and open-ended questions
- Instant scoring with weak area detection
- Adaptive recommendations based on performance

### 🔄 Learning Loop
```
Profile → Plan → Learn → Evaluate → Reflect → (loop)
```

---

## Product API (v2)

```
POST /api/v2/auth/register           POST /api/v2/chat/stream
POST /api/v2/auth/login              POST /api/v2/chat/message
POST /api/v2/auth/guest              GET  /api/v2/chat/threads
GET  /api/v2/profile                 POST /api/v2/learning/plan
PUT  /api/v2/profile                 GET  /api/v2/learning/history
POST /api/v2/resources/generate      GET  /api/v2/learning/stats
POST /api/v2/evaluation/quiz/generate
POST /api/v2/evaluation/quiz/score
```

---

## Quick Start

```bash
git clone https://github.com/Leisure-Auf1/A3-Multi-Agent-System.git
cd A3-Multi-Agent-System

# Install Veritas-Core (framework dependency)
pip install git+https://github.com/Leisure-Auf1/Veritas-Core.git@main

# Install A3 dependencies
pip install -r requirements.txt

# Run API server
uvicorn src.api.server:app --reload --port 8000

# Run Streamlit UI (in another terminal)
streamlit run app.py --server.port 8501
```

### Run without API keys
A3 works fully offline with rule-based generators. No LLM API key required. Check `docs/phase9.5-multimodal-implementation.md` for details.

---

## Testing

```bash
make test       # 1130 tests
```

---

## Repository Relationship

| Repository | Role | Tests |
|:-----------|:-----|:-----:|
| [Veritas-Core](https://github.com/Leisure-Auf1/Veritas-Core) | Agent Runtime Framework (dependency) | 558 |
| **A3-Multi-Agent-System** | AI Learning Application | 1130 |
| [Terence-Agent](https://github.com/Leisure-Auf1/Terence-Agent) | Engineering Governance | — |

---

## Development Phases

| Phase | Milestone | Status |
|:------|:----------|:------:|
| 1–6 | Runtime Engine + SDK + Recovery + Lifecycle | ✅ |
| 7.0 | Repository Independence (Veritas-Core extraction) | ✅ |
| 8.0 | Productization Audit | ✅ |
| 9.1 | Data Layer (Auth + SQLite) | ✅ |
| 9.2 | TutorAgent + EvaluationAgent | ✅ |
| 9.3 | Multimodal Gateway Design | ✅ |
| 9.4 | Product API v2 + UI Design | ✅ |
| 9.5 | Multimodal Generation Implementation | ✅ |

---

## License

MIT
