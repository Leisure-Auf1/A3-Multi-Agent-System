# Phase 14.2 — Product Reality Recovery Audit

**Date:** 2026-07-20  
**Auditor:** Hermes Agent  
**Status:** ⏳ **AWAITING APPROVAL — No source modifications will be made until approved**

---

## Objective

Identify every condition in the codebase that prevents real LLM execution from reaching users, then propose minimal fixes that reuse existing architecture.

---

## Complete LLM Execution Path — Every Blocking Condition

### Gate 1: API Endpoint (src/api/v2/pipeline.py)

| Line | Condition | Effect | Block? |
|------|-----------|--------|--------|
| 67 | `require_auth(user)` | JWT auth required | 🟢 OK |
| 81 | `budget.check_available(tokens=500)` | Token budget check | 🟢 OK |
| **96** | **`if role in (Role.PRO, Role.TEACHER, Role.ADMIN):`** | **Only 3 roles get LLM** | 🔴 **BLOCK** |
| 98 | `create_provider()` | Creates LLM provider | Only reached if role passes |
| 100 | `except Exception: pass` | Silently swallows failures | 🟡 Hidden errors |

**Verdict:** Line 96 is the primary gate. All users who register normally get `role="free"`. The condition `"free" in (PRO, TEACHER, ADMIN)` evaluates to `False`. `llm_provider` stays `None`. The pipeline runs with zero LLM calls.

**Fix:** Remove lines 95-101. Replace with unconditional `create_provider()` call.

---

### Gate 2: Provider Factory (src/core/provider_factory.py)

| Line | Condition | Effect | Block? |
|------|-----------|--------|--------|
| 34 | `if provider_name == "deepseek":` → `DeepSeekProvider` | Matches deepseek | 🟢 OK |
| 38 | `if provider_name == "openai":` → `OpenAIProvider` | Matches openai | 🟢 OK |
| 42 | `if provider_name == "spark":` → `XunfeiSparkProvider` | Matches spark | 🟢 OK |
| **47** | **`return None`** | **All other providers → None** | 🔴 **BLOCK** |

**Verdict:** `_build_from_config()` only handles 3 of 8 production providers. Claude, Gemini, Qwen, Kimi, Grok all return `None` and fall through to Veritas factory → mock.

**Fix:** Add 5 `if` cases for anthropic, google, qwen, kimi, grok.

---

### Gate 3: Pipeline Service (src/services/learning_pipeline.py)

| Line | Condition | Effect | Block? |
|------|-----------|--------|--------|
| 71 | `A3Workflow(student_id=user_id, llm_provider=llm_provider)` | Passes provider to workflow | 🟢 OK (inherits from Gate 1) |
| 105-120 | Response format | Returns dict to API | 🟢 OK |

**Verdict:** Pass-through. No additional blocking. The service correctly passes whatever provider it receives.

**Fix:** None needed here (depends on Gate 1 fix).

---

### Gate 4: A3Workflow (src/workflow/__init__.py)

| Line | Condition | Effect | Block? |
|------|-----------|--------|--------|
| 93 | `if llm_provider is not None:` | Sets provider on all 5 agents | 🟢 OK |
| 94-97 | `self.profile_agent.set_llm_provider(llm_provider)` etc. | Distributes to agents | 🟢 OK |

**Verdict:** Correct. If `llm_provider` is not None, all agents receive it. If None, agents use rule mode.

**Fix:** None needed. This is already correct.

---

### Gate 5: Agent Execution (all 7 agents)

| Agent | Line | LLM Check | Rule Fallback | Block? |
|-------|------|-----------|---------------|--------|
| ProfileAgent | 149 | `if llm is None: return self.extract(text)` | keyword matching | 🟢 OK |
| PlannerAgent | 597 | `if self._llm_provider is not None:` | static topic list | 🟢 OK |
| ContentGeneratorAgent | 232 | `set_llm_provider` → `_llm_provider` | template | 🟢 OK |
| ResourceAgent | 157 | `set_llm_provider` → `_llm_provider` | static catalog | 🟢 OK |
| EvaluationAgent | 123 | `if self._llm is not None:` | template questions | 🟢 OK |
| ReflectionAgent | 131 | `if self._llm_provider is not None:` | template summary | 🟢 OK |
| Image/Video/PPT Generators | — | Routed through Orchestrator | N/A | 🟢 OK |

