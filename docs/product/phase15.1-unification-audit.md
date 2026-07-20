# Phase 15.1 — AI Capability Unification Audit

**Date:** 2026-07-20  
**Auditor:** Hermes Agent  
**Status:** ⏳ **AWAITING HUMAN GATE — Read-Only Audit Complete**

---

## Defect Re-Assessment

Phase 15.0 identified 4 defects. Re-verification reveals:

| # | Phase 15.0 Label | Actual Status | Root Cause |
|---|-----------------|---------------|------------|
| D1 | `_build_run_info` reports rule-only | ✅ **CONFIRMED** | veritas.llm providers lack `provider_name` attribute |
| D2 | Quiz endpoint bypasses LLM | ❌ **FALSE ALARM** | Quiz DOES have LLM wiring (`get_llm_provider()`). Template output was due to dummy key failing API call |
| D3 | Resource endpoint bypasses LLM | ✅ **CONFIRMED** | `MultimodalGateway` uses internal template providers, no LLM injection |
| D4 | Profile endpoint lacks LLM | ✅ **CONFIRMED** | Calls `agent.extract()` (rule-only) instead of `agent.extract_with_provider()` |

**Net: 3 real defects, 1 false alarm.**

---

## Root Cause Analysis

### D1: `_build_run_info` — Provider Name Detection Failure

**File:** `src/api/v2/pipeline.py:127`

```python
provider_name = getattr(llm_provider, 'provider_name', None)  # ← None for veritas
```

**Why it fails:**

```python
# veritas.llm.deepseek_provider.DeepSeekProvider
# Has: .model, .api_key, .is_available, .generate()
# Does NOT have: .provider_name  ← attribute missing

# src.providers.anthropic_provider.AnthropicProvider  
# Has: .provider_name (via BaseLLMProvider)  ← works fine

# Result: DeepSeek/OpenAI/Spark → provider_name=None → falls to "rule-only" branch
```

**Impact:** Pipeline always shows `engine: "rule-only"` in run_info, even with real API key. Users never see their actual provider in the UI.

**Fix size:** 5 lines — add fallback detection chain.

---

### D2: Quiz Endpoint — NOT A DEFECT

**File:** `src/api/v2/evaluation.py:89`

```python
agent = EvaluationAgent(llm_provider=get_llm_provider())  # ← LLM IS injected!
```

`get_llm_provider()` → `get_provider("")` → `create_provider("")` → `load_llm_config()` → `_build_from_config(cfg)`.

**Verdict:** Quiz endpoint already has full LLM wiring. Phase 15.0 test showed template output because the dummy API key caused LLM call failure → rule fallback. With real key, quiz generates AI-powered questions.

**No fix needed.**

---

### D3: Resource Endpoint — No LLM Injection

**File:** `src/api/v2/resources.py:103`

```python
gateway = MultimodalGateway()  # ← No LLM provider passed
```

`MultimodalGateway.__init__()` registers internal template providers:
- `TextProvider()` — template text generator
- `CodeProvider()` — template code generator  
- `PPTProvider()` — template slide generator
- `ImageProvider()` — template image generator

None of these use `create_provider()` or accept LLM injection. All produce template output.

**Impact:** Resources always template-generated regardless of user's API key configuration.

**Fix size:** 8 lines — inject LLM provider into gateway and pass to text/code providers.

---

### D4: Profile Endpoint — Rule-Only Extraction

**File:** `src/api/v2/profile.py:74-75`

```python
agent = ProfileAgent()              # ← No LLM provider
result = agent.extract(req.text)    # ← Rule-based extraction, not extract_with_provider()
```

ProfileAgent has a fully working `extract_with_provider()` method (line 125-200) that calls LLM with a structured prompt. But the endpoint calls `extract()` which uses keyword matching only.

**Impact:** Profile always `source: "rule"`, `confidence: 0.0`. Users never get AI-analyzed learning profiles.

**Fix size:** 5 lines — inject provider and call `extract_with_provider()`.

---

## Additional Finding: Provider Cache Issue (Note, Not Blocking)

**File:** `src/api/dependencies.py:21-24`

```python
@lru_cache(maxsize=4)
def _cached_create_provider(mode: str) -> Optional[LLMProvider]:
    return create_provider(mode)
```

`create_provider("")` reads user config from disk. First call caches the result per-mode. Subsequent calls return cached provider regardless of caller's config.

**Risk:** If user A configures DeepSeek and calls any endpoint first, the cached DeepSeek provider is returned for user B who has no config. This is a cache invalidation bug, not a Phase 15.1 scope item.

---

## Modification Plan

### Fix D1: Provider Name Detection

**File:** `src/api/v2/pipeline.py` — `_build_run_info()`

**Current (lines 127-132):**
```python
provider_name = getattr(llm_provider, 'provider_name', None)
model_name = getattr(llm_provider, 'model', None)
info = {
    "engine": provider_name or "rule",
    "provider": provider_name or "rule",
    "model": model_name or "",
```

**Fixed:**
```python
# Try provider_name first (src/providers/*), then type name (veritas.llm.*)
provider_name = (
    getattr(llm_provider, 'provider_name', None)
    or type(llm_provider).__name__.replace('Provider', '').lower()
)
model_name = getattr(llm_provider, 'model', None)
info = {
    "engine": provider_name or "rule",
    "provider": provider_name or "rule",
    "model": model_name or "",
```

**Lines changed:** 2  
**Risk:** Low — purely additive fallback  
**Architecture impact:** None

---

### Fix D3: Resource Endpoint LLM Injection

**File:** `src/api/v2/resources.py`

