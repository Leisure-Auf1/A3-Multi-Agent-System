# A3 System Architecture

## Overview

A3 employs a **5-layer architecture** designed for separation of concerns, testability, and competition demonstration. Each layer is independently testable and replaceable.

```
┌──────────────────────────────────────────────────────────────────┐
│                     🖥️  Presentation Layer                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────┐ │
│  │  Streamlit UI   │  │   FastAPI v2    │  │  Desktop (.exe)  │ │
│  │  · 7 tabs       │  │  · 25 endpoints │  │  · PyInstaller   │ │
│  │  · Onboarding   │  │  · REST + SSE   │  │  · Self-contained│ │
│  └─────────────────┘  └─────────────────┘  └──────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                                │
┌───────────────────────────────┼──────────────────────────────────┐
│                     🤖  Agent Pipeline Layer                     │
│                                                                  │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────┐ │
│  │ Profile  │──▶│ Planner  │──▶│ Resource │──▶│  Evaluation  │ │
│  │ Agent    │   │ Agent    │   │ Agent    │   │  Agent       │ │
│  └──────────┘   └──────────┘   └──────────┘   └──────────────┘ │
│       │              │              │               │           │
│       └──────────────┼──────────────┼───────────────┘           │
│                      │   EventBus   │                           │
│              ┌───────┴──────┐ ┌─────┴────────┐                  │
│              │  Reflection  │ │  Tutor Agent │                  │
│              │  Agent       │ │  (streaming) │                  │
│              └──────────────┘ └──────────────┘                  │
└──────────────────────────────────────────────────────────────────┘
                                │
┌───────────────────────────────┼──────────────────────────────────┐
│                     🧠  Intelligence Layer                       │
│                                                                  │
│  ┌──────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐   │
│  │LLM Provider  │ │   RAG    │ │  Memory  │ │ Multimodal   │   │
│  │Factory       │ │Retriever │ │ Manager  │ │ Gateway      │   │
│  │              │ │(TF-IDF)  │ │(SQLite)  │ │(7 types)     │   │
│  │DeepSeek/     │ │          │ │          │ │              │   │
│  │OpenAI/Spark/ │ │Fallback: │ │Session-  │ │Document/Code/│   │
│  │Mock/Rule     │ │Rule-based│ │scoped    │ │Slides/PPT…   │   │
│  └──────────────┘ └──────────┘ └──────────┘ └──────────────┘   │
└──────────────────────────────────────────────────────────────────┘
                                │
┌───────────────────────────────┼──────────────────────────────────┐
│                     🔐  Trust & Security Layer                   │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │ReviewGate│ │  User    │ │ Keyring  │ │ Auth Middleware  │   │
│  │          │ │Simulation│ │ Storage  │ │                  │   │
│  │Correct-  │ │          │ │          │ │JWT tokens        │   │
│  │ness 0.92 │ │Mimics    │ │Windows CM│ │Guest mode        │   │
│  │Personal- │ │student   │ │Linux SS  │ │Thread isolation  │   │
│  │ization   │ │behavior  │ │macOS KC  │ │Cross-user auth   │   │
│  │0.85      │ │          │ │          │ │                  │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
                                │
┌───────────────────────────────┼──────────────────────────────────┐
│                     💾  Data Layer                              │
│                                                                  │
│  SQLite (WAL mode) — users · profiles · threads · messages      │
│  · resources · sessions · learning_records · schema_migrations  │
│                                                                  │
│  Design: Single-file · Zero-config · WAL concurrency            │
│  Migrations: ALTER TABLE + version tracking                     │
└──────────────────────────────────────────────────────────────────┘
```

## Design Principles

### 1. Separation of Concerns
Each layer depends only on the layer below it. Agents never directly access the database; the Data layer is the single source of truth for persistence.

### 2. Provider Abstraction
The LLM Provider Factory abstracts all AI model backends behind a single interface:
```python
provider = create_provider("deepseek")  # or openai, spark, mock, rule
response = provider.generate(prompt="...")
```

Priority: `user config (llm.json) > env var > mock > rule`

### 3. Event-Driven Communication
Agents communicate exclusively through the EventBus, not direct method calls. This enables:
- Independent testing of each agent
- Trace collection for observability
- Loose coupling for future agent additions

### 4. Trust by Design
Every agent output passes through ReviewGate before reaching the student. The gate evaluates:
- **Correctness**: Is the content factually accurate?
- **Personalization**: Does it match the student profile?
- **Explainability**: Can the reasoning be traced?
- **Efficiency**: Are resources used appropriately?

### 5. Zero-Config Operation
The system works fully offline with mock providers. No API keys, no network, no external services required for demonstration. Real LLM integration is optional and user-configurable.

## Technology Stack

| Component | Technology | Rationale |
|:----------|:-----------|:----------|
| Frontend | Streamlit | Rapid UI, Python-native, no JS required |
| API | FastAPI | Async, auto-docs, SSE streaming |
| Database | SQLite (WAL) | Zero-config, embedded, fast reads |
| Agent Runtime | Veritas-Core 7.0 | In-house framework, event-driven |
| LLM | DeepSeek/OpenAI/Spark | Multi-provider via ProviderFactory |
| Security | Keyring | OS-native credential storage |
| Packaging | PyInstaller (Win) / tar.gz (Linux) | Self-contained distribution |
| Container | Docker | Reproducible deployment |

## Deployment Modes

| Mode | Requirements | Use Case |
|:-----|:------------|:---------|
| Docker | Docker Engine | Production / cloud |
| Linux tar.gz | Python 3.10+ | Linux desktop |
| Windows .exe | Nothing | Windows desktop |
| Streamlit Cloud | GitHub repo | Free hosting |
| Render | GitHub repo | Free tier hosting |
