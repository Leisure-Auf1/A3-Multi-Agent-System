# Phase 13 — Xunfei Spark Live Provider Switch Plan

> Architecture and implementation plan for production Xunfei Spark integration
> Date: 2026-07-13 | A3 v2.8 → v2.9

---

## 1. Architecture

```
┌──────────────────────────────────────────────────────┐
│                   Agent Layer                         │
│                                                       │
│  ProfileAgent  PlannerAgent  ContentAgent  ...        │
│       │              │              │                 │
│       └──────────────┼──────────────┘                 │
│                      │                                │
│              ┌───────┴───────┐                        │
│              │ LLMAgentAdapter│  (src/core/)           │
│              │ provider=???   │                        │
│              └───────┬───────┘                        │
│                      │                                │
├──────────────────────┼────────────────────────────────┤
│              Provider Layer                            │
│                      │                                │
│         ┌────────────┼────────────┐                   │
│         ▼            ▼            ▼                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐              │
│  │  Mock    │ │ Xunfei  │ │ Future   │              │
│  │ Provider │ │  Spark  │ │ Provider │              │
│  └──────────┘ └──────────┘ └──────────┘              │
│                                                       │
│  All implement: LLMProvider.generate(prompt, ...)     │
└──────────────────────────────────────────────────────┘
```

**Key invariant:** Agents never know which provider is active. They call the adapter, which calls the provider, which either reaches Spark or falls back to rules.

---

## 2. Production Configuration

### 2.1 Environment Variables

```bash
# Required for Spark
export XF_SPARK_API_KEY="your-xunfei-api-key"

# Optional (defaults shown)
export XF_SPARK_BASE_URL="https://spark-api.xf-yun.com/v1"
export XF_SPARK_MODEL="spark-pro"          # spark-lite | spark-pro | spark-max | spark-4.0-ultra
export LLM_PROVIDER="xunfei"               # xunfei | mock | none
```

### 2.2 Provider Factory

```python
# Proposed: src/core/provider_factory.py (~30 lines)
import os
from src.llm.provider import LLMProvider
from src.llm.mock_provider import MockLLMProvider
from src.llm.xunfei_provider import XunfeiSparkProvider

def create_provider() -> LLMProvider:
    """Factory: select provider based on LLM_PROVIDER env var."""
    mode = os.getenv("LLM_PROVIDER", "mock")

    if mode == "xunfei":
        return XunfeiSparkProvider(
            api_key=os.getenv("XF_SPARK_API_KEY", ""),
            model=os.getenv("XF_SPARK_MODEL", "spark-pro"),
        )
    elif mode == "mock":
        provider = MockLLMProvider()
        _seed_mock_responses(provider)
        return provider
    else:
        return None  # Pure rule mode

def _seed_mock_responses(provider: MockLLMProvider):
    """Pre-seed mock with realistic competition demo responses."""
    import json
    provider.add_response("画像分析", json.dumps({
        "knowledge_base": "mid_level",
        "cognitive_style": "visual_dominant",
        "error_prone_bias": "magic_syntax_blind",
        "learning_pace": "fast_track",
        "interaction_preference": "code_sandbox",
        "frustration_threshold": "medium",
        "reasoning": "学生有编程基础，偏好视觉化学习。"
    }, ensure_ascii=False))
```

### 2.3 Model Selection

| Model | Max Tokens | Demo Use | Competition Recommendation |
|:------|:-----------|:---------|:---------------------------|
| `spark-lite` | 4,096 | Fast onboarding messages | Not recommended (limited quality) |
| `spark-pro` | 8,192 | **Default** | ✅ Best balance for demo |
| `spark-max` | 32,768 | Complex planning tasks | Overkill for 5-min demo |
| `spark-4.0-ultra` | 32,768 | Best quality | Reserve for final presentation |

---

## 3. Zero Agent-Code Modification

### 3.1 How It Works

Agents use `LLMAgentAdapter`. The adapter accepts any `LLMProvider`. Switching is purely configuration:

```python
# Before (mock mode):
adapter = LLMAgentAdapter(provider=MockLLMProvider())

# After (Spark mode):
adapter = LLMAgentAdapter(provider=create_provider())  # Reads LLM_PROVIDER env var

# Agent code is IDENTICAL:
result = adapter.call_json(
    agent_name="ProfileAgent",
    prompt_template=pa.LLM_PROMPT_TEMPLATE,
    input_vars={"student_text": text, "history_context": ""},
    rule_fn=lambda: pa.extract(text),
)
```

