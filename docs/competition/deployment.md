# Competition Deployment Guide

A3 v7.1.0 deploys directly from GitHub — no packaging, no .exe, no Docker.

## ⚡ Fastest: Streamlit Community Cloud (Free)

1. Push to GitHub (done)
2. Go to https://share.streamlit.io
3. Click "New app" → select `Leisure-Auf1/A3-Multi-Agent-System`
4. Main file path: `app.py`
5. Click "Deploy!"

**Result**: Public URL like `https://a3-multi-agent-system.streamlit.app`

No Python, no API keys, no configuration needed. Works immediately with mock providers.

## 🔄 Alternative: Render (Free)

1. Go to https://dashboard.render.com
2. "New" → "Blueprint"
3. Connect `Leisure-Auf1/A3-Multi-Agent-System`
4. Render auto-detects `render.yaml`

**Result**: `https://a3-multi-agent-system.onrender.com`

Cold start: ~30-60s after idle. Service stays warm for demo sessions.

## 🐳 Docker (optional, for offline demos)

```bash
docker pull leisureauf1/a3-multi-agent-system:latest
docker run -p 8501:8501 leisureauf1/a3-multi-agent-system:latest
```

## 💻 Local (development)

```bash
git clone https://github.com/Leisure-Auf1/A3-Multi-Agent-System.git
cd A3-Multi-Agent-System
pip install -r requirements.txt
streamlit run app.py
```

## 🏆 Competition Demo

For competitions, use **Streamlit Cloud** — share a URL, zero setup:

1. Deploy on Streamlit Cloud (2 clicks)
2. Open the app → "🏆 比赛演示" tab
3. Click "运行完整 Pipeline"
4. Present from any device with a browser

No Python installation. No API keys. No network dependencies (mock mode works offline in browser).

## Provider Configuration (optional)

To use real AI models during demos:

1. Open "⚙️ AI模型设置" tab
2. Select provider (DeepSeek/OpenAI/Spark)
3. Enter API key → Test → Save
4. Pipeline now uses real LLM

API keys are stored in-browser (Streamlit session) and in the OS keyring (local mode). Never committed to git.
