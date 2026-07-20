# Phase 14.1 — LLM Capability Wiring Audit

**Date:** 2026-07-20  
**Auditor:** Hermes Agent (Read Only)  
**Method:** Full source trace of every agent, provider, and pipeline link  

---

## Executive Summary

**A3-Agent v1.0.0 has complete LLM support in every agent, but the wiring is severed at two points:**
1. **Role gate** in `src/api/v2/pipeline.py:96` blocks LLM for all normal users
2. **Provider factory** in `src/core/provider_factory.py:30` only builds 3 of 8 providers

All 7 agents have full dual-mode (LLM + rule fallback), all providers have complete classes, `create_provider()` correctly reads user config — but the signal never reaches the agents.

---

## Complete Call Chain

### Path 1: What The Code Says (When LLM Is Active)

```
User Input "我要学习Python基础"
  │
  ├─ web/app.py: _render_learning()
  │    └─ _execute_pipeline_with_progress()
  │         └─ api.run_pipeline(goal)
  │              └─ POST /api/v2/learning/run    ← src/api/v2/pipeline.py
  │
  ├── Auth: require_auth(user) → ✅ Pass
  ├── Token Budget: check_available(500) → ✅ Pass
  │
  ├── 🔴 GATE: role ∈ (PRO, TEACHER, ADMIN)?
  │    ├─ FREE/STUDENT → llm_provider = None     ← LLM BLOCKED
  │    └─ PRO/TEACHER/ADMIN → create_provider()
  │         │
  │         ├─ src/config/llm_config.load_llm_config()
  │         │    └─ Reads ~/.a3-agent/config/llm.json → LLMConfig
  │         │         provider: "deepseek"
  │         │         model: "deepseek-chat"
  │         │         api_key: "sk-..." (decrypted)
  │         │
  │         ├─ cfg.is_configured? → True (has key + non-mock)
  │         ├─ _build_from_config(cfg)
  │         │    ├─ deepseek  → DeepSeekProvider(api_key, model) ✅
  │         │    ├─ openai    → OpenAIProvider(api_key, model)   ✅
  │         │    ├─ spark     → XunfeiSparkProvider(api_key)     ✅
  │         │    └─ others    → None (falls to Veritas factory)   ⚠️
  │         │
  │         └─ provider.is_available → True → return provider ✅
  │
  ├── LearningPipelineService.run(user_id, goal, llm_provider)
  │    └─ A3Workflow(student_id, llm_provider=DeepSeekProvider)
  │         │
  │         ├─ profile_agent.set_llm_provider(llm_provider)   ← ALL agents receive it
  │         ├─ planner_agent.set_llm_provider(llm_provider)
  │         ├─ content_generator_agent.set_llm_provider(llm_provider)
  │         ├─ resource_agent.set_llm_provider(llm_provider)
  │         └─ reflection_agent.set_llm_provider(llm_provider)
  │
  └─ Agent Execution:
       │
       ├─ ProfileAgent.extract_with_provider(text)
       │    └─ llm.generate(prompt, system_prompt, temp, max_tokens)
       │         └─ DeepSeekProvider._openai_compatible_chat()
       │              └─ HTTP POST https://api.deepseek.com/v1/chat/completions
       │                   └─ 📡 REAL LLM CALL
       │
       ├─ PlannerAgent.plan(profile, goal, ...)
       │    └─ self._llm_provider.generate(prompt) → 📡 REAL LLM CALL
       │
       ├─ ContentGeneratorAgent.generate(plan, ...)
       │    └─ self._llm_provider.generate(prompt) → 📡 REAL LLM CALL
       │
       ├─ ResourceAgent.recommend(profile, goal, gaps)
       │    └─ self._llm_provider → 📡 REAL LLM CALL (enrichment)
       │
       ├─ EvaluationAgent.generate_quiz(topic)
       │    └─ self._llm → 📡 REAL LLM CALL (quiz generation)
       │         └─ Plus: analyze_wrong_answer() → 📡 REAL LLM CALL
       │
       └─ ReflectionAgent.reflect(goal, plan, resources, feedback)
            └─ self._llm_provider.generate(prompt) → 📡 REAL LLM CALL
```

### Path 2: Reality (What Actually Happens)

```
User Input "我要学习Python基础"
  │
  └─ POST /api/v2/learning/run   ← pipeline.py:65
       │
       ├── role = "free" (from registration)
       ├── "free" ∉ (PRO, TEACHER, ADMIN)
       ├── 🔴 llm_provider = None
       │
       └─ ALL AGENTS RUN RULE-ONLY:
            ├─ ProfileAgent.extract()           → keyword matching
            ├─ PlannerAgent.plan()              → static topic list
            ├─ ContentGeneratorAgent.generate() → template
            ├─ ResourceAgent.recommend()        → static catalog
            ├─ EvaluationAgent._rule_generate_quiz() → template
            └─ ReflectionAgent._generate_summary()   → template
```

---

## Agent-by-Agent LLM Audit

### ProfileAgent

