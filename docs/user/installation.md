# Installation Guide

---

## System Requirements

| Requirement | Minimum |
|:-----------|:--------|
| **Python** | 3.10+ |
| **OS** | Windows 10+, Linux (x86_64), macOS (via Docker) |
| **RAM** | 2 GB |
| **Disk** | 500 MB |
| **Network** | Optional (required for LLM providers, Docker pull) |

---

## Windows

### Desktop App (recommended)

1. Download from [GitHub Releases](https://github.com/Leisure-Auf1/A3-Multi-Agent-System/releases):
   ```
   A3-Agent-v7.1.1-win64.zip (~55 MB)
   ```
2. Extract the ZIP anywhere
3. Double-click `A3-Agent.exe`
4. Browser opens automatically at `http://localhost:8501`

> **First run**: The app seeds a fresh SQLite database and creates `%APPDATA%/A3-Agent/storage/`.

### From Source

```powershell
git clone https://github.com/Leisure-Auf1/A3-Multi-Agent-System.git
cd A3-Multi-Agent-System
pip install -r requirements.txt
streamlit run web/app.py
```

---

## Linux

### Desktop App

```bash
curl -LO https://github.com/Leisure-Auf1/A3-Multi-Agent-System/releases/latest/download/A3-Agent-linux-x64.tar.gz
tar xzf A3-Agent-linux-x64.tar.gz
cd A3-Agent-linux-x64
./A3-Agent
```

### From Source

```bash
git clone https://github.com/Leisure-Auf1/A3-Multi-Agent-System.git
cd A3-Multi-Agent-System
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
streamlit run web/app.py
```

---

## Docker

```bash
docker pull leisureauf1/a3-multi-agent-system:latest
docker run -p 8501:8501 -p 8000:8000 leisureauf1/a3-multi-agent-system:latest
```

Open `http://localhost:8501` in your browser.

### Persistent Data

```bash
docker run -p 8501:8501 -p 8000:8000 \
  -v ~/.a3-agent:/root/.a3-agent \
  leisureauf1/a3-multi-agent-system:latest
```

---

## LLM Provider Setup

A3 works in **demo mode** without any API key. For AI-powered content, configure a provider:

### DeepSeek

1. Get an API key at [platform.deepseek.com](https://platform.deepseek.com/api_keys)
2. In A3 Settings: select **DeepSeek**, enter key, choose model (`deepseek-chat`)

### OpenAI

1. Get an API key at [platform.openai.com](https://platform.openai.com/api-keys)
2. In A3 Settings: select **OpenAI**, enter key, choose model (`gpt-4o-mini`)

### Spark (讯飞星火)

1. Get credentials at [console.xfyun.cn](https://console.xfyun.cn/app/myapp)
2. In A3 Settings: select **Spark**, enter credentials

---

## Verification

After installation, verify everything works:

1. Open the app
2. Register a test account
3. Run a learning task: `"I want to learn Python basics"`
4. Check the History tab — a run record should appear

Or via API:

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```
