# Xunfei Spark Integration — Production Readiness Analysis

> Phase 12 | A3 v2.8 → v2.9
> Date: 2026-07-13

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────┐
│              A3 Agent Layer                       │
│                                                   │
│  ProfileAgent  ContentAgent  ResourceGenAgent     │
│       │              │              │             │
│       └──────────────┼──────────────┘             │
│                      │                            │
│              ┌───────┴───────┐                    │
│              │ LLMAgentAdapter│                    │
│              │ (provider=?)   │                    │
│              └───────┬───────┘                    │
│                      │                            │
├──────────────────────┼────────────────────────────┤
│              Provider Interface                   │
│                      │                            │
│         ┌────────────┼────────────┐               │
│         ▼            ▼            ▼               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │  Mock    │ │ Xunfei  │ │ Future:  │          │
│  │ Provider │ │  Spark  │ │ DeepSeek │          │
│  └──────────┘ └──────────┘ └──────────┘          │
│                                                   │
│  All implement: LLMProvider.generate(prompt)      │
└──────────────────────────────────────────────────┘
```

**Key insight:** Agents never know which provider they're using. The adapter handles it.

---

## 2. XunfeiSparkProvider — Production Readiness

### 2.1 What's Ready ✅

| Component | Status | Evidence |
|:----------|:------:|:---------|
| OpenAI-compatible `/chat/completions` | ✅ | `xunfei_provider.py:124` |
| Model catalog (4 models) | ✅ | `SPARK_MODELS` dict |
| System prompt injection | ✅ | `generate(system_prompt=...)` |
| Token usage tracking | ✅ | `LLMResponse.usage` |
| Error handling (HTTP + timeout) | ✅ | `_call_api()` try/except |
| Graceful degradation | ✅ | Returns `LLMResponse(error=...)` on failure |
| `is_available` check | ✅ | Checks `api_key` presence |
| CLI demo | ✅ | `python -m src.llm.xunfei_provider` |

### 2.2 What's Missing ⚠️

| Gap | Impact | Mitigation |
|:----|:-------|:-----------|
| **No real API key testing** | Medium | Provider works against OpenAI-compatible spec; tested with mock |
| **No streaming** | Low | `LLMProvider.generate_stream()` abstract method exists |
| **No rate limiting** | Low | Competition demo volume is negligible |
| **No auth refresh** | Low | API keys are long-lived |

### 2.3 Production Readiness Assessment

**Verdict:** 🟡 **Demo-ready but not production-hardened.**

The provider correctly implements the OpenAI chat completions protocol. Since Xunfei Spark's API is OpenAI-compatible, the implementation should work with a real API key. The `urllib`-based HTTP client is adequate for competition use (single-threaded, low volume).

**Recommendation for competition:**
- Pre-test with real Spark API key before demo day
- Keep `MockLLMProvider` as fallback in case of network issues
- Use `spark-pro` model for balance of speed and quality

---

## 3. Configuration

### 3.1 Environment Variables

```bash
# Required
export XF_SPARK_API_KEY="your-xunfei-spark-api-key"

# Optional (default shown)
export XF_SPARK_BASE_URL="https://spark-api.xf-yun.com/v1"
```

### 3.2 Programmatic Configuration

```python
from src.llm.xunfei_provider import XunfeiSparkProvider

# Option A: Environment variables (recommended for competition)
provider = XunfeiSparkProvider(model="spark-pro")

# Option B: Explicit constructor
provider = XunfeiSparkProvider(
    api_key="your-key-here",
    base_url="https://spark-api.xf-yun.com/v1",
    model="spark-max",
)
```

### 3.3 Model Selection

| Model | Best For | Competition Use |
|:------|:---------|:----------------|
| `spark-lite` | Fast simple responses | OnboardingAgent welcome message |
| `spark-pro` | **Default choice** | ProfileAgent, ContentAgent |
| `spark-max` | Complex reasoning | Planning, evaluation |
| `spark-4.0-ultra` | Best quality | Not needed for demo |

---

## 4. Provider Switching Without Code Changes

### 4.1 The Adapter Pattern

The `LLMAgentAdapter` accepts any `LLMProvider`. Agents never construct providers directly:

```python
# Development / testing
from src.llm.mock_provider import MockLLMProvider
adapter = LLMAgentAdapter(provider=MockLLMProvider())

# Competition / production
from src.llm.xunfei_provider import XunfeiSparkProvider
adapter = LLMAgentAdapter(provider=XunfeiSparkProvider())
```

### 4.2 Switching at Startup

```python
import os
from src.llm.mock_provider import MockLLMProvider
from src.llm.xunfei_provider import XunfeiSparkProvider
from src.core.llm_agent_adapter import LLMAgentAdapter

