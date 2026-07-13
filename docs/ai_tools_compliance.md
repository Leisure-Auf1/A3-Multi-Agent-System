# Xunfei AI Competition Compliance

> A3 Multi-Agent System — 讯飞星火 AI 竞赛合规文档
> Phase 11 | v2.8

---

## 1. Overview

This document demonstrates A3's compliance with the Xunfei (讯飞) Spark AI Competition requirements. The system integrates Xunfei Spark Model API as a core inference engine and follows competition technical specifications.

---

## 2. Xunfei Spark Model API Integration

### Architecture

```
A3 Multi-Agent System
        │
        ▼
┌──────────────────────────────────────┐
│           AgentRouter                 │
│  (Dual-Engine Target Routing)         │
│                                       │
│  Frontend Agents → Xunfei Spark       │
│  Backend Agents  → DeepSeek Core      │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│      XunfeiSparkProvider              │
│  (src/llm/xunfei_provider.py)         │
│                                       │
│  • OpenAI-compatible chat endpoint    │
│  • Model: spark-pro / spark-max       │
│  • System prompt injection            │
│  • Token usage tracking               │
│  • Error handling + fallback          │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│   Xunfei Spark API                    │
│   https://spark-api.xf-yun.com/v1    │
│   /chat/completions                   │
└──────────────────────────────────────┘
```

### Supported Models

| Model | Max Tokens | Use Case |
|:------|:-----------|:---------|
| **spark-lite** | 4,096 | Lightweight, fast responses |
| **spark-pro** | 8,192 | Balanced performance (default) |
| **spark-max** | 32,768 | Complex reasoning tasks |
| **spark-4.0-ultra** | 32,768 | Latest generation, best quality |

### Configuration

```bash
# Environment variables
export XF_SPARK_API_KEY="your-api-key"
export XF_SPARK_BASE_URL="https://spark-api.xf-yun.com/v1"
```

```python
# Programmatic configuration
from src.llm.xunfei_provider import XunfeiSparkProvider

provider = XunfeiSparkProvider(
    api_key="your-api-key",
    model="spark-pro",
)

response = provider.generate(
    prompt="Explain AI in Chinese.",
    system_prompt="You are an AI education assistant.",
    temperature=0.7,
    max_tokens=500,
)
```

---

## 3. Agent Routing — Frontend Compliance

### Frontend Agents (Spark-powered)

Per competition requirements, user-facing agents use Xunfei Spark:

| Agent | Role | Why Spark? |
|:------|:-----|:-----------|
| **ContentAgent** | Generate teaching content | Student-facing, requires safe/accurate output |
| **ProfileAgent** | Extract student profiles | Student-facing, privacy-sensitive |
| **OnboardingAgent** | Welcome and orientation | First interaction, sets trust |

### DynamicProfile Injection

Spark receives personalized system prompts based on student profiles:

```python
# DynamicProfile → System Prompt
profile = DynamicProfile(
    cognitive_style="visual_dominant",
    learning_pace="fast_track",
)
hint = profile.to_system_prompt_hint()
# → "该学生是视觉主导型——请大量使用 ASCII 字符画、
#    Mermaid 拓扑图和代码对比块。\n学习节奏极快——跳过冗余铺垫。"
```

This ensures Spark generates content that matches each student's learning style.

---

## 4. Competition Requirement Mapping

### 4.1 Multi-Agent Collaboration ✅
- 10 specialized agents with distinct roles
- EventBus-based inter-agent communication
- Shared Memory system (StudentMemory + ExperienceMemory)
- Dashboard shows agent topology and interaction timeline

### 4.2 LLM-Driven Intelligence ✅
- Dual-engine architecture: Xunfei Spark (frontend) + DeepSeek (backend)
- LLMProvider abstraction layer for provider-agnostic development
- MockLLMProvider for deterministic testing

### 4.3 Personalized Learning ✅
- 6-dimension student profiles from natural language
- Personalized learning paths (PlannerAgent, 3 courses)
- Mastery-based resource recommendation (EMA α=0.5)

