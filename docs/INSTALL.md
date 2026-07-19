# A3-Agent v7.1.0 — Installation Guide

## Quick Install

### 🌐 Browser (zero install, free)

Visit: `https://a3-agent.streamlit.app`

Deploy your own in 2 clicks on [Streamlit Cloud](https://share.streamlit.io).

No download. No Python. No API key.

---

### 🐳 Docker

```bash
docker pull leisureauf1/a3-multi-agent-system:latest
docker run -p 8501:8501 leisureauf1/a3-multi-agent-system:latest
# → http://localhost:8501
```

---

### 🪟 Windows (Desktop App)

**Requirements**: None. No Python, no dependencies. Single-file double-click launch.

#### Quick Start

1. Download `A3-Agent-v7.1.0-win64.zip` from [GitHub Releases](https://github.com/Leisure-Auf1/A3-Multi-Agent-System/releases/tag/v7.1.0)
2. Extract to any folder (e.g., Desktop or `C:\A3-Agent`)
3. Double-click `A3-Agent.exe`
4. The launcher initializes in 5 stages:
   ```
   [1/5] Initializing user data...
   [2/5] Starting AI Backend (FastAPI)...
   [3/5] Waiting for API health check...
   [4/5] Starting Learning Interface (Streamlit)...
   [5/5] Opening browser → http://127.0.0.1:8501
   ```
5. Browser opens automatically — configure your AI provider or try Demo Mode

#### What's Included

| Component | Description |
|:----------|:------------|
| `A3-Agent.exe` | Main launcher (double-click to start) |
| `_internal/` | Bundled Python runtime, all dependencies, source code |
| `LICENSE` | MIT License |
| `README.txt` | Quick reference guide |
| `VERSION` | Version identifier (v7.1.0) |

#### First Launch Wizard

On first run, you'll see the **Welcome Page**:
1. **Demo Mode** — Click "🎭 先体验 Demo" to explore A3 offline (no API key needed)
2. **Configure Provider** — Click "🚀 开始配置" to set up DeepSeek, OpenAI, or Spark

API keys are stored securely in **Windows Credential Manager** (not plaintext files).

#### Where Is My Data?

| Path | Contents |
|:-----|:---------|
| `%APPDATA%\A3-Agent\config\` | LLM configuration (`llm.json`) |
| `%APPDATA%\A3-Agent\storage\` | Learning database (`a3.db`) |
| `%APPDATA%\A3-Agent\logs\` | Launcher and service logs |

To reset the app: delete `%APPDATA%\A3-Agent\` and restart.

#### Uninstall

1. Delete the extracted folder
2. (Optional) Delete `%APPDATA%\A3-Agent\` to remove all user data

#### Windows-Specific Troubleshooting

| Problem | Solution |
|:--------|:---------|
| Windows Defender blocks | Click "More info" → "Run anyway" |
| Port 8501 already in use | Close other instances, or run: `netstat -ano \| findstr :8501` then `taskkill /PID <pid> /F` |
| Port 8000 already in use | Same as above, replace 8501 with 8000 |
| Browser doesn't open | Manually navigate to http://127.0.0.1:8501 |
| Launcher window closes immediately | Check `%APPDATA%\A3-Agent\logs\launcher.log` for errors |

---

### 🐧 Linux

1. Download `A3-Agent-v7.1.0-linux-x64.tar.gz`
2. Extract and run:
   ```bash
   tar xzf A3-Agent-v7.1.0-linux-x64.tar.gz
   cd A3-Agent-v7.1.0-linux-x64
   ./A3-Agent
   ```
3. Browser opens → `http://127.0.0.1:8501`

Or build from source (Linux/WSL):
```bash
git clone https://github.com/Leisure-Auf1/A3-Multi-Agent-System.git
cd A3-Multi-Agent-System
pip install -r requirements.txt
pip install pyinstaller
# Linux build:
pyinstaller --onedir --name A3-Agent --clean --noconfirm \
  --add-data "app.py:." \
  --add-data "src:src" \
  --add-data "web:web" \
  --add-data "utils:utils" \
  --add-data "knowledge_base:knowledge_base" \
  --add-data "storage/a3.db:storage" \
  --add-data "demo/fixtures:demo/fixtures" \
  --add-data ".streamlit/config.toml:.streamlit" \
  --add-data ".env.example:." \
  --add-data "LICENSE:." \
  --hidden-import fastapi --hidden-import uvicorn --hidden-import streamlit \
  --hidden-import veritas --hidden-import veritas.llm --hidden-import veritas.llm.factory \
  --hidden-import keyring --collect-all fastapi --collect-all uvicorn --collect-all streamlit \
  --collect-all veritas --runtime-hook desktop/hooks/runtime_hook.py \
  desktop/launcher.py
```

Or build on Windows:
```batch
# Install dependencies
pip install -r requirements.txt
pip install pyinstaller

# Build (one command)
desktop\build.bat
```

---

### 🍎 macOS

Build from source (same as Linux) or use Docker. Native .app coming in future release.

---

## First Launch

On first run, you'll see the **Welcome Page**:

1. Choose your AI provider (DeepSeek, OpenAI, Spark) or "Demo Mode"
2. If using a real provider: enter API key → Test → Save
3. Start learning!

**Demo Mode** works offline with no API key — perfect for trying A3 before configuring.

---

## Provider Setup

| Provider | Where to get API key |
|:---------|:---------------------|
| DeepSeek | https://platform.deepseek.com/api_keys |
| OpenAI | https://platform.openai.com/api-keys |
| Spark | https://console.xfyun.cn/app/myapp |

API keys are stored securely in your OS credential store (Windows Credential Manager, Linux Secret Service, macOS Keychain).

---

## Troubleshooting

| Problem | Solution |
|:--------|:---------|
| Port 8501 in use | Close other instances, or kill: `lsof -ti:8501 | xargs kill` |
| Port 8000 in use | Same: `lsof -ti:8000 | xargs kill` |
| Browser doesn't open | Manually navigate to http://127.0.0.1:8501 |
| "API Key invalid" | Check key at provider dashboard, re-enter |
| Streamlit blank page | Wait 5s for startup, refresh browser |
| Windows Defender blocks | Click "More info" → "Run anyway" |