**Verdict:** All agents are correctly implemented for dual-mode. No agent ever calls LLM when provider is None. No agent has a bug in its LLM path. All rule fallbacks are functional.

**Fix:** None needed. Agents are correct.

---

### Gate 6: Response Delivery (pipeline.py → API → UI)

| Line | Data Field | Populated? | Block? |
|------|-----------|------------|--------|
| pipeline.py:45 | `profile` | ✅ Yes | 🟢 |
| pipeline.py:46 | `plan` | ✅ Yes | 🟢 |
| pipeline.py:48 | `content` | ✅ Yes (but not rendered) | 🟡 **GAP** |
| pipeline.py:49 | `evaluation` | ✅ Yes | 🟢 |
| pipeline.py:50 | `reflection` | ✅ Yes | 🟢 |
| pipeline.py:51 | `trace` | ✅ Yes | 🟢 |
| pipeline.py:55 | `status` | ✅ Yes | 🟢 |
| **N/A** | **`run_info`** (AI Engine, Model, Tokens, Latency) | ❌ **Not in schema** | 🔴 **MISSING** |

**Verdict:** The response schema lacks observability data (which provider was used, which model, how many tokens, latency per agent). The UI's "AI Engine Details" expander is always empty because the data is never provided.

**Fix:** Add `run_info` field to `PipelineRunResponse` and populate it from the workflow execution.

---

### Gate 7: UI Display (web/app.py)

| Line | UI Element | Renders Real Data? | Block? |
|------|-----------|-------------------|--------|
| 219-223 | Dashboard stats | ✅ From API | 🟢 |
| 297-320 | Pipeline progress bar | ⚠️ Simulated, not real agent status | 🟡 |
| 340-360 | AI Engine Details | ❌ `run_info` always empty | 🔴 |
| 363-369 | Quick summary metrics | ✅ From API result | 🟢 |
| 392-401 | Learning Plan expander | ✅ Shows real plan data | 🟢 |
| 404-411 | Quality Evaluation | ✅ Shows real score | 🟢 |
| **N/A** | **Generated content (lesson)** | ❌ `content` not rendered | 🔴 **GAP** |
| **N/A** | **Quiz panel** | ❌ Not integrated into results | 🔴 **GAP** |
| **N/A** | **Resource cards** | ❌ Not in pipeline results | 🔴 **GAP** |

**Verdict:** The UI receives real data (profile, plan, evaluation) but fails to display:
1. Generated lesson content (`result.content`) — exists in response but never rendered
2. Quiz — exists as separate component but not wired into pipeline flow
3. Resource cards — exist in workspace but not shown in pipeline results
4. AI Engine metadata — never populated in response

**Fix:** Add content rendering, quiz integration, resource cards to `_render_pipeline_results`.

---

## Complete Blocking Condition Inventory

### 🔴 Critical — Block LLM Execution

| # | File | Line | Condition | Severity |
|---|------|------|-----------|----------|
| B1 | `src/api/v2/pipeline.py` | 96 | `if role in (PRO, TEACHER, ADMIN):` — only 3 roles | P0 |
| B2 | `src/core/provider_factory.py` | 47 | `return None` — only 3 of 8 providers | P0 |

### 🟡 High — Block User Experience

| # | File | Line | Condition | Severity |
|---|------|------|-----------|----------|
| B3 | `web/app.py` | 332 | Content field not rendered after pipeline | P1 |
| B4 | `web/app.py` | 286 | Quiz panel not integrated into pipeline results | P1 |
| B5 | `web/app.py` | 332 | Resource cards not in pipeline results | P1 |
| B6 | `src/api/v2/pipeline.py` | — | `run_info` not in response schema | P1 |

### 🟢 Medium — Usability

| # | File | Line | Condition | Severity |
|---|------|------|-----------|----------|
| B7 | `web/app.py` | 297-320 | Progress bar is simulated, not real agent status | P2 |
| B8 | `src/core/provider_factory.py` | 100 | `except Exception: pass` — silently swallows errors | P2 |

---

## Provider Registry Audit

