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

### 🪟 Windows

1. Download `A3-Agent-v7.1.0-win64.zip` from [GitHub Releases](https://github.com/Leisure-Auf1/A3-Multi-Agent-System/releases)
2. Extract to any folder (Desktop, Documents, etc.)
3. Double-click `A3-Agent.exe`
4. Browser opens automatically → `http://127.0.0.1:8501`

**Requirements**: None. No Python, no dependencies.

#### Uninstall
Delete the extracted folder. User data at `%APPDATA%\A3-Agent\` can also be deleted.

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

Or build from source:
```bash
git clone https://github.com/Leisure-Auf1/A3-Multi-Agent-System.git
cd A3-Multi-Agent-System
pip install -r requirements.txt
pip install pyinstaller
desktop/build.bat  # (use WSL or adapt for Linux: colon separators)
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
