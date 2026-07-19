# GitHub Release Notes — v7.1.0

## Release: A3-Agent v7.1.0

🎉 First competition-ready release of the A3 Multi-Agent Learning System.

---

## Highlights

- **12 AI Agents** collaborate through an EventBus for personalized learning
- **7-tab Streamlit UI** with architecture overview, dashboard, and competition demo
- **5-layer architecture**: Presentation → Agent → Intelligence → Trust → Data
- **Zero-config demo**: Full pipeline runs offline with mock providers
- **Cross-platform**: Windows (.exe), Linux (tar.gz), Docker, Streamlit Cloud
- **OS keyring security**: API keys stored in Windows Credential Manager / Linux Secret Service
- **1154 tests**: 100% pass rate, 0 failures

---

## Downloads

| Platform | Asset | Size |
|:---------|:------|:-----|
| 🪟 Windows x64 | `A3-Agent-v7.1.0-win64.zip` | 54 MB |
| 🐧 Linux x64 | `A3-Agent-v7.1.0-linux-x64.tar.gz` | 76 MB |
| 🐳 Docker | `leisureauf1/a3-multi-agent-system:latest` | — |
| 🌐 Browser | [a3-agent.streamlit.app](https://a3-agent.streamlit.app) | — |

### Verification

```bash
# Linux
sha256sum -c A3-Agent-v7.1.0-linux-x64.sha256

# Windows (PowerShell)
Get-FileHash -Algorithm SHA256 A3-Agent-v7.1.0-win64.zip
```

### Checksums

```
# Linux
d0d8b88e21d312eae0717250e434a06f1a47c6d18b3102c6d40c13b6eb03b2a5  A3-Agent-v7.1.0-linux-x64.tar.gz

# Windows
3063ec38f82b84a0a255b319bea444d43f55668da1e032110e49107f199e8bfa  A3-Agent-v7.1.0-win64.zip
```

---

## Quick Start

### Windows (Desktop App — zero dependencies)
1. Download `A3-Agent-v7.1.0-win64.zip`
2. Extract anywhere, double-click `A3-Agent.exe`
3. Browser opens automatically → configure provider or try Demo Mode

### Linux
```bash
tar xzf A3-Agent-v7.1.0-linux-x64.tar.gz
cd A3-Agent-v7.1.0-linux-x64 && ./A3-Agent
```

### Browser (recommended, zero install)
Visit [a3-agent.streamlit.app](https://a3-agent.streamlit.app)

### Docker
```bash
docker pull leisureauf1/a3-multi-agent-system:latest
docker run -p 8501:8501 leisureauf1/a3-multi-agent-system:latest
```

---

## What's New

### 🪟 Windows Desktop Edition
Native Windows executable with 5-stage launcher: initialize → FastAPI backend → Streamlit UI → browser. User data stored in `%APPDATA%\A3-Agent\`. API keys encrypted via Windows Credential Manager.

### 🏆 Competition Demo
One-click pipeline execution with frozen fixture data. No API key, no network. Activates from "比赛演示" tab.

### 🔐 Keyring Security
API keys stored in OS credential store (Windows Credential Manager, Linux Secret Service). Automatic XOR fallback when keyring unavailable.

### 🚀 First-Run Onboarding
Welcome page with step-by-step provider setup. Select provider → enter API key → test connection → start learning. Or skip with "Demo Mode".

### 📊 Demo Dashboard
Live agent execution timeline with color-coded bars, KPI cards, explainability chain, and trust metrics.

### 🏗️ Architecture Overview
Interactive 5-layer system diagram: Presentation → Agent Pipeline → Intelligence → Trust → Data.

---

## Verification

| Metric | Value |
|:-------|:------|
| Tests | 1154/1154 passed |
| Failures | 0 |
| Agent core changes | 0 |
| Workflow changes | 0 |
| Veritas-Core changes | 0 |
| Release validation (Linux) | 32/32 checks passed |
| Release validation (Windows) | 32/32 checks passed |

---

## Documentation

- [Installation Guide](docs/INSTALL.md)
- [User Guide](docs/USER_GUIDE.md)
- [Architecture](docs/competition/architecture.md)
- [Agent Design](docs/competition/agent-design.md)
- [Memory & RAG](docs/competition/memory-rag-design.md)
- [Evaluation Design](docs/competition/evaluation-design.md)
- [Demo Script](docs/competition/demo-script.md)
- [Release Checklist](docs/release-checklist.md)
- [Screenshots Guide](docs/screenshots.md)

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for full release history from v6.x to v7.1.0.

---

## Contributors

Built by [Leisure-Auf1](https://github.com/Leisure-Auf1) on [Veritas-Core](https://github.com/Leisure-Auf1/Veritas-Core).
