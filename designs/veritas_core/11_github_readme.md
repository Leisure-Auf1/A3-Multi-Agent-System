# Veritas_Core — GitHub README

> **最终展示用 README — 面向 GitHub, AI Engineer 面试, 竞赛评审**

---

```markdown
# Veritas_Core — Trustworthy Personalized Learning Multi-Agent System

> A production-grade AI application combining Multi-Agent architecture, RAG,
> Memory, and Trust mechanisms for reliable personalized learning.

[![Python](https://img.shields.io/badge/python-3.11+-blue)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)]()
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

---

## What is Veritas_Core?

Veritas_Core is not a ChatGPT wrapper or a generic agent framework.

It's a **trustworthy personalized learning system** that:
- Understands students through natural language profiling
- Retrieves authoritative course knowledge via RAG
- Plans adaptive learning paths based on individual gaps
- Generates 5 types of personalized learning resources
- Evaluates learning outcomes and self-adjusts
- Protects against prompt injection, memory poisoning, and agent privilege escalation

> **"Veritas"** = Trust. Content reliability, agent accountability, and memory integrity are first-class concerns — not afterthoughts.

---

## Architecture

```
                        ┌──────────────────────────┐
                        │        Student            │
                        │   "我想系统学习多智能体系统"  │
                        └─────────────┬────────────┘
                                      │
┌─────────────────────────────────────▼─────────────────────────────────────┐
│                          FastAPI + Orchestrator                              │
│                                                                             │
│   ┌──────────┐  ┌───────────────┐  ┌──────────┐  ┌──────────────────┐     │
│   │ProfileAgent│  │KnowledgeAgent │  │PlannerAgent│  │  ResourceAgent   │     │
│   │ 画像构建    │  │ RAG知识检索    │  │ 路径规划    │  │ Agent+Tool调度    │     │
│   └──────────┘  └───────────────┘  └──────────┘  └──────┬───────────┘     │
│                                                          │                  │
│   ┌──────────────────┐        ┌──────────────────┐      │                  │
│   │ EvaluationAgent  │───────▶│ ReflectionAgent  │      │                  │
│   │ 学习+Agent双评估   │        │ 画像+路径调整      │◄─────┘                  │
│   └──────────────────┘        └──────────────────┘                         │
│                                                                             │
│                    ┌─────────────────────────────┐                         │
│                    │       Skill Router           │                         │
│                    │  Intent→Match→Permission→Load│                         │
│                    └─────────────┬───────────────┘                         │
│                                  │                                          │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│   │ Document │ │   PPT    │ │   Quiz   │ │   Code   │ │ MindMap  │       │
│   │Generator │ │Generator │ │Generator │ │Generator │ │Generator │       │
│   └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└───────────────────────────────────────────────────────────────────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         ▼                        ▼                        ▼
┌─────────────────┐  ┌─────────────────────┐  ┌──────────────────────┐
│   RAG Engine    │  │  Memory (3-Tier)    │  │   Trust Layer        │
│                 │  │                     │  │                      │
│ Parser→Chunker  │  │ Conversation(Redis) │  │ Memory Validation    │
│ →Embedder→VDB   │  │ Profile(PostgreSQL) │  │ Agent Permission     │
│ →Retriever      │  │ History(PG+Chroma)  │  │ Prompt Injection     │
│                 │  │                     │  │ Content Grounding    │
└─────────────────┘  └─────────────────────┘  └──────────────────────┘
```

---

## ✨ Features

### Core Learning Loop
- **🧠 Dynamic Student Profiling** — 8-dimension profiles extracted from natural language with Memory Trust validation
- **🔍 RAG-Enhanced Knowledge** — Course content as authoritative ground truth, not LLM hallucination
- **📋 Adaptive Learning Planning** — Knowledge-gap-driven path generation with real-time adjustment

### Resource Generation (Agent+Tool Architecture)
- **📚 5 Resource Types** — Course Notes (Markdown), PPT (.pptx), Mind Maps (Mermaid), Exercises (3 difficulty levels), Code Labs (Python)

### Trust & Security (Not an afterthought)
- **🛡️ Memory Trust Layer** — 6-step validation pipeline, dual-state storage (candidate/confirmed), anti-poisoning
- **🔒 Agent Permission System** — Capability matrix per agent, Tool Call Gateway (Identity→Parameter→Scope→Audit)
- **🛡️ Prompt Injection Defense** — 4-layer: Sanitize → Detect → Isolate → Validate
- **👤 Human-in-the-Loop** — Approval Gate for high-risk operations (profile changes, memory deletion)

### Engineering
- **📊 Dual Evaluation** — Learning evaluation (student) + Agent evaluation (AI system quality)
- **📈 Full Observability** — Trace audit, memory audit log, security alerts, learning analytics
- **⚡ Skill Budget** — Token/Time/Call/Cost limits prevent runaway agent behavior
- **🐳 Docker Deploy** — `docker compose up` — PostgreSQL + Redis + ChromaDB + FastAPI + Streamlit

---

## 🚀 Quick Start

```bash
# Clone
git clone https://github.com/Leisure-Auf1/Terence-Agent.git
cd Terence-Agent/projects/veritas-core

