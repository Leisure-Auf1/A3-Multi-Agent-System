# Phase 17.1 — LLM Authenticity Audit

**Date:** 2026-07-20
**Status:** ⏳ **AWAITING HUMAN GATE** — READ-ONLY audit.

**Baseline:** v1.0.0 (da953fa), 2836 tests, Phase 17.0 black-box complete.

---

## 1. Executive Summary

Traced all 7 agents' LLM provider injection paths. Found:

- **5 agents** wired via A3Workflow injection ✅
- **2 agents** wired via API endpoint constructor ✅
- **Trace/EventBus records NO provider data** ❌ — events have `agent/action/status/duration` but no `provider` or `tokens`
- **Quiz `strong_areas` empty string bug** — root cause identified
- **Per-agent LLM vs rule usage is opaque** — `run_info` aggregates all agents

---

## 2. Complete LLM Injection Map

### 2.1 Injection Entry Point

```
POST /api/v2/learning/run
  → LearningPipelineService.run()
    → create_provider()                          # reads llm.json / env var
    → A3Workflow(student_id, llm_provider=...)   # constructor injection
      → profile_agent.set_llm_provider(provider)       ✅ Line 94
      → planner_agent.set_llm_provider(provider)       ✅ Line 95
      → content_generator_agent.set_llm_provider(provider) ✅ Line 96
      → resource_agent.set_llm_provider(provider)      ✅ Line 97
      → reflection_agent.set_llm_provider(provider)    ✅ Line 98
```

### 2.2 Per-Agent LLM Usage

| Agent | LLM Store | LLM Check | Rule Fallback | Works? |
|-------|-----------|-----------|---------------|--------|
| **ProfileAgent** | `self._llm_provider` | `extract_with_llm()` if provider set | Rule-based profile extraction | ✅ |
| **PlannerAgent** | `self._llm_provider` | `_enhance_plan_with_llm()` if provider set | Rule-based plan generation | ✅ |
| **ContentGeneratorAgent** | `self._llm_provider` | `_generate_with_llm()` if provider set | Rule-based content templates | ✅ |
| **ResourceAgent** | `self._llm_provider` | `_enrich_with_llm()` if provider set | Static resource selection | ✅ |
| **ReflectionAgent** | `self._llm_provider` | `_reflect_with_llm()` if provider set | Rule-based reflection | ✅ |
| **EvaluationAgent** | `self._llm` (constructor) | `_llm_generate_quiz()`, `_llm_analyze_wrong_answer()` | `_rule_generate_quiz()` | ✅ |
| **TutorAgent** | `self._llm` (constructor) | `generate()` if provider set | `_fallback_explain()` | ✅ |

**Note:** EvaluationAgent and TutorAgent are NOT injected by A3Workflow. They receive LLM via:
- Quiz: `EvaluationAgent(llm_provider=get_llm_provider())` → `src/api/v2/evaluation.py:89`
- Score: `EvaluationAgent(llm_provider=get_llm_provider())` → `src/api/v2/evaluation.py:112`
- Chat: `TutorAgent(llm_provider=get_llm_provider())` → `src/api/v2/chat.py:88`

---

## 3. Trace/EventBus Gap — No Provider Data

### Current Event Recording

```python
# src/workflow/__init__.py:712-732
def _emit(self, agent, action, input_summary, output_summary, status, duration_ms):
    self._bus.emit(agent=agent, action=action, ...)  # NO metadata!

# src/core/event_bus.py:89-109
def emit(self, agent, action, ..., metadata=None):
    event = AgentEvent(
        agent=agent, action=action, status=status, duration_ms=duration_ms,
        metadata=metadata or {},  # metadata EXISTS but NEVER used by workflow!
    )
```

### What's Missing

| Data | In trace? | In run_info? |
|------|-----------|-------------|
| Agent name | ✅ | ❌ |
| Action | ✅ | ❌ |
| Status (success/error) | ✅ | ❌ |
| Duration | ✅ | ❌ |
| **Provider used** | ❌ | ❌ (aggregate only) |
| **LLM vs Rule** | ❌ | ❌ |
| **Tokens per agent** | ❌ | ❌ |
| **Model per agent** | ❌ | ❌ |

### Impact

In the UI, `run_info` shows `engine=mockllm, model=mock-model-v1, tokens=0` — but this is the **pipeline-level aggregate**. A user cannot tell which specific agents used LLM and which fell back to rule mode.

**Example from Phase 17.0 black-box test:**
- `ReflectionAgent`: `source=llm` ✅
- `ContentGenerator`: `source=rule` ❌ (was this intentional or a bug?)

---

## 4. AI Execution Card — Dashboard Gap

### Current Dashboard State

```python
# web/app.py:229-257 — Dashboard
if is_demo:
    "Demo Mode — exploring with rule-based AI."
else:
    "AI Mode — Deepseek" + "Active model: deepseek-chat"
```

### What's Missing

The Dashboard shows **whether** AI is enabled, but not:
- How many agents used LLM vs rule in the last run
- Token consumption per run
- Provider latency breakdown
- Which agents contributed to token usage

