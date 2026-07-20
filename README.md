# A3-Agent — Multi-Agent Personalized Learning System

<p align="center">
  <img src="docs/assets/banner.svg" alt="A3-Agent Banner" width="100%">
</p>

[![Release](https://img.shields.io/badge/release-v1.0.0-blue)](https://github.com/Leisure-Auf1/A3-Multi-Agent-System/releases)
[![CI](https://github.com/Leisure-Auf1/A3-Multi-Agent-System/actions/workflows/test.yml/badge.svg)](https://github.com/Leisure-Auf1/A3-Multi-Agent-System/actions/workflows/test.yml)
[![Tests](https://img.shields.io/badge/tests-2857%2F2857-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Win%20%7C%20Linux%20%7C%20Docker-lightgrey)]()

> **Production-ready multi-agent AI learning platform.** 7 specialized agents orchestrated through an EventBus pipeline — profiles you, plans your path, generates content, quizzes you, reflects on your learning, and persists it to memory. 2857 tests, 0 failures.

**[📥 Download v1.0.0](https://github.com/Leisure-Auf1/A3-Multi-Agent-System/releases)** · **[🚀 Quick Start](docs/user/getting-started.md)** · **[📖 Docs](docs/)**

---

## What is A3?

A3 is a **complete AI-powered learning application** that orchestrates 7 specialized agents through A3Workflow + EventBus to deliver personalized education.

- 🧠 **Profiles you** across 6 cognitive dimensions
- 🗺️ **Plans your path** with adaptive learning sequences
- 📝 **Generates content** personalized to your profile
- 📚 **Recommends resources** matched to your needs
- 🔍 **Reviews quality** through ReviewGate evaluation
- 💭 **Reflects and improves** with ReflectionAgent
- 💾 **Persists learning** to memory for continuous adaptation
- ✅ **Interactive quizzes** with AI-powered error analysis and recovery plans
- 📋 **History replay** — revisit any past learning session with full results
- 🧠 **Memory dashboard** — see what AI has learned about your strengths and weaknesses

| Feature | Description |
|:--------|:------------|
| 🔐 **Zero-config demo** | Full pipeline runs offline — no API key needed |
| 🤖 **8 LLM providers** | DeepSeek, OpenAI, Anthropic, Google, Qwen, Kimi, Grok, Spark |
| 🖥️ **Cross-platform** | Windows `.exe`, Linux binary, Docker, Streamlit |
| 🔒 **Security** | JWT auth, role-based permissions, token budget |
| 📊 **Product UI** | 6-tab dashboard with onboarding, history replay, workspace, memory |
| 🎯 **Goal suggestions** | 3 clickable demo goals — start learning in 1 click |
| 🤖 **AI transparency** | Per-agent execution card — see which agents used LLM vs rule |
| ✅ **2857 tests** | 100% pass rate, 0 failures |

### Pipeline Execution Example

```bash
$ streamlit run web/app.py
# → Register → Click "Learn Python basics" → Run Pipeline

🤖 ProfileAgent        — cognitive analysis (7ms)
🗺️ PlannerAgent        — 5-node learning path (4ms)
📝 ContentGenerator    — personalized lesson (2ms)
📚 ResourceAgent       — 4 resources recommended (3ms)
💭 ReflectionAgent     — "well-structured for beginners" (1ms)
💾 Memory              — experience saved, profile updated (1ms)

✅ Pipeline complete — see plan, content, reflection, quiz
📋 History → replay any past session with full details
🧠 Memory → 12 concepts mastered, 3 areas to improve
```

---

## Screenshots

| Dashboard | Pipeline Results | Quiz & Reflection |
|:---------:|:----------------:|:-----------------:|
| ![Dashboard](docs/assets/screenshots/dashboard.svg) | ![Pipeline](docs/assets/screenshots/pipeline.svg) | ![Quiz](docs/assets/screenshots/quiz.svg) |

| Memory Card | Provider Settings |
|:-----------:|:-----------------:|
| ![Memory](docs/assets/screenshots/memory.svg) | ![Settings](docs/assets/screenshots/settings.svg) |

---

## Quick Start

### 🌐 Streamlit Cloud (zero install)

```
https://a3-agent.streamlit.app
```

### 🖥️ Windows Desktop

1. Download [`A3-Agent-v1.0.0-win64.zip`](https://github.com/Leisure-Auf1/A3-Multi-Agent-System/releases)
2. Extract → double-click `A3-Agent.exe`
3. Browser opens → choose Demo Mode or configure your LLM provider

📖 [Windows install guide →](docs/user/installation.md#windows)

### 🐧 Linux Desktop

```bash
curl -LO https://github.com/Leisure-Auf1/A3-Multi-Agent-System/releases/latest/download/A3-Agent-linux-x64.tar.gz
tar xzf A3-Agent-linux-x64.tar.gz
cd A3-Agent-linux-x64 && ./A3-Agent
```

### 🐳 Docker

```bash
docker pull leisureauf1/a3-multi-agent-system:latest
docker run -p 8501:8501 -p 8000:8000 leisureauf1/a3-multi-agent-system:latest
```

### 💻 From Source

```bash
git clone https://github.com/Leisure-Auf1/A3-Multi-Agent-System.git
cd A3-Multi-Agent-System
pip install -r requirements.txt
streamlit run web/app.py
```

📖 [Full install guide →](docs/user/installation.md)

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   User Interface                     │
│  web/app.py  →  6-tab Dashboard  →  Streamlit       │
├─────────────────────────────────────────────────────┤
│                     API Layer                        │
│  FastAPI /api/v2/*  →  A3APIClient                  │
├─────────────────────────────────────────────────────┤
│                 Security Layer                       │
│  Auth (JWT)  →  Permission (Role)  →  TokenBudget   │
├─────────────────────────────────────────────────────┤
│                 Pipeline Layer                       │
│  LearningPipelineService  →  A3Workflow             │
├─────────────────────────────────────────────────────┤
│                  Agent Layer                         │
│  ProfileAgent → PlannerAgent → ContentGenerator     │
│  → ResourceAgent → ReviewGate → ReflectionAgent     │
├─────────────────────────────────────────────────────┤
│                 Data Layer                           │
│  SQLite (users/sessions/records) + Filesystem        │
│  (artifacts/memory/audit)                            │
└─────────────────────────────────────────────────────┘
```

📖 [Full architecture →](docs/developer/architecture.md)

---

## Documentation

| For Users | For Developers |
|:----------|:---------------|
| [Getting Started](docs/user/getting-started.md) | [Architecture](docs/developer/architecture.md) |
| [Installation](docs/user/installation.md) | [API Reference](docs/developer/api.md) |
| [FAQ](docs/user/faq.md) | [Release Checklist](docs/release/release-checklist.md) |
| [Demo Script](docs/demo/demo-script.md) | [Changelog](docs/release/changelog.md) |

---

## Testing

```bash
# Run all tests
make test

# 2857 tests, 0 failures
```

📖 [Security documentation →](docs/product/security-production-readiness.md)

---

## License

MIT — see [LICENSE](LICENSE)

---

*Built as an open-source AI learning research project.*
