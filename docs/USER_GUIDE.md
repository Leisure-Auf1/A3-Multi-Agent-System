# A3-Agent v7.1.0 — User Guide

## Overview

A3 is a multi-agent AI learning system. Describe what you want to learn in natural language, and a team of 12 AI agents generates personalized learning paths, resources, and evaluations.

---

## Tabs

| Tab | Purpose |
|:----|:--------|
| 🏠 **学习助手** | Enter learning goals, run the agent pipeline |
| 👤 **学习画像** | View your 6-dimension student profile |
| 📚 **学习空间** | Learning path + recommended resources |
| ⚙️ **AI模型设置** | Configure AI provider and API key |
| 🏆 **比赛演示** | One-click competition demo (no API key) |
| 🎯 **仪表盘** | Agent timeline, evaluation scores, confidence |
| 🏗️ **架构概览** | System architecture diagram |

---

## Basic Workflow

### 1. Describe your learning goal

Go to 🏠 **学习助手**, type something like:

> "I'm a sophomore CS student. I know basic Python and want to learn Multi-Agent AI development. I prefer visual learning and hands-on coding."

### 2. Run the pipeline

Click **🚀 开始分析**. A3's agents will:
- Extract your learning profile (6 dimensions)
- Generate a personalized learning path
- Recommend resources matched to your style
- Evaluate the quality of the plan

### 3. Explore results

- **👤 学习画像**: See your cognitive style, knowledge level, learning pace
- **📚 学习空间**: Browse your learning path and resources
- **🎯 仪表盘**: View agent execution timeline and quality metrics

---

## Competition Demo

For demonstrations without an API key:

1. Click 🏆 **比赛演示**
2. Click **🚀 运行完整 Pipeline**
3. All 6 agents execute using mock providers (~500ms)
4. Switch to 🎯 **仪表盘** to see metrics
5. Switch to 🏗️ **架构概览** to see the system design

---

## Provider Configuration

### Using a Real AI Model

1. Go to ⚙️ **AI模型设置**
2. Select a provider (DeepSeek recommended for Chinese)
3. Enter your API key
4. Click **🔍 测试连接** to verify
5. Click **💾 保存配置**

Now return to 🏠 学习助手 — the pipeline will use real AI.

### Available Providers

| Provider | Best For |
|:---------|:---------|
| 🌊 DeepSeek | High value, strong Chinese capability |
| 🤖 OpenAI | Global SOTA, English-primary |
| 🚀 Spark | China-compliant, domestic |
| 🎭 Mock | Offline demo, no API key needed |

---

## Keyboard Shortcuts

| Shortcut | Action |
|:---------|:--------|
| `Ctrl+C` | Stop A3-Agent (in terminal) |
| `F5` | Refresh Streamlit page |

---

## Data & Privacy

- **API keys**: Stored in OS credential store (not plaintext)
- **Learning data**: Stored locally in SQLite (`~/.a3-agent/storage/a3.db`)
- **No telemetry**: A3 does not send usage data anywhere
- **Offline capable**: Mock mode works without internet

---

## Support

- **Issues**: https://github.com/Leisure-Auf1/A3-Multi-Agent-System/issues
- **Docs**: https://github.com/Leisure-Auf1/A3-Multi-Agent-System/tree/main/docs
