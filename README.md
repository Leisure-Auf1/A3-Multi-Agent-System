# A3-Agent — Multi-Agent Personalized Learning System

[![Release](https://img.shields.io/badge/release-v7.1.0-blue)](https://github.com/Leisure-Auf1/A3-Multi-Agent-System/releases)
[![CI](https://github.com/Leisure-Auf1/A3-Multi-Agent-System/actions/workflows/test.yml/badge.svg)](https://github.com/Leisure-Auf1/A3-Multi-Agent-System/actions/workflows/test.yml)
[![Tests](https://img.shields.io/badge/tests-1164%2F1164-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Win%20%7C%20Linux%20%7C%20Docker-lightgrey)]()

> **A 12-agent AI learning system that builds personalized curricula from natural language.**
>
> *Describe what you want to learn. A team of specialized AI agents profiles you, plans your path, generates resources, tutors interactively, and evaluates your progress — all locally, with zero-config demo mode.*

**[🌐 Live Demo](https://a3-agent.streamlit.app)** · **[📥 Download](https://github.com/Leisure-Auf1/A3-Multi-Agent-System/releases)** · **[📖 Docs](docs/)** · **[📝 Blog](docs/blog/)**

---

## What is A3?

A3 is a **complete AI-powered learning application** that orchestrates 12 specialized agents through an EventBus to deliver personalized education. Unlike generic AI chatbots that answer one question at a time, A3:

- 🧠 **Profiles you** across 6 cognitive dimensions from natural language input
- 📋 **Plans your path** with adaptive, goal-driven learning sequences
- 📚 **Generates resources** in 7 formats: documents, mindmaps, exercises, code, slides, illustrations, video scripts
- 🎓 **Tutors interactively** via SSE-streaming chat with knowledge retrieval
- 📊 **Evaluates and improves** through ReviewGate + explainability tracing

**Key qualities:**

| | |
|:--|:--|
| 🔐 **Zero-config demo** | Full 6-agent pipeline runs offline — no API key, no network |
| 🏗️ **5-layer architecture** | Presentation → Agent → Intelligence → Trust → Data |
| 🖥️ **Cross-platform** | Windows `.exe`, Linux binary, Docker, Streamlit Cloud |
| 🔒 **OS keyring security** | API keys stored in Windows Credential Manager / Linux Secret Service |
| ✅ **1164 tests** | 100% pass rate, 0 failures |

---

## Quick Start

### 🌐 Browser (zero install, recommended)

```
https://a3-agent.streamlit.app
```

Deploy your own on [Streamlit Cloud](https://share.streamlit.io) in 2 clicks.

### 🖥️ Desktop App (Windows)

1. Download [`A3-Agent-v7.1.0-win64.zip`](https://github.com/Leisure-Auf1/A3-Multi-Agent-System/releases/download/v7.1.0/A3-Agent-v7.1.0-win64.zip) (54 MB)
2. Extract anywhere — **double-click `A3-Agent.exe`**
3. Browser opens automatically → configure provider or try Demo Mode

📖 [Full Windows install guide →](docs/INSTALL-windows.md)

### 🐧 Desktop App (Linux)

```bash
curl -LO https://github.com/Leisure-Auf1/A3-Multi-Agent-System/releases/download/v7.1.0/A3-Agent-v7.1.0-linux-x64.tar.gz
tar xzf A3-Agent-v7.1.0-linux-x64.tar.gz
cd A3-Agent-v7.1.0-linux-x64 && ./A3-Agent
```

📖 [Full Linux install guide →](docs/INSTALL-linux.md)

### 🐳 Docker

```bash
docker pull leisureauf1/a3-multi-agent-system:latest
docker run -p 8501:8501 leisureauf1/a3-multi-agent-system:latest
```

### 💻 Run from Source

```bash
git clone https://github.com/Leisure-Auf1/A3-Multi-Agent-System.git
cd A3-Multi-Agent-System
pip install -r requirements.txt
python -m desktop.launcher
```

---

## First Launch

| Step | Action |
|:-----|:-------|
| 1 | Launch A3 → Welcome page appears |
| 2 | Choose provider (DeepSeek / OpenAI / Spark) or **🎭 Demo Mode** |
| 3 | If using a provider: enter API key → Test connection → Save |
| 4 | Enter the main app — 7 tabs of AI-powered learning |

API keys are stored in your OS credential store, not plaintext files.

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  🖥️  Presentation    Streamlit 7-tab UI · FastAPI · Desktop  │
├──────────────────────────────────────────────────────────────┤
│  🤖  Agent Pipeline  Profile→Planner→Resource→Tutor→Eval     │
│                       EventBus · TraceCollector              │
├──────────────────────────────────────────────────────────────┤
│  🧠  Intelligence    LLM Factory · TF-IDF RAG · Memory       │
├──────────────────────────────────────────────────────────────┤
│  🔐  Trust           ReviewGate · Keyring · JWT Auth         │
├──────────────────────────────────────────────────────────────┤
│  💾  Data            SQLite (WAL) · Profiles · Threads       │
└──────────────────────────────────────────────────────────────┘
                                │
                        Veritas-Core 7.0
                  (Agent Runtime Framework)
```

📖 [Full Architecture](docs/competition/architecture.md) · [Agent Design](docs/competition/agent-design.md)

---

## Supported Providers

| Provider | Models | Best For |
|:---------|:-------|:---------|
| 🌊 DeepSeek | deepseek-chat, v4-pro | High value, strong Chinese |
| 🤖 OpenAI | gpt-4o-mini, gpt-4o | Global SOTA capability |
| 🚀 Spark | spark-pro, spark-lite | China-compliant deployment |
| 🎭 Mock | mock-model-v1 | **No key needed** — full offline demo |

---

## Performance

| Metric | Mock Mode | DeepSeek (API) |
|:-------|:----------|:---------------|
| Full Pipeline Latency | ~500ms | ~2-5s |
| Profile Extraction | <10ms | ~200ms |
| Plan Generation | ~50ms | ~500ms |
| Resource Recommendation | ~30ms | ~300ms |
| Memory Usage (idle) | ~80MB | ~80MB |

📖 [Full Benchmark](docs/competition/benchmark.md)

---

## Documentation

### Getting Started
| Document | Description |
|:---------|:------------|
| [Linux Install Guide](docs/INSTALL-linux.md) | Arch/Ubuntu/Fedora — tar.gz + source build |
| [Windows Install Guide](docs/INSTALL-windows.md) | zip extraction, Defender, SmartScreen |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Common issues: ports, API keys, bundle errors |
| [User Guide](docs/USER_GUIDE.md) | 7-tab reference + workflow |

### Architecture & Design
| Document | Description |
|:---------|:------------|
| [Architecture](docs/competition/architecture.md) | 5-layer system design |
| [Agent Design](docs/competition/agent-design.md) | 12-agent pipeline specification |
| [Memory & RAG](docs/competition/memory-rag-design.md) | Memory manager + TF-IDF retrieval |
| [Evaluation Design](docs/competition/evaluation-design.md) | ReviewGate + confidence metrics |

### Blog Series
| Article | Topic |
|:--------|:------|
| [01 — Architecture Evolution](docs/blog/01-architecture-evolution.md) | From monolith to 12-agent pipeline |
| [02 — Multi-Agent Design](docs/blog/02-multi-agent-design.md) | EventBus concurrency + coordinator patterns |
| [03 — Memory & RAG](docs/blog/03-memory-rag-system.md) | SQLite memory + TF-IDF retrieval |
| [04 — Evaluation & Tracing](docs/blog/04-agent-evaluation-and-tracing.md) | ReviewGate + explainability chain |
| [05 — Production](docs/blog/05-productionization-and-deployment.md) | PyInstaller, Docker, Streamlit Cloud |
| [06 — Lessons Learned](docs/blog/06-lessons-learned.md) | Engineering takeaways |

### More
| Document | Description |
|:---------|:------------|
| [Release Notes](docs/RELEASE_NOTES_v7.1.0.md) | v7.1.0 highlights + checksums |
| [Release Checklist](docs/release-checklist.md) | Cross-platform validation |
| [Demo Script](docs/competition/demo-script.md) | 5-minute walkthrough |
| [Benchmark](docs/competition/benchmark.md) | Performance data |

---

## Release

[![Release](https://img.shields.io/badge/v7.1.0-stable-blue)](https://github.com/Leisure-Auf1/A3-Multi-Agent-System/releases/tag/v7.1.0)

| Platform | Download | Size |
|:---------|:---------|:-----|
| 🪟 Windows x64 | [`A3-Agent-v7.1.0-win64.zip`](https://github.com/Leisure-Auf1/A3-Multi-Agent-System/releases/download/v7.1.0/A3-Agent-v7.1.0-win64.zip) | 54 MB |
| 🐧 Linux x64 | [`A3-Agent-v7.1.0-linux-x64.tar.gz`](https://github.com/Leisure-Auf1/A3-Multi-Agent-System/releases/download/v7.1.0/A3-Agent-v7.1.0-linux-x64.tar.gz) | 76 MB |
| 🐳 Docker | [`leisureauf1/a3-multi-agent-system:latest`](https://hub.docker.com/r/leisureauf1/a3-multi-agent-system) | — |
| 🌐 Web | [a3-agent.streamlit.app](https://a3-agent.streamlit.app) | — |

```bash
# Verify checksum
sha256sum -c A3-Agent-v7.1.0-linux-x64.sha256
```

---

## License

MIT — [Leisure-Auf1](https://github.com/Leisure-Auf1)