### Proposed: AI Execution Card

```
┌─────────────────────────────────────────────────────┐
│ 🤖 AI Execution — Last Run                          │
│ Provider: DeepSeek · Model: deepseek-chat           │
│ Duration: 2.3s · Tokens: 1,847                      │
│                                                     │
│ Agents using LLM:  5/7                              │
│ ✅ ProfileAgent     — 247 tokens (llm)              │
│ ✅ PlannerAgent     — 312 tokens (llm)              │
│ ✅ ContentGenerator — 892 tokens (llm)              │
│ ❌ ResourceAgent    — rule (no LLM enrichment)      │
│ ✅ ReflectionAgent  — 196 tokens (llm)              │
│ ❌ Memory           — rule (no LLM)                 │
└─────────────────────────────────────────────────────┘
```

---

## 5. Quiz `strong_areas` Empty String Bug

### Root Cause

```
src/api/v2/evaluation.py:48-49
  class QuizScoreRequest(BaseModel):
      quiz_id: str = ""
      topic: str = ""            ← defaults to ""

src/api/v2/evaluation.py:117-125
  questions.append(QuizQuestion(
      topic=req.topic,           ← empty string when client omits topic
      ...
  ))

src/agents/evaluation_agent.py:245
  strong.add(q.topic)            ← adds "" to set

src/agents/evaluation_agent.py:270
  strong_areas=sorted(strong)    ← produces ['']
```

### Reproduction

```python
# Client doesn't pass topic:
POST /api/v2/evaluation/quiz/score
  {"quiz_id": "abc", "answers": [...]}   # NO topic field

→ Response: {"strong_areas": [""]}       # BUG: empty string
```

### Fix (2 options)

**Option A** (in `score_quiz` — safest):
```python
# Line 245: Filter empty topics
if q.topic:  # only add non-empty topics
    strong.add(q.topic)
```

**Option B** (in API — stricter):
```python
# QuizScoreRequest: make topic required
topic: str = Field(..., min_length=1)
```

**Recommendation:** Option A (backward-compatible). Also apply to `weak` on line 247.

---

## 6. Summary of Findings

| # | Finding | Type | Severity |
|---|---------|------|----------|
| 1 | Trace events lack provider/model/token metadata | Gap | P0 |
| 2 | Dashboard shows pipeline-level AI info, not per-agent | Gap | P0 |
| 3 | `strong_areas` contains empty string when topic omitted | Bug | P1 |
| 4 | `weak_areas` can also contain empty string (same root cause) | Bug | P1 |
| 5 | 5 agents wired via workflow, 2 via API — inconsistent pattern | Gap | P2 |
| 6 | EventBus `metadata` dict exists but never populated by workflow | Gap | P0 |

---

## 7. Recommended Implementation Plan

### Phase 17.1-A: Trace Provider Data (P0, ~20 lines)

**File:** `src/workflow/__init__.py`

Add `metadata` to each `_emit()` call with provider info:
```python
def _run_profile_agent(self, ...):
    source = "llm" if self.llm_provider else "rule"
    self._emit("ProfileAgent", "profile_extracted",
               input_summary=..., output_summary=...,
               duration_ms=dur,
               metadata={"source": source, "provider": provider_name, "model": model_name})
```

### Phase 17.1-B: AI Execution Card (P0, ~25 lines)

**File:** `web/app.py` — `_render_pipeline_results`

After `run_info` expander, add AI Execution Card:
```python
# Extract per-agent LLM usage from trace
llm_agents = []
for t in trace:
    meta = t.get("metadata", {})
    if meta.get("source") == "llm":
        llm_agents.append(f"{t['agent']} ({meta.get('provider','?')})")
```

### Phase 17.1-C: Fix Quiz Empty String (P1, ~5 lines)

**File:** `src/agents/evaluation_agent.py`

```python
if is_correct:
    correct += 1
    earned += q.points
    if q.topic:  # FIX: filter empty topics
        strong.add(q.topic)
else:
    if q.topic:  # FIX: filter empty topics
        weak.add(q.topic)
```

**File:** `src/api/v2/evaluation.py` (optional)

```python
class QuizScoreRequest(BaseModel):
    quiz_id: str = ""
    topic: str = Field("", min_length=0)  # Keep backward-compat, filter in agent
```

---

## 8. Architecture Impact

| Component | Modified? | How |
|-----------|----------|-----|
| `src/workflow/__init__.py` | ✅ Yes | Add metadata to _emit calls |
| `src/agents/evaluation_agent.py` | ✅ Yes | Filter empty topics in score_quiz |
| `web/app.py` | ✅ Yes | AI Execution Card |
| A3Workflow | ❌ No | Only trace metadata, not core logic |
| Agents (core logic) | ❌ No | Only bug fix in score_quiz |
| Veritas-Core | ❌ No | — |

**Total: 3 files, ~50 lines, 0 core changes.**

---

## ⏳ Awaiting Human Gate

**3 features (trace metadata, AI card, quiz bug fix), 0 architecture changes.**