| Provider | PROVIDER_META (config) | `_build_from_config` (factory) | Settings UI | Status |
|----------|----------------------|-------------------------------|-------------|--------|
| deepseek | ✅ | ✅ | ✅ | Consistent |
| openai | ✅ | ✅ | ✅ | Consistent |
| spark | ✅ | ✅ | ✅ | Consistent |
| anthropic | ✅ | ❌ | ✅ | Factory gap |
| google | ✅ | ❌ | ✅ | Factory gap |
| qwen | ✅ | ❌ | ✅ | Factory gap |
| kimi | ✅ | ❌ | ✅ | Factory gap |
| grok | ✅ | ❌ | ✅ | Factory gap |
| mock | ✅ | ❌ (Veritas fallback) | ✅ | Indirectly OK |
| rule | ✅ | ❌ (returns None) | ✅ | OK (no provider needed) |

---

## Runtime Observability Audit

| Metric | Collected? | Exposed in Response? | Displayed in UI? |
|--------|-----------|---------------------|-----------------|
| Selected provider | ❌ | ❌ | ❌ |
| Active model name | ❌ | ❌ | ❌ |
| Token usage | ❌ | ❌ | ❌ |
| Latency per agent | ⚠️ In trace events | ⚠️ In trace | ⚠️ Trace expander |
| Fallback status | ❌ | ❌ | ❌ |
| Rule vs LLM indicator | ⚠️ In agent output | ⚠️ In trace | ⚠️ "done (rule-based)" text |

---

## Proposed Fix Plan

### Fix 1: Remove Role Gate
**File:** `src/api/v2/pipeline.py`  
**Change:** Delete lines 95-101, replace with unconditional provider creation  
**Risk:** Low — `create_provider()` returns None when no config exists, graceful degradation preserved  
**Tests affected:** 0 (existing pipeline tests already test with direct provider injection)

### Fix 2: Extend Provider Factory
**File:** `src/core/provider_factory.py`  
**Change:** Add 5 `if` cases (anthropic, google, qwen, kimi, grok), ~15 lines  
**Risk:** Low — each provider class already exists and is tested  
**Tests affected:** New integration tests needed

### Fix 3: Add Runtime Observability to Response
**File:** `src/api/v2/pipeline.py`  
**Change:** Add `run_info` dict to response: `{engine, provider, model, generation_time_ms, tokens_used, is_fallback}`  
**Risk:** Low — additive field, backward compatible  
**Tests affected:** New assertion verifications

### Fix 4: Wire UI to Display Generated Content
**File:** `web/app.py`  
**Change:** Add content/quiz/resource rendering to `_render_pipeline_results`  
**Risk:** Low — content data already in response, just not rendered  
**Tests affected:** UI component tests needed

### Fix 5: Integration Tests
**File:** `tests/test_product_llm_integration.py` (new)  
**Tests:**
- DeepSeek provider is actually invoked when configured
- Mock fallback only occurs without API key
- Generated quiz is not template output (LLM mode)
- Profile analysis has confidence > 0 (LLM mode)
- Pipeline includes `run_info` with provider/model
- All 8 providers can be built by factory
- Response contains non-empty `content` field

---

## Impact Assessment

| What Changes | What Stays |
|-------------|-----------|
| 1 role check removed | A3Workflow — unchanged |
| 5 provider cases added | All 7 agents — unchanged |
| 1 new response field (`run_info`) | All 2661 existing tests — unchanged |
| 3 UI sections wired (content/quiz/resources) | Auth, token budget, permission — unchanged |
| ~15 lines of factory code | LearningPipelineService — unchanged |
| ~30 lines of UI code | ProviderFactory structure — unchanged |
| ~60 lines of new tests | Veritas-Core — unchanged |

**No new Runtime. No duplicate agents. No architecture changes.**

---

## Verification Criteria

After approval and implementation, verify:

1. `make test` → 2661 + new tests all pass
2. Free user with DeepSeek API key → pipeline calls LLM
3. Free user without API key → pipeline falls back to rule-only (graceful degradation)
4. Settings UI shows all 8 production providers
5. Pipeline results show AI Engine, Model, Tokens, Latency
6. Pipeline results show generated lesson content
7. Quiz generates non-template questions (LLM mode)
8. Profile analysis confidence > 0 (LLM mode)

---

## ⏳ Awaiting Approval

**No source modifications will be made until approved.**

Please review and confirm:
1. Fix plan acceptable?
2. Scope appropriate?
3. Any additional constraints?