### 4.4 Educational Content Generation ✅
- 5-asset content generation (tutorial, mindmap, quiz, extended, sandbox)
- ResourceGenerationAgent with 5 sub-generators
- Multimodal resource cards (document/mindmap/video/code)

### 4.5 Quality Assurance ✅
- ReviewGate 3-layer validation (AST + Pytest + Judge)
- AgentEvaluator 4-dimension scoring
- ImprovementLoop for continuous self-improvement

### 4.6 Knowledge Base ✅
- Structured course knowledge base (6 chapters)
- `resources.json` and `exercises.json` for structured metadata
- Anti-hallucination grounding against knowledge base

---

## 5. Technical Compliance Checklist

| Requirement | Implementation | File |
|:------------|:---------------|:-----|
| LLM API integration | XunfeiSparkProvider | `src/llm/xunfei_provider.py` |
| OpenAI-compatible endpoint | `/v1/chat/completions` | — |
| System prompt support | `generate(system_prompt=...)` | `src/llm/provider.py` |
| Token usage tracking | `LLMResponse.usage` | `src/llm/provider.py` |
| Error handling | HTTP error + timeout handling | `src/llm/xunfei_provider.py` |
| Model catalog | `SPARK_MODELS` dict | `src/llm/xunfei_provider.py` |
| Environment config | `XF_SPARK_API_KEY` env var | `src/llm/xunfei_provider.py` |
| Frontend routing | `AgentRouter.FRONTEND_AGENTS` | `src/core/agent_router.py` |
| Profile injection | `DynamicProfile.to_system_prompt_hint()` | `src/core/agent_router.py` |
| CLI demo | `python -m src.llm.xunfei_provider` | `src/llm/xunfei_provider.py` |

---

## 6. Fallback and Resilience

### Graceful Degradation

If Xunfei Spark is unavailable:

1. **Detection**: `XF_SPARK_API_KEY` not set or API returns error
2. **Fallback**: Backend agents can handle frontend requests via DeepSeek
3. **Notification**: Error logged to EventBus, visible in Dashboard Trace panel
4. **Recovery**: Automatic retry on next request (no persistent failure state)

```python
# Example: graceful fallback in AgentRouter
if not self.xf_spark_api_key:
    # Log warning, route to backend
    self.bus.emit(agent="AgentRouter", action="spark_unavailable",
                  status="warning")
    return self._dispatch_to_core(payload)
```

### Rate Limiting (Future)

Not yet implemented but designed for:

- Token-based quota per student session
- Exponential backoff on 429 responses
- Provider pool with failover (Spark → DeepSeek → Mock)

---

## 7. Competition Demo Flow

### Integration with Demo Story

The Xunfei Spark integration is demonstrated in Scene 2 of `docs/demo_story.md`:

```
Scene 2: AI-Powered Teaching Generation
├─ ContentAgent (Spark) generates personalized lecture notes
├─ ProfileAgent (Spark) extracts 6-dim student profile
├─ System prompt injection with DynamicProfile
└─ Dashboard shows Spark model usage in Agent Trace panel
```

---

## 8. Future Enhancements

| Feature | Description | Timeline |
|:--------|:------------|:---------|
| Streaming via Spark | SSE-based token streaming for real-time UX | v2.9 |
| Spark multi-modal | Image generation + understanding via Spark 4.0 | v3.0 |
| Spark fine-tuning | Custom fine-tuned Spark model for education domain | Future |
| Quota management | Per-student token budget with Spark | Future |

---

## 9. Verification

Run the compliance check:

```bash
# Verify Xunfei provider imports
python -c "from src.llm.xunfei_provider import XunfeiSparkProvider; print('OK')"

# List available Spark models
python -c "from src.llm.xunfei_provider import SPARK_MODELS; print(SPARK_MODELS)"

# Run provider CLI demo (requires API key)
python -m src.llm.xunfei_provider

# Run full test suite
python -m pytest tests/ -q
```

---

*Part of A3 Competition Documentation — v2.8*
*Xunfei Spark Model API: https://www.xfyun.cn/doc/spark/*
