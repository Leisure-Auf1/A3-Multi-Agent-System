# GitHub Release Notes — v7.1.0

## Release: A3-Agent v7.1.0

🎉 First competition-ready release of the A3 Multi-Agent Learning System.

---

## Highlights

- **12 AI Agents** collaborate through an EventBus for personalized learning
- **7-tab Streamlit UI** with architecture overview and competition demo
- **5-layer architecture**: Presentation → Agent → Intelligence → Trust → Data
- **Zero-config demo**: Full pipeline runs offline with mock providers
- **OS keyring security**: API keys stored in Windows Credential Manager / Linux Secret Service
- **1154 tests**: 100% pass rate, 0 failures

---

## What's New

### 🏆 Competition Demo
One-click pipeline execution with frozen fixture data. No API key, no network, no configuration. Activates from the "比赛演示" tab.

### 🔐 Keyring Security
API keys are now stored in your operating system's credential store (Windows Credential Manager, Linux Secret Service, macOS Keychain) instead of config files. Automatic fallback to local encryption when keyring is unavailable.

### 🚀 First-Run Onboarding
New users see a Welcome page with step-by-step provider setup. Select provider → enter API key → test connection → start learning. Or skip with "Demo Mode".

### 📊 Demo Dashboard
Live agent execution timeline with color-coded bars, KPI cards, explainability chain, and trust metrics (correctness 92%, personalization 85%).

### 🏗️ Architecture Overview
Interactive 5-layer system diagram showing Presentation, Agent Pipeline, Intelligence, Trust, and Data layers.

### 🔧 Database Migration Fix
Fixed `is_guest` column missing in pre-v7.0 databases. All 1154 tests now pass with zero failures.

---

## Installation

### Browser (recommended, zero install):
```
https://a3-agent.streamlit.app
```

### Linux:
```bash
tar xzf A3-Agent-v7.1.0-linux-x64.tar.gz
cd A3-Agent-v7.1.0-linux-x64 && ./A3-Agent
```

### Windows:
```batch
REM Extract A3-Agent-v7.1.0-win64.zip, then:
A3-Agent.exe
```

### Docker:
```bash
docker pull leisureauf1/a3-multi-agent-system:latest
docker run -p 8501:8501 leisureauf1/a3-multi-agent-system:latest
```

---

## Checksums

```
## Linux
SHA256: d0d8b88e21d312eae0717250e434a06f1a47c6d18b3102c6d40c13b6eb03b2a5  A3-Agent-v7.1.0-linux-x64.tar.gz

## Windows (placeholder — build from source)
# SHA256 will be added after Windows build completes
```

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for full release history from v6.x to v7.1.0.

## Documentation

- [Installation Guide](docs/INSTALL.md)
- [User Guide](docs/USER_GUIDE.md)
- [Architecture](docs/competition/architecture.md)
- [Agent Design](docs/competition/agent-design.md)
- [Demo Script](docs/competition/demo-script.md)

---

## Contributors

Built by [Leisure-Auf1](https://github.com/Leisure-Auf1) on [Veritas-Core](https://github.com/Leisure-Auf1/Veritas-Core).
