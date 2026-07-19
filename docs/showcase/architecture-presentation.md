# A3-Agent — Architecture Presentation

## For: Competition Judges, Technical Interviewers, Portfolio Reviewers

---

## Slide 1: Title

**A3-Agent v7.1.0 — Multi-Agent Personalized Learning System**

> 12 specialized AI agents collaborate through EventBus to deliver personalized education. 5-layer architecture. 1154 tests. Competition-ready.

---

## Slide 2: Problem Statement

| Traditional AI Learning | A3 Multi-Agent System |
|:------------------------|:----------------------|
| Single LLM call | 12 agents collaborate |
| No personalization | 6-dimension student profile |
| Generic responses | Knowledge-base-driven plans |
| Black box | Full explainability chain |
| Requires API keys | Works offline (mock mode) |

---

## Slide 3: Architecture Overview

```
┌─────────────────────────────────────────────┐
│ 🖥️  Presentation Layer                       │
│ Streamlit 7-tab UI · FastAPI 25 endpoints   │
│ Desktop .exe · Docker · Streamlit Cloud     │
├─────────────────────────────────────────────┤
│ 🤖  Agent Pipeline Layer                    │
│ Profile→Planner→Resource→Tutor→Eval→Reflect│
│ EventBus · TraceCollector                   │
├─────────────────────────────────────────────┤
│ 🧠  Intelligence Layer                      │
│ LLM ProviderFactory · RAG (TF-IDF)          │
│ Memory Manager (SQLite) · Multimodal Gateway│
├─────────────────────────────────────────────┤
│ 🔐  Trust & Security Layer                  │
│ ReviewGate (3-tier) · Keyring · Auth (JWT)  │
├─────────────────────────────────────────────┤
│ 💾  Data Layer                              │
│ SQLite WAL · Profiles · Threads · Resources │
└─────────────────────────────────────────────┘
```

---

## Slide 4: Agent Pipeline

```
Student: "I want to learn Multi-Agent AI"
    │
    ▼
ProfileAgent ──→ 6-dimension profile (mid_level, visual, fast_track)
    │
    ▼
PlannerAgent ──→ 5-node learning path with teaching strategies
    │
    ▼
ResourceAgent ──→ 6 resources (docs, code, exercises, projects)
    │
    ▼
ReviewAgent ────→ Quality scoring: 86/100 (PASSED)
    │
    ▼
ReflectionAgent → Improvement suggestions + profile update
    │
    ▼
Memory ────────→ Persistent storage for next session
```

---

## Slide 5: Key Differentiators

| Feature | Implementation |
|:--------|:--------------|
| **Multi-Agent** | 12 agents via EventBus, not single LLM |
| **Personalization** | 6-dimension profile from natural language |
| **Zero-config Demo** | Mock providers, offline, no API key |
| **Trust** | ReviewGate 3-tier: AST → Pytest → Judge |
| **Security** | OS keyring, encrypted API keys |
| **Platform** | Windows .exe, Linux binary, Docker, Cloud |
| **Quality** | 1154 tests, 100% pass rate |

---

## Slide 6: Technical Stack

| Layer | Technology |
|:------|:-----------|
| Frontend | Streamlit (Python-native, 7 tabs) |
| API | FastAPI (async, SSE streaming) |
| Database | SQLite WAL (zero-config, concurrent) |
| Agent Runtime | Veritas-Core (in-house framework) |
| LLM | DeepSeek / OpenAI / Spark (ProviderFactory) |
| Security | Keyring (OS credential store) |
| Packaging | PyInstaller (one-dir, 221 MB) |
| Deployment | Docker, Streamlit Cloud, Render |

---

## Slide 7: Demo Flow

```
1. Welcome Page  → First-run detection, provider setup
2. Demo Pipeline → 6 agents, <1s, mock providers
3. Dashboard     → KPI cards, timeline, explainability
4. Architecture  → 5-layer diagram, agent details
5. Settings      → Provider switch, keyring security
```

**All offline. No API key. No network.**

---

## Slide 8: Results

| Metric | Value |
|:-------|:------|
| Agents | 12 |
| Tests | 1154 (100% pass) |
| Architecture Layers | 5 |
| API Endpoints | 25 |
| UI Tabs | 7 |
| Documentation | 13 docs |
| Release Size | 75 MB (compressed) |

---

## Slide 9: Contact

- **GitHub**: https://github.com/Leisure-Auf1/A3-Multi-Agent-System
- **Release**: https://github.com/Leisure-Auf1/A3-Multi-Agent-System/releases/tag/v7.1.0
- **License**: MIT
