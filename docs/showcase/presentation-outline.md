# A3-Agent v7.1.0 — Presentation Outline

9-slide deck for competition defense, internship interviews, or project showcase.

---

## Slide 1: Problem

**Title**: The Problem with AI Learning Tools

**Content**:
- Generic AI chatbots lack personalization — same response for every student
- No student modeling — can't adapt to individual learning style
- Single-agent limitation — one LLM call can't plan, teach, and evaluate simultaneously
- Deployment friction — most AI tools require API keys, cloud setup, or Python knowledge

**Visual**: Comparison table — "Generic Chatbot" vs "A3 Multi-Agent System"

| Capability | Generic Chatbot | A3 |
|:-----------|:---------------:|:--:|
| Personalization | ❌ | ✅ 6-dim profile |
| Learning Plan | ❌ Generic | ✅ Structured |
| Resources | ❌ Text only | ✅ 7 types |
| Evaluation | ❌ None | ✅ ReviewGate |
| Offline | ❌ | ✅ Mock mode |
| Desktop App | ❌ | ✅ .exe download |

---

## Slide 2: Solution

**Title**: A3 — Personalized Multi-Agent Learning Assistant

**Content**:
- **What**: A complete AI-powered learning application with 12 collaborating agents
- **How**: Multi-agent pipeline → 6-dimension profiling → explainable workflow → cross-platform distribution
- **Key Result**: 1154 tests, 0 failures, deployable as Windows .exe

**One-line pitch**:
> "Students describe what they want to learn. A team of AI agents does the rest."

---

## Slide 3: System Architecture

**Title**: 5-Layer Architecture

**Content**: Architecture diagram

```
┌──────────────────────────────────────────────────────────────┐
│  🖥️  Presentation    Streamlit 7-tab UI · FastAPI · Desktop .exe  │
├──────────────────────────────────────────────────────────────┤
│  🤖  Agent Pipeline  Profile → Planner → Resource → Tutor → Eval │
│                       EventBus · TraceCollector · 12 Agents      │
├──────────────────────────────────────────────────────────────┤
│  🧠  Intelligence    LLM Factory · TF-IDF RAG · Memory · Multimodal│
│                       DeepSeek / OpenAI / Spark / Mock providers   │
├──────────────────────────────────────────────────────────────┤
│  🔐  Trust & Security  ReviewGate 3-tier · Keyring (OS-level) · Auth│
├──────────────────────────────────────────────────────────────┤
│  💾  Data            SQLite (WAL) · Schema Migration · WAL mode │
└──────────────────────────────────────────────────────────────┘
```

**Key Points**:
- Each layer is independently testable
- LLM providers are pluggable (factory pattern)
- Security uses OS credential store (no plaintext keys)

---

## Slide 4: Multi-Agent Design

**Title**: 12 Agents, 1 Pipeline

**Content**: Core agent collaboration diagram

```
Student Input
     │
     ▼
ProfileAgent ──→ 6-dim cognitive profile
     │
     ▼
PlannerAgent ──→ structured learning path (with TF-IDF RAG)
     │
     ▼
ResourceAgent ──→ 7 resource types (doc, exercises, mindmap, code, slides, illustration, video)
     │
     ├──→ TutorAgent ──→ interactive Q&A (SSE streaming)
     │
     └──→ EvaluationAgent ──→ quiz generation + scoring
                │
                ▼
         ReflectionAgent ──→ improvement suggestions
```

**Agent Details**:
| Agent | Role | LLM? |
|:------|:-----|:----:|
| ProfileAgent | Extract 6-dim cognitive profile | ✅ |
| PlannerAgent | Generate structured learning path | ✅ |
| ResourceAgent | Create 7 types of educational resources | ❌ rule |
| TutorAgent | Interactive tutoring (SSE streaming) | ✅ |
| EvaluationAgent | Quiz generation + auto-scoring | ✅ |
| ReflectionAgent | Meta-analysis + improvement | ✅ |

---

## Slide 5: LLM Integration

**Title**: Pluggable LLM Provider Architecture

**Content**:

**Provider Factory Pattern**:
```
User Config (llm.json) → ProviderFactory → veritas.llm.create_provider()
                                              │
                        ┌─────────────────────┼─────────────────────┐
                        ▼                     ▼                     ▼
                    DeepSeek               OpenAI               Spark
                  (deepseek-chat)       (gpt-4o-mini)        (spark-pro)
```

**Security Design**:
- API keys stored in OS credential store (Windows Credential Manager, Linux Secret Service)
- Automatic XOR fallback for headless/server environments
- Never stored in plaintext — `llm.json` contains `keyring://provider` references