def create_provider():
    """Select provider based on environment."""
    if os.getenv("XF_SPARK_API_KEY"):
        return XunfeiSparkProvider()
    return MockLLMProvider()

adapter = LLMAgentAdapter(provider=create_provider())
```

### 4.3 The Dashboard Config Pattern

In `web/chat_demo.py` (already implemented):

```python
use_llm = st.checkbox("Use LLM (Mock Provider)", value=True)
if use_llm:
    provider = MockLLMProvider()
else:
    provider = None  # Falls back to rule mode
```

**Extend for competition:**

```python
llm_mode = st.selectbox("LLM Mode", ["Mock", "Spark", "Off"])
if llm_mode == "Spark":
    provider = XunfeiSparkProvider()
elif llm_mode == "Mock":
    provider = MockLLMProvider()
else:
    provider = None  # Pure rule mode
```

---

## 5. Fallback Strategy

### 5.1 Automatic Fallback Layers

```
1. Try XunfeiSparkProvider.generate()
       │
       ▼ Fail?
2. Auto-fallback via LLMAgentAdapter → rule_fn()
       │
       ▼ Fail?
3. ProfileAgent.extract() — deterministic keywords
       │
       ▼
4. PlannerAgent.DEFAULT_KNOWLEDGE_GRAPH — hardcoded graph
```

### 5.2 Reliability Guarantees

| Scenario | Behavior | User Impact |
|:---------|:---------|:------------|
| No API key | Auto-fallback to rule mode | Slightly less nuanced profile |
| Network timeout | Auto-fallback to rule mode | Same as above |
| API error (4xx/5xx) | Auto-fallback to rule mode | Same as above |
| JSON parse error | Auto-fallback to rule mode | Same as above |
| All layers fail | Returns empty profile + error log | Graceful degradation |

### 5.3 Monitoring

`LLMAgentAdapter.stats` tracks:
- `total_calls` / `llm_calls` / `rule_fallbacks` / `errors`
- `fallback_rate` — percentage of calls that fell back
- `avg_latency_ms` — LLM response time

These can be shown in the Dashboard to demonstrate reliability.

---

## 6. Competition Demo Recommendations

### 6.1 Recommended Setup

```bash
# 1. Set API key
export XF_SPARK_API_KEY="your-competition-key"

# 2. Launch dashboard with Spark
streamlit run web/chat_demo.py

# 3. Demo flow:
#    - Show LLM mode toggle (Mock vs Spark)
#    - Run pipeline with Spark → show real AI output
#    - Show fallback toggle → demonstrate resilience
```

### 6.2 Demo Script Talking Points

> **Slide:** "A3 integrates Xunfei Spark as the primary inference engine."
> - "4 Spark models from Lite to 4.0 Ultra"
> - "OpenAI-compatible API — industry standard protocol"
> - "Automatic fallback to rule engine — never breaks"

> **Slide:** "Provider switching requires zero code changes."
> - "LLMProvider interface abstracts the backend"
> - "Mock → Spark in one line of configuration"
> - "Same agents, same prompts, different backends"

> **Slide:** "Safety through fallback architecture."
> - "Spark unavailable → rule engine takes over"
> - "All failures logged to EventBus for observability"
> - "Students never see a broken system"

### 6.3 Risk Mitigation

| Risk | Backup Plan |
|:-----|:------------|
| Spark API down | Demo with MockProvider + explain fallback architecture |
| API key expired | Pre-verify key 24h before; have backup key |
| Slow response | Use `spark-lite` for demo; explain model selection |
| Network issues | Pre-load demo data; run fully offline with MockProvider |

---

## 7. Quick Reference

### Files

| File | Purpose |
|:-----|:--------|
| `src/llm/provider.py` | `LLMProvider` abstract interface |
| `src/llm/xunfei_provider.py` | Spark API client |
| `src/llm/mock_provider.py` | Deterministic test provider |
| `src/core/llm_agent_adapter.py` | Provider-agnostic agent wrapper |
| `docs/ai_tools_compliance.md` | Xunfei competition compliance doc |

### Commands

```bash
# Test Spark provider (offline — shows model catalog)
python -m src.llm.xunfei_provider

# Test Spark with real API
XF_SPARK_API_KEY="your-key" python -m src.llm.xunfei_provider

# Test LLM adapter
python -m src.core.llm_agent_adapter

# Launch chat demo
streamlit run web/chat_demo.py
```