| Attribute | Value |
|-----------|-------|
| **File** | `src/agents/profile_agent.py` |
| **LLM Method** | `extract_with_provider(text, provider)` |
| **Rule Fallback** | `extract(text)` — keyword→profile dimension mapping |
| **LLM Provider Set** | `set_llm_provider(provider)` → `self._llm_provider` |
| **Called By Workflow** | `_run_profile_agent()` line 351: `if self.llm_provider is not None: return self.profile_agent.extract_with_provider(user_goal)` |
| **LLM Prompt** | `LLM_PROMPT_TEMPLATE` — JSON extraction of 6 profile dimensions |
| **Fallback Condition** | `llm is None` → rule fallback; `response.success == False` → rule fallback |
| **Output Difference** | LLM: `source="llm"`, `confidence>0`; Rule: `source="rule"`, `confidence=0.0` |
| **Verdict** | ✅ **LLM-Ready** — Full prompt + JSON parsing + validation |

### PlannerAgent

| Attribute | Value |
|-----------|-------|
| **File** | `src/agents/planner_agent.py` |
| **LLM Method** | `plan()` line 597: `if self._llm_provider is not None:` → LLM path |
| **Rule Fallback** | Static knowledge graph → topic list → rule-based node generation |
| **LLM Provider Set** | `set_llm_provider(provider)` → `self._llm_provider` |
| **LLM Prompt** | Generates JSON plan with nodes, concepts, strategies |
| **Verdict** | ✅ **LLM-Ready** — Full LLM path with validation |

### ContentGeneratorAgent

| Attribute | Value |
|-----------|-------|
| **File** | `src/agents/content_generator_agent.py` |
| **LLM Method** | `generate()` — uses `self._llm_provider` for content creation |
| **Rule Fallback** | Template-based content generation |
| **Verdict** | ✅ **LLM-Ready** |

### ResourceAgent

| Attribute | Value |
|-----------|-------|
| **File** | `src/agents/resource_agent.py` |
| **LLM Method** | `recommend()` → `_enrich_with_llm()` for personalization |
| **Rule Fallback** | Static `RESOURCE_CATALOG` with 15 hardcoded resources (all networking-themed) |
| **LLM Provider Set** | `set_llm_provider(provider)` → `self._llm_provider` |
| **Note** | Hardcoded catalog is ONLY about networking topics — all other subjects get empty explanations |
| **Verdict** | ✅ **LLM-Ready** — But rule mode is limited to one subject |

### EvaluationAgent

| Attribute | Value |
|-----------|-------|
| **File** | `src/agents/evaluation_agent.py` |
| **LLM Method** | `generate_quiz()` line 123: `if self._llm is not None: return self._llm_generate_quiz()` |
| **Rule Fallback** | `_rule_generate_quiz()` — template: "What is the purpose of [topic]?" |
| **LLM Error Analysis** | `analyze_wrong_answer()` — LLM-only with full diagnosis |
| **Verdict** | ✅ **LLM-Ready** — Template fallback produces detectable garbage |

### ReflectionAgent

| Attribute | Value |
|-----------|-------|
| **File** | `src/agents/reflection_agent.py` |
| **LLM Method** | `reflect()` line 131: `if self._llm_provider is not None: summary = self._reflect_with_llm()` |
| **Rule Fallback** | `_generate_summary()` — template summary |
| **Verdict** | ✅ **LLM-Ready** — Dual-mode with source tracking |

---

## Provider Factory Coverage

### `_build_from_config()` — The Actual Factory Code

```python
# src/core/provider_factory.py:30-47
def _build_from_config(cfg: LLMConfig) -> Optional[LLMProvider]:
    if provider_name == "deepseek":  return DeepSeekProvider(...)
    if provider_name == "openai":    return OpenAIProvider(...)
    if provider_name == "spark":     return XunfeiSparkProvider(...)
    return None  # ALL OTHER PROVIDERS → None
```

### Provider Support Matrix

| Provider | In PROVIDER_META | In UI Settings | In `_build_from_config` | Actually Callable |
|----------|-----------------|---------------|------------------------|-------------------|
| DeepSeek | ✅ | ✅ | ✅ | ✅ |
| OpenAI | ✅ | ✅ | ✅ | ✅ |
| Spark (讯飞) | ✅ | ✅ | ✅ | ✅ |
| Claude | ✅ | ✅ | ❌ | ❌ |
| Gemini | ✅ | ✅ | ❌ | ❌ |
| Qwen | ✅ | ✅ | ❌ | ❌ |
| Kimi | ✅ | ✅ | ❌ | ❌ |
| Grok | ✅ | ✅ | ❌ | ❌ |
| Mock | ✅ | ✅ | ❌ (falls to Veritas) | ✅ (via Veritas) |
| Rule | ✅ | ✅ | ❌ (returns None) | ✅ (pure code) |

### The Double Gate

```
Provider configured in UI → PROVIDER_META ✓
  → load_llm_config() reads config ✓
  → _build_from_config() checks provider name
    → deepseek/openai/spark → Provider created ✓
    → all others → None → falls to Veritas factory → returns mock ❌
```

**Even if the role gate is removed, only 3 of 8 production providers are actually callable.**

---

## UI Reality Check

### Settings Page LLM Status

