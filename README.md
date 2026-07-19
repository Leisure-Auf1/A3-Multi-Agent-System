# A3 — AI Personalized Learning System

[![Version](https://img.shields.io/badge/version-7.1.0-blue)](https://github.com/Leisure-Auf1/A3-Multi-Agent-System)
[![Tests](https://img.shields.io/badge/tests-1154%20passed-brightgreen)](https://github.com/Leisure-Auf1/A3-Multi-Agent-System/actions)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20Docker-lightgrey)]()

> **Competition-Ready AI Learning Software** · 12 Agents · 1154 Tests · 5-Layer Architecture
>
> *"Students describe what they want to learn. A team of AI agents does the rest."*

---

## What is A3?

A3 is a **complete AI-powered learning application** that combines 12 specialized agents to deliver personalized education. Unlike generic AI chatbots, A3 builds a 6-dimension student profile, generates tailored learning paths, creates 7 types of multimodal resources, tutors interactively, evaluates understanding, and continuously improves — all through a professional Streamlit interface.

**Key Differentiators**:
- 🧠 **Multi-Agent Pipeline** — Not a single LLM call; 12 agents collaborate via EventBus
- 👤 **6-Dimension Profiling** — Natural language → automatic cognitive analysis
- 📚 **7 Resource Types** — Documents, mindmaps, exercises, code, slides, illustrations, video scripts
- 🔐 **Zero-Config Demo** — Works fully offline with mock providers; no API key needed
- 🏗️ **5-Layer Architecture** — Presentation → Agent → Intelligence → Trust → Data

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  🖥️  Presentation    Streamlit UI · FastAPI · Desktop .exe    │
├──────────────────────────────────────────────────────────────┤
│  🤖  Agent Pipeline  Profile→Planner→Resource→Tutor→Eval     │
│                       EventBus · TraceCollector              │
├──────────────────────────────────────────────────────────────┤
│  🧠  Intelligence    LLM Factory · RAG · Memory · Multimodal │
├──────────────────────────────────────────────────────────────┤
│  🔐  Trust & Security  ReviewGate · Keyring · Auth (JWT)     │
├──────────────────────────────────────────────────────────────┤
│  💾  Data            SQLite (WAL) · Profiles · Threads       │
└──────────────────────────────────────────────────────────────┘
                                │
                        Veritas-Core 7.0
                  (Agent Runtime Framework)
```

📖 [Full Architecture](docs/competition/architecture.md) · [Agent Design](docs/competition/agent-design.md)

---

## Quick Start

### ⚡ Browser (recommended — zero install, free)
```
https://a3-agent.streamlit.app
```
Deploy your own in 2 clicks: [Streamlit Cloud](https://share.streamlit.io) → select repo → deploy.

No Python. No API keys. No Docker. Works on any device with a browser.

### 🐳 Docker
```bash
docker pull leisureauf1/a3-multi-agent-system:latest
docker run -p 8501:8501 leisureauf1/a3-multi-agent-system:latest
```

### 💻 Local
```bash
pip install -r requirements.txt
streamlit run app.py
```
```bash
streamlit run app.py
# → Click "🏆 比赛演示" tab → Click "运行完整 Pipeline"
```

---

## First Launch Guide

| Step | Action |
|:-----|:-------|
| 1 | Launch A3 → Welcome page appears |
| 2 | Choose provider (DeepSeek / OpenAI / Spark / Demo) |
| 3 | Enter API key → Test connection → Save |
| 4 | Enter the main app — 7 tabs of AI-powered learning |

Or click **🎭 Demo Mode** to skip configuration entirely.

🔐 API keys are stored in your OS credential store (Windows Credential Manager / Linux Secret Service / macOS Keychain).

---

## Supported Providers

| Provider | Model | Best For |
|:---------|:------|:---------|
| 🌊 DeepSeek | deepseek-chat, v4-pro | High value, strong Chinese |
| 🤖 OpenAI | gpt-4o-mini, gpt-4o | Global SOTA capability |
| 🚀 Spark | spark-pro, spark-lite | China-compliant |
| 🎭 Mock | mock-model-v1 | **No key needed** — full offline demo |

---

## Benchmark

| Metric | Mock Mode | DeepSeek (API) |
|:-------|:----------|:---------------|
| Full Pipeline Latency | ~500ms | ~2-5s (network) |
| Profile Extraction | <10ms | ~200ms |
| Plan Generation | ~50ms | ~500ms |
| Resource Recommendation | ~30ms | ~300ms |
| ReviewGate Scoring | ~5ms | ~200ms |
| Memory Usage (idle) | ~80MB | ~80MB |

**1154 tests, 100% pass rate, 0 external failures.**

📖 [Full Benchmark](docs/competition/benchmark.md)

---

## Project Status

| Phase | Milestone | Status |
|:------|:----------|:------:|
| 1–6 | Runtime Engine, SDK, Recovery, Lifecycle | ✅ |
| 7.0 | Veritas-Core Independence | ✅ |
| 8.0 | Productization Audit | ✅ |
| 9.x | Data Layer, Tutor, Evaluation, Multimodal | ✅ |
| 4.0 | User LLM Configuration Layer | ✅ |
| 5.0 | First-Run Onboarding | ✅ |
| 6.0 | Release Hardening (keyring, capability detection) | ✅ |
| 7.0 | Release Validation & Distribution | ✅ |
| 8.0 | Competition Demo Polish | ✅ |

---

## Documentation

| Document | Description |
|:---------|:------------|
| [Architecture Design](docs/competition/architecture.md) | 5-layer system architecture |
| [Agent Design](docs/competition/agent-design.md) | 12-agent pipeline specification |
| [Memory & RAG](docs/competition/memory-rag-design.md) | Memory manager + TF-IDF retrieval |
| [Evaluation Design](docs/competition/evaluation-design.md) | ReviewGate + confidence metrics |
| [Demo Script](docs/competition/demo-script.md) | 5-minute competition presentation |
| [Deployment](docs/competition/deployment.md) | Streamlit Cloud / Render / Docker |
| [Benchmark](docs/competition/benchmark.md) | Performance benchmarks |
| [Release Checklist](docs/release-checklist.md) | Cross-platform validation |
| [Demo Video Script](docs/showcase/demo-video-script.md) | 5-minute recording guide |
| [Architecture Slides](docs/showcase/architecture-presentation.md) | Slide deck for presentations |
| [Resume Description](docs/showcase/internship-resume.md) | STAR-format project summary |
| [Demo Assets](docs/showcase/demo-assets.md) | Screenshots + capture guide |
| [Install Guide](docs/INSTALL.md) | Windows / Linux / Docker setup |
| [User Guide](docs/USER_GUIDE.md) | Tab reference + workflow |
| [Screenshots](docs/screenshots.md) | UI capture guide for demos |
| [Release Notes](docs/RELEASE_NOTES_v7.1.0.md) | v7.1.0 release notes |
| [Windows Validation](docs/windows-release-validation.md) | Windows build + E2E checklist |

---

## Showcase

| Asset | Purpose |
|:------|:--------|
| 🎬 [Demo Video Script](docs/showcase/demo-video-script.md) | 8-scene recording guide (3-5 min) |
| 📊 [Architecture Slides](docs/showcase/architecture-presentation.md) | 9-slide presentation deck |
| 📄 [Internship Resume](docs/showcase/internship-resume.md) | STAR-format project description |
| 📸 [Demo Assets](docs/showcase/demo-assets.md) | 8 screenshots + capture instructions |

---

## Release

[![Release](https://img.shields.io/badge/release-v7.1.0-blue)](https://github.com/Leisure-Auf1/A3-Multi-Agent-System/releases/tag/v7.1.0)

| Platform | Download |
|:---------|:---------|
| 🐧 Linux | `A3-Agent-v7.1.0-linux-x64.tar.gz` (76 MB) |
| 🪟 Windows | `A3-Agent-v7.1.0-win64.zip` (coming soon — build from source: `desktop\\build.bat`) |

```bash
# Verify checksum
sha256sum -c A3-Agent-v7.1.0-linux-x64.sha256
```

---

## License

MIT — [Leisure-Auf1](https://github.com/Leisure-Auf1)