### 3.2 Files That Change

| File | Change | Lines |
|:-----|:-------|:------|
| `src/core/provider_factory.py` | **NEW** — factory function | 30 |
| `web/chat_demo.py` | Add Spark option to sidebar | 15 |
| `web/app_v2.py` | Optional: provider selector in sidebar | 10 |
| `src/core/llm_agent_adapter.py` | No change | 0 |
| `src/agents/profile_agent.py` | No change | 0 |
| `src/agents/planner_agent.py` | No change | 0 |

**Total: ~55 lines of new/updated code.** Zero agent changes.

---

## 4. Fallback Strategy

### 4.1 Automatic Fallback Layers

```
1. LLMAgentAdapter tries XunfeiSparkProvider.generate()
       │
       ├─ API key missing? → fallback to rule
       ├─ Network timeout (>120s)? → fallback to rule
       ├─ HTTP error (4xx/5xx)? → fallback to rule
       ├─ JSON parse error? → fallback to rule
       └─ Success → return LLM result
```

### 4.2 Fallback Already Implemented

The `LLMAgentAdapter.call()` method already handles all failure cases:

```python
# Existing code in llm_agent_adapter.py (lines 134-207):
if not self.provider or not self.provider.is_available:
    return self._fallback_to_rule(...)

try:
    response = self.provider.generate(...)
except Exception as e:
    if self.fallback_enabled:
        return self._fallback_to_rule(...)
```

**No new code needed for fallback.**

---

## 5. Risk Analysis

### 5.1 API Failure

| Scenario | Probability | Impact | Mitigation |
|:---------|:----------:|:------:|:-----------|
| API key expired | Low | High | Verify 24h before; backup key |
| Network timeout | Medium | Medium | Auto-fallback to rule; explain gracefully |
| Rate limit hit | Very Low | Low | Demo volume is trivial |
| Spark API down | Low | High | Pre-loaded MockProvider backup |
| Model returns garbage | Low | Medium | `extract_with_provider()` validates JSON |

### 5.2 Offline Demo

If network is unavailable:

1. Set `LLM_PROVIDER=mock` (or leave unset — mock is default)
2. Pre-seeded MockLLMProvider returns realistic responses
3. Dashboard toggle shows "Demo Mode (Offline)"
4. Competition presentation: "Here's our Spark integration architecture. For reliability, we also have a fully offline demo mode."

### 5.3 Quota Management

Not needed for competition demo (single run, short duration). For production: implement token counter in `LLMAgentAdapter.stats`.

---

## 6. Configuration Examples

### 6.1 Competition Day

```bash
# Production Spark setup
export LLM_PROVIDER=xunfei
export XF_SPARK_API_KEY="sk-competition-key-here"
export XF_SPARK_MODEL=spark-pro

streamlit run web/chat_demo.py
```

### 6.2 Offline Development

```bash
# Mock mode (default)
export LLM_PROVIDER=mock
# No API key needed

streamlit run web/chat_demo.py
```

### 6.3 Pure Rule Mode

```bash
# No LLM at all
export LLM_PROVIDER=none

python -c "
from src.agents.profile_agent import ProfileAgent
result = ProfileAgent().extract('I am a visual learner')
print(result.source)  # 'rule'
"
```

---

## 7. Competition Demo Flow with Spark

```
Judge watches screen:

1. Sidebar: "LLM Provider: [Xunfei Spark ▼]"  ← selected
2. Student types: "I want to learn multi-agent AI..."
3. System shows: "🤖 ProfileAgent (Spark Pro) analyzing..."
4. Profile appears with confidence scores
5. "🗺️ PlannerAgent generating path from knowledge base..."
6. Learning path appears: 6 chapters, 180 minutes
7. "🎨 ResourceGenerationAgent creating 5 resource types..."
8. Resource cards appear with colored borders

Key moment: Toggle to "Mock" mode → same pipeline, different backend.
"This is the LLMProvider abstraction — switch backends without touching agent code."
```

---

## 8. Quick Reference

| What | Where |
|:-----|:------|
| Provider interface | `src/llm/provider.py` |
| Spark client | `src/llm/xunfei_provider.py` |
| Mock client | `src/llm/mock_provider.py` |
| Agent adapter | `src/core/llm_agent_adapter.py` |
| Factory (proposed) | `src/core/provider_factory.py` (NEW) |
| Chat demo | `web/chat_demo.py` |
| Integration doc | `docs/xunfei_integration.md` |