| Element | Shows Real Data? | Evidence |
|---------|-----------------|----------|
| Production Models list | ✅ All 8 shown | PROVIDER_META rendered in settings |
| Connection status icons | ✅ 🟢/🔴/⚪ | ProviderStatusTracker |
| Provider selector | ✅ All 10 options | SUPPORTED_PROVIDERS |
| Model selector | ✅ Per-provider presets | PROVIDER_META["models"] |
| API Key input | ✅ Password-masked | st.form with proper capture |
| Test Connection | ✅ Real API call | `_test_connection()` → `_build_from_config()` → `provider.generate("ping")` |
| Save Configuration | ✅ Persists to llm.json | `save_llm_config()` with encryption |
| **Current Model Display** | ⚠️ Shows provider name only | No model name, no token count, no latency from actual use |

### Learning Page LLM Status

| Element | Shows Real Data? | Reality |
|---------|-----------------|---------|
| Pipeline progress bar | ⚠️ Animation works | But all stages say "rule-based" |
| AI Engine Details | ❌ Empty | No `run_info` from rule mode |
| Learning Plan | ❌ Template nodes | "闭包与作用域" for Python basics |
| Quality Score | ❌ Constant 95 | Rule-determined, not AI-evaluated |
| Quiz Panel | ❌ Not rendered | Separate component, not in pipeline flow |
| Resource Cards | ❌ Not in results | Only in Workspace tab |

---

## Problem Catalog

### P0 — Critical (Blocks All LLM Usage)

| # | Problem | Location | Effect |
|---|---------|----------|--------|
| 1 | **Role gate blocks LLM** | `pipeline.py:96` | 100% of normal users get rule-only |
| 2 | **Provider factory incomplete** | `provider_factory.py:30-47` | Only 3 of 8 providers callable |

### P1 — High (Produces Demo Feel)

| # | Problem | Location | Effect |
|---|---------|----------|--------|
| 3 | **Rule output is obviously fake** | All agent `_rule_*` methods | Chinese+English mixed templates, nonsense topics |
| 4 | **Pipeline shows "done (rule-based)"** | `web/app.py:316` | User sees the lie in the UI |
| 5 | **Quiz not integrated into pipeline results** | `web/app.py:286` | Quiz panel exists but never rendered after pipeline |
| 6 | **No LLM vs Rule indicator** | Multiple | User can't tell if AI is active |

### P2 — Medium (Limits Realism)

| # | Problem | Location |
|---|---------|----------|
| 7 | **Resource catalog is single-subject** | `resource_agent.py:24-79` — all networking |
| 8 | **Profile confidence always 0.0** | `profile_agent.py` — rule mode |
| 9 | **Settings doesn't show active provider's runtime state** | `settings_tab.py` — no connection to actual pipeline usage |
| 10 | **AI Engine Details always empty** | `web/app.py:340` — `run_info` never populated from rule mode |

---

## Fix Prescription

### Fix 1: Remove Role Gate (1 line)

```python
# src/api/v2/pipeline.py — CURRENT
llm_provider = None
if role in (Role.PRO, Role.TEACHER, Role.ADMIN):
    try:
        from src.core.provider_factory import create_provider
        llm_provider = create_provider()
    except Exception:
        pass

# src/api/v2/pipeline.py — FIXED
llm_provider = None
try:
    from src.core.provider_factory import create_provider
    llm_provider = create_provider()
except Exception:
    pass  # Falls back to rule-only if no provider configured
```

**Effect:** Every user with a configured API key gets real LLM. Users without configuration still get rule-only (graceful degradation). `create_provider()` already handles "no config → mock".

### Fix 2: Extend Provider Factory (5 cases, ~15 lines)

```python
# src/core/provider_factory.py — Add after spark case
if provider_name == "anthropic":
    from src.providers.anthropic_provider import AnthropicProvider
    return AnthropicProvider(api_key=cfg.api_key, model=cfg.model or "claude-sonnet")
if provider_name == "google":
    from src.providers.google_provider import GoogleProvider
    return GoogleProvider(api_key=cfg.api_key, model=cfg.model or "gemini-pro")
if provider_name == "qwen":
    from src.providers.qwen_provider import QwenProvider
    return QwenProvider(api_key=cfg.api_key, model=cfg.model or "qwen3.5")
if provider_name == "kimi":
    from src.providers.kimi_provider import KimiProvider
    return KimiProvider(api_key=cfg.api_key, model=cfg.model or "kimi-k3")
if provider_name == "grok":
    from src.providers.grok_provider import GrokProvider
    return GrokProvider(api_key=cfg.api_key, model=cfg.model or "grok")
```

**Effect:** All 8 production providers become callable through the pipeline.

---

## Verdict

**The LLM wiring is complete and correct in every agent.** Each agent has a proper `set_llm_provider()` method, an LLM code path with prompt construction, and a rule-based fallback. The workflow correctly distributes the provider to all agents. The provider factory correctly reads user configuration and creates providers.

**The problem is not missing capability — it's two severed connections:**
1. A role gate in the API layer that refuses to create providers for normal users
2. A truncated factory that only handles 3 of 8 provider names

Fix both = real AI for real users.