**Current (lines 98-119):**
```python
@router.post("/generate")
def generate_resources_v2(req: GenerateBody, user: AuthUser = Depends(require_auth)):
    gateway = MultimodalGateway()
    results = []
    for rtype in req.resource_types:
        ...
        artifact = gateway.generate(GenerateRequest(...))
```

**Fixed:**
```python
@router.post("/generate")
def generate_resources_v2(req: GenerateBody, user: AuthUser = Depends(require_auth)):
    from src.api.dependencies import get_llm_provider
    from src.core.provider_factory import create_provider
    
    llm = get_llm_provider()  # Already reads user config
    gateway = MultimodalGateway()
    if llm is not None:
        gateway.set_llm_provider(llm)  # New method on gateway
    ...
```

**New method on `MultimodalGateway`:**
```python
def set_llm_provider(self, provider):
    """Inject LLM provider into registered text/code providers."""
    for p in self._providers.values():
        if hasattr(p, 'set_llm_provider'):
            p.set_llm_provider(provider)
```

**Lines changed:** ~8 (3 in resources.py, 5 in gateway.py)  
**Risk:** Low — additive injection, gateways are stateless  
**Architecture impact:** MultimodalGateway gains `set_llm_provider()` (new method)

---

### Fix D4: Profile Endpoint LLM Enhancement

**File:** `src/api/v2/profile.py`

**Current (lines 73-81):**
```python
agent = ProfileAgent()
result = agent.extract(req.text)
profile = result.to_dict() if hasattr(result, 'to_dict') else {}
save_profile(user.id, profile)
resp = JSONResponse(content=ProfileResponse(
    user_id=user.id, profile=profile, source="rule"
).model_dump())
```

**Fixed:**
```python
from src.api.dependencies import get_llm_provider

llm = get_llm_provider()
agent = ProfileAgent()
if llm is not None:
    agent.set_llm_provider(llm)
    result = agent.extract_with_provider(req.text)
else:
    result = agent.extract(req.text)
profile = result.to_dict() if hasattr(result, 'to_dict') else {}
source = result.source if hasattr(result, 'source') else 'rule'
save_profile(user.id, profile)
resp = JSONResponse(content=ProfileResponse(
    user_id=user.id, profile=profile, source=source
).model_dump())
```

**Lines changed:** 5  
**Risk:** Low — additive, rule fallback preserved when no config  
**Architecture impact:** None (ProfileAgent already has `extract_with_provider()`)

---

## Test Plan

### New Tests: `tests/test_phase15_ai_unification.py`

| # | Test | What It Verifies |
|---|------|-----------------|
| 1 | `test_run_info_detects_deepseek_provider` | `_build_run_info` correctly identifies veritas.llm providers |
| 2 | `test_run_info_detects_src_provider` | `_build_run_info` works with `src.providers.*` providers |
| 3 | `test_run_info_detects_anthropic_provider` | Specific provider name extraction |
| 4 | `test_run_info_fallback_when_none` | `_build_run_info` correctly reports rule-only when llm_provider=None |
| 5 | `test_run_info_model_name` | Model name correctly extracted |
| 6 | `test_run_info_tokens_from_trace` | Token extraction from trace entries |
| 7 | `test_gateway_set_llm_provider` | `MultimodalGateway.set_llm_provider()` propagates to providers |
| 8 | `test_gateway_llm_provider_none_noop` | Calling `set_llm_provider(None)` doesn't crash |
| 9 | `test_gateway_providers_accept_llm` | TextProvider/CodeProvider accept LLM injection |
| 10 | `test_profile_endpoint_accepts_llm` | Profile endpoint uses `extract_with_provider` when LLM available |
| 11 | `test_profile_endpoint_falls_back_rule` | Profile endpoint falls to `extract()` when no LLM |
| 12 | `test_profile_source_tracks_llm_vs_rule` | `source` field correctly reflects LLM vs rule |
| 13 | `test_quiz_endpoint_still_has_llm` | Regression: Quiz endpoint still gets LLM provider |
| 14 | `test_resource_generate_with_llm` | Resources endpoint passes LLM to gateway |
| 15 | `test_all_fixes_preserve_rule_fallback` | No config → all endpoints still work in rule mode |

**Total: 15 tests**

### Existing Test Impact

| Impact | Reason |
|--------|--------|
| 0 existing tests broken | All changes are additive |
| `_build_run_info` behavior change | New test covers, existing tests don't assert on run_info internals |
| `MultimodalGateway` new method | Existing tests create gateway without calling `set_llm_provider()` |
| Profile endpoint behavior change | Existing profile tests check structure not source field value |

---

## Change Summary

| File | Lines Changed | What |
|------|-------------|------|
| `src/api/v2/pipeline.py` | +2 | D1: provider name fallback |
| `src/api/v2/resources.py` | +4 | D3: LLM injection into gateway |
| `src/multimodal/gateway.py` | +5 | D3: `set_llm_provider()` method |
| `src/api/v2/profile.py` | +5 | D4: `extract_with_provider()` call |
| `tests/test_phase15_ai_unification.py` | +200 | 15 new tests |
| **Total** | **~216** | **3 fixes + 15 tests** |

## Architecture Impact

| Component | Modified? | How |
|-----------|----------|-----|
| A3Workflow | ❌ No | — |
| Agent Runtime | ❌ No | — |
| ProviderFactory | ❌ No | — |
| ProfileAgent | ❌ No | Uses existing `extract_with_provider()` |
| EvaluationAgent | ❌ No | Already wired |
| MultimodalGateway | ✅ New method | `set_llm_provider()` — additive |
| API routes | ✅ 3 files | Minor hookup changes |

---

## ⏳ Awaiting Human Gate

**3 fixes, 15 new tests, 0 architecture changes, ~216 lines total.**

Approve to proceed with implementation.