# (After Phase 5: Docker Compose)
docker compose up

# Open dashboard
open http://localhost:8501
```

### Demo Scenario

```
Student: "我是网络工程大三学生，Python基础不错，视觉型学习，想系统学多智能体系统"

→ ProfileAgent: 8-dim DynamicProfile {knowledge: mid_level, style: visual, ...}
→ KnowledgeAgent: RAG诊断 → KnowledgeGap {gaps: [async_io, agent_patterns]}
→ PlannerAgent: 5-level, 13-node learning path, visual strategy
→ ResourceAgent: 生成讲义 + PPT + 思维导图 + 练习题 + 代码实验
→ EvaluationAgent: 答题后评估 → 掌握度EMA更新
→ ReflectionAgent: 画像调整 → 路径优化 → 下一轮资源
```

---

## 📂 Project Structure

```
veritas_core/
├── src/
│   ├── agents/          # 6 Cognitive Agents (Business Logic)
│   ├── tools/           # 5 Generator Tools (Execution)
│   ├── rag/             # RAG Engine (Knowledge Retrieval)
│   ├── memory/          # 3-Tier Memory (Redis/PG/ChromaDB)
│   ├── trust/           # Trust Layer (Memory/Agent/Content Security)
│   ├── skills/          # Skill Router + Lifecycle + Budget
│   ├── evaluation/      # Dual Evaluation (Learning + Agent)
│   ├── observability/   # Trace + Analytics
│   ├── orchestrator/    # Pipeline DAG Engine
│   ├── api/             # FastAPI REST
│   ├── providers/       # LLM Provider Abstraction
│   └── core/            # EventBus + Contracts
├── tests/
│   ├── unit/            # Per-agent, per-module unit tests
│   ├── integration/     # End-to-end learning loop tests
│   └── security/        # Prompt injection, memory poison, privilege escalation
├── docs/                # Architecture + Design docs
├── deployment/          # Docker Compose + env config
└── knowledge_base/      # Course materials (6 chapters)
```

---

## 🛠 Tech Stack

| Layer | Technology | Why |
|:------|:-----------|:----|
| API | FastAPI | Async, auto OpenAPI, production-ready |
| Database | PostgreSQL 16 | Structured profiles, complex queries, ACID |
| Cache | Redis 7 | Low-latency session context, TTL |
| Vector DB | ChromaDB | Zero-ops, Python-native, metadata filtering |
| LLM | DeepSeek / Xunfei Spark | Provider-agnostic via LLMProvider interface |
| Frontend | Streamlit | Rapid prototyping dashboard |
| Container | Docker Compose | One-command deploy |
| Testing | pytest | 241 → 300+ target |

---

## 📖 Documentation

| Document | Contents |
|:---------|:---------|
| [Architecture](docs/architecture.md) | System design, data flow, 7-phase learning loop |
| [Agent Design](docs/agent-design.md) | 6-agent design + Agent+Tool architecture |
| [RAG Design](docs/rag-design.md) | Course knowledge enhancement module |
| [Memory Design](docs/memory-design.md) | 3-tier memory + SQL schema |
| [Security Architecture](docs/security-architecture.md) | Memory trust, agent permissions, injection defense |
| [Skill Extension](docs/skill-extension.md) | Skill lifecycle, router, budget |
| [ADR](docs/adr/) | 6 Architecture Decision Records |

---

## 🧪 Security Testing

```bash
# Run security tests
pytest tests/security/ -v

# Tests include:
# ✓ Prompt Injection    — 20+ payloads (instruction override, token injection, role hijacking)
# ✓ Memory Poison       — User claims validation, conflict detection, candidate expiry
# ✓ Privilege Escalation — Agent capability matrix enforcement
# ✓ Tool Abuse          — Oversized input, code injection, rate limiting, budget exhaustion
```

---

## 🎯 Why This Project Matters

| Engineering Dimension | Demonstrated Capability |
|:----------------------|:------------------------|
| **LLM Application Engineering** | RAG pipeline, 3-tier memory (Redis/PG/ChromaDB), FastAPI, Docker Compose |
| **Multi-Agent Architecture** | 6 agents with clear roles, Agent+Tool separation, Skill Router, EventBus |
| **RAG Engineering** | Parser→Chunker→Embedder→Retriever→ContextBuilder, Metadata filtering |
| **AI Security** | Memory Trust Layer, Agent Permission Matrix, Prompt Injection 4-layer defense |
| **Memory Engineering** | Dual-State Storage, Source Classification, Confidence Scoring, TTL |
| **Educational AI** | Complete learning loop, EMA mastery tracking, profile evolution audit |

---

## 📝 License

MIT

---

*Built as an evolution of A3 Multi-Agent System (v2.8) — 12 agents → 6 cognitive agents + 5 generator tools*
*Veritas_Core v1.0 — Architecture Freeze 2026-07-13*
```