**First-Run Onboarding**:
1. Welcome page → choose provider
2. Enter API key → test connection
3. Save → key encrypted in OS keyring
4. Start learning

---

## Slide 6: Memory & Evaluation

**Title**: Intelligent Memory + Quality Gates

**Content**:

**Memory Architecture (3-layer)**:
```
Experience Memory ←── Session Memory ←── Working Memory
 (cross-session)       (per-session)       (in-flight)
```

**TF-IDF RAG Pipeline**:
- Zero embedding models, zero vector databases
- 46K course markdown indexed in <100ms
- Lazy singleton pattern — build once, reuse across sessions
- Graceful degradation — RAG failure → agent still works

**ReviewGate (3-tier evaluation)**:
| Tier | Check | Example |
|:-----|:------|:--------|
| L1: Structure | Fields populated, valid types | Profile has all 6 dimensions |
| L2: Content | Semantic quality, relevance | Plan matches learning goal |
| L3: Quality | Confidence score, improvement flag | Score ≥ 0.7 → automatic pass |

---

## Slide 7: Demo Flow

**Title**: Demo Scenario — Python Learning Plan

**Content**: Step-by-step walkthrough

| Step | Action | Agent | Output |
|:-----|:-------|:------|:-------|
| 1 | User inputs: "帮我制定 Python 学习计划" | — | — |
| 2 | ProfileAgent analyzes | ProfileAgent | 6-dim profile |
| 3 | Plan generation | PlannerAgent | Structured path |
| 4 | Resource creation | ResourceAgent | 7 resource types |
| 5 | Interactive tutoring | TutorAgent | SSE chat |
| 6 | Competency evaluation | EvaluationAgent | Quiz + score |
| 7 | Meta-reflection | ReflectionAgent | Improvements |

**Key Demo Features**:
- One-click "比赛演示" mode — no configuration needed
- Frozen fixture data — works fully offline
- Agent execution timeline — color-coded visualization
- KPI dashboard — correctness, personalization, coverage

---

## Slide 8: Deployment

**Title**: Cross-Platform Distribution

**Content**:

| Platform | Method | Size | Dependencies |
|:---------|:-------|:-----|:-------------|
| 🪟 Windows | `.exe` double-click | 54 MB | None |
| 🐧 Linux | `tar.gz` extract + run | 76 MB | None |
| 🐳 Docker | `docker pull` | — | Docker |
| 🌐 Browser | Streamlit Cloud | — | None |

**Windows Desktop (zero-dependency)**:
```
Download → Extract → Double-click A3-Agent.exe → Browser opens
```

**5-Stage Launcher**:
```
[1/5] Initialize user data     → %APPDATA%/A3-Agent/
[2/5] Start FastAPI backend    → http://127.0.0.1:8000
[3/5] Health check             → {"status":"ok"}
[4/5] Start Streamlit UI       → http://127.0.0.1:8501
[5/5] Open browser             → auto-launch
```

---

## Slide 9: Future Work

**Title**: Roadmap & Future Directions

**Content**:

| Priority | Feature | Impact |
|:---------|:--------|:-------|
| 🔴 High | macOS native .app | Complete cross-platform |
| 🔴 High | Multimodal input (image, audio) | Richer learning context |
| 🟡 Medium | Learning analytics dashboard | Teacher/parent visibility |
| 🟡 Medium | Collaborative learning (multi-student) | Group study scenarios |
| 🟢 Low | Plugin system for custom agents | Extensibility |
| 🟢 Low | Mobile companion app | On-the-go learning |

**Open Source**:
- GitHub: [Leisure-Auf1/A3-Multi-Agent-System](https://github.com/Leisure-Auf1/A3-Multi-Agent-System)
- Framework: [Leisure-Auf1/Veritas-Core](https://github.com/Leisure-Auf1/Veritas-Core)
- License: MIT

---

## Presenter Notes

### For Competition Defense
- Emphasize: 12-agent collaboration is the core innovation
- Show: architecture diagram (Slide 3) + demo video (Slide 7)
- Answer "why multi-agent?": each agent specializes, pipeline is transparent, decisions are traceable

### For Internship Interview
- Emphasize: engineering practices — 1154 tests, keyring security, PyInstaller packaging
- Show: provider factory pattern (Slide 5) — demonstrates system design skill
- Answer "what did you learn?": cross-platform distribution, OS-level security, multi-agent orchestration

### For Project Showcase
- Emphasize: zero-config demo mode — anyone can try it
- Show: screenshots of all 7 tabs
- Provide: live demo link (a3-agent.streamlit.app) or Windows .exe download
