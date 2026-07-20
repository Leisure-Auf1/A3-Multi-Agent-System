# Phase 16.1 — Learning Loop Completion Plan

**Date:** 2026-07-20  
**Status:** ⏳ **AWAITING HUMAN GATE**

---

## Audit Summary

| Target | Current State | Plan |
|--------|-------------|------|
| **P0: Quiz Integration** | `render_quiz_panel()` exists but never called from pipeline results | Wire into `_render_pipeline_results` with provider from config |
| **P1: Reflection Output** | `result.reflection` has data but never rendered | Add reflection expander |
| **P1: Progress Bar** | Shows hardcoded 7 stages, read after pipeline completes | Replace hardcoded stages with actual agent names from trace |

---

## P0: Quiz Integration

### Current State

```python
# web/app.py:286 — _render_pipeline_results
# Renders: AI Engine Details, Summary, Agent Trace, Plan, Evaluation, Content, Resources
# Quiz panel is NOT called anywhere in this function.
```

### Integration Point

```python
# After resource cards (line 456), add:
result = st.session_state.get("pipeline_result")
if result:
    # Create provider from user config for quiz
    from src.core.provider_factory import create_provider
    provider = create_provider()
    topic = result.get("goal", "")
    if provider is not None:
        render_quiz_panel(provider, topic)
```

### Provider Resolution

`render_quiz_panel` needs an LLM provider. Options:
1. `create_provider()` — reads user config, returns real provider if configured
2. `get_llm_provider()` — same, via FastAPI dependency

We use `create_provider()` which:
- Reads user config from llm.json
- Returns DeepSeek/OpenAI/etc if configured
- Returns None if mock/rule (→ quiz shows "Configure LLM" message)

### File Changes

| File | Change | Lines |
|------|--------|-------|
| `web/app.py` | Import quiz panel, call it in `_render_pipeline_results` | +8 |

---

## P1: Reflection Output

### Current State

```python
# API response has:
refl = result.get("reflection")
# refl = {
#   "source": "rule" | "llm",
#   "summary": "...",
#   "achievements": [...],
#   "improvements": [...],
# }
# But _render_pipeline_results never renders it.
```

### Integration Point

```python
# After evaluation expander, before generated content:
refl = result.get("reflection")
if refl:
    with st.expander("💭 AI Reflection", expanded=False):
        source = refl.get("source", "rule")
        if source == "llm":
            st.success("🤖 AI-powered analysis")
        else:
            st.info("⚙️ Rule-based analysis")
        
        summary = refl.get("summary", "")
        if summary:
            st.markdown(summary[:500])
        
        achievements = refl.get("achievements", [])
        improvements = refl.get("improvements", [])
        
        if achievements:
            st.markdown("**Achievements:**")
            for a in achievements:
                st.markdown(f"- ✅ {a}")
        
        if improvements:
            st.markdown("**Improvements:**")
            for imp in improvements:
                st.markdown(f"- 📝 {imp}")
```

### File Changes

| File | Change | Lines |
|------|--------|-------|
| `web/app.py` | Add reflection expander in `_render_pipeline_results` | +20 |

---

## P1: Progress Bar Accuracy

### Current State

```python
PIPELINE_STAGES = [
    ("ProfileAgent", ...),
    ("PlannerAgent", ...),
    ("ContentGeneratorAgent", ...),
    ("ResourceAgent", ...),
    ("ReviewAgent", ...),
    ("ReflectionAgent", ...),
    ("Memory", ...),
]
# Always shows 7 stages regardless of actual execution
```

### Fix

Read actual agent names from trace data instead of hardcoded list:

```python
# In _execute_pipeline_with_progress:
trace = result.get("trace", [])
# Extract unique agent names from trace
agents_in_trace = []
seen = set()
for t in trace:
    agent = t.get("agent", "")
    if agent and agent not in seen and agent != "System":
        seen.add(agent)
        agents_in_trace.append(agent)

# Show progress for actual agents that ran
completed = 0
for i, agent_name in enumerate(agents_in_trace):
    pct = int((i + 1) / max(len(agents_in_trace), 1) * 100)
    matching = [t for t in trace if t.get("agent") == agent_name]
    if matching:
        t = matching[-1]
        dur = t.get("duration_ms", 0)
        status_text.success(f"🤖 {agent_name} — {dur:.0f}ms")
        completed += 1
    progress_bar.progress(pct, f"{completed}/{len(agents_in_trace)} agents")

# If no trace, show minimal (1 agent)
if not agents_in_trace:
    progress_bar.progress(100, "Pipeline complete (rule-only)")
```

### File Changes

| File | Change | Lines |
|------|--------|-------|
| `web/app.py` | Replace hardcoded PIPELINE_STAGES loop with trace-driven progress | ~15 |

---

## Test Plan

### New Tests: `tests/test_phase16_ui_loop.py`

| # | Test | What It Verifies |
|---|------|-----------------|
| 1 | `test_quiz_panel_importable` | `render_quiz_panel` is importable |
| 2 | `test_quiz_panel_accepts_provider` | Quiz panel renders without crash with valid provider |
| 3 | `test_quiz_panel_handles_none_provider` | Quiz panel shows message when provider=None |
| 4 | `test_quiz_panel_stateful` | Quiz generates questions, stores in session_state |
| 5 | `test_reflection_data_structure` | Pipeline response has reflection with expected keys |
| 6 | `test_reflection_has_source` | Reflection has source field (rule/llm) |
| 7 | `test_reflection_has_summary` | Reflection has summary text |
| 8 | `test_pipeline_result_has_all_sections` | Result dict has profile, plan, content, evaluation, reflection, run_info |
| 9 | `test_progress_from_trace` | Trace-driven agents list is correct |
| 10 | `test_progress_fallback_empty_trace` | Empty trace → shows fallback message |

**Total: 10 new tests**

### Existing Test Impact

| Test | Impact | Action |
|------|--------|--------|
| `test_ui_polish.py::test_pipeline_result_has_all_fields` | Checks result dict keys | May need to add "reflection" to expected keys |
| All pipeline tests | No behavior change | — |
| All quiz tests | No quiz behavior change | — |

---

## Full Change Summary

| File | Lines Changed | What |
|------|-------------|------|
| `web/app.py` | +43 | Quiz integration (+8), Reflection expander (+20), Progress accuracy (+15) |
| `tests/test_phase16_ui_loop.py` | +150 | 10 new tests |
| `tests/test_ui_polish.py` | +1 | Add "reflection" to expected keys if needed |
| **Total** | **~194** | **3 features + 10 tests** |

---

## Architecture Impact

| Component | Modified? | How |
|-----------|----------|-----|
| `src/core/` | ❌ No | — |
| A3Workflow | ❌ No | — |
| Agents | ❌ No | — |
| Veritas-Core | ❌ No | — |
| `web/app.py` | ✅ Yes | Quiz + reflection + progress |
| `web/components/quiz_panel.py` | ❌ No | Used as-is |

---

## Before/After User Journey

### Before (Phase 16.0)

```
Register → Configure LLM → Enter Goal → Run Pipeline
  → [progress bar 7 stages]
  → AI Engine Details ("rule-only")
  → Learning Plan (4 nodes)
  → Quality Evaluation (95)
  → Generated Lesson (4 chapters)
  → Resource Cards (3 items)
  → ❌ NO QUIZ
  → ❌ NO REFLECTION
  → History (score + duration)
```

### After (Phase 16.1)

```
Register → Configure LLM → Enter Goal → Run Pipeline
  → [progress bar → actual agent names from trace]
  → AI Engine Details (real provider name)
  → Learning Plan (4 nodes)
  → Quality Evaluation (95)
  → 💭 AI Reflection (summary, achievements, improvements)
  → Generated Lesson (4 chapters)
  → Resource Cards (3 items)
  → ✅ QUIZ ("Verify Learning" button)
      → view 3 questions
      → answer each
      → submit
      → see score + weak/strong areas
      → see per-question error analysis
      → see recovery plan
  → History (score + duration)
```

---

## ⏳ Awaiting Human Gate

**3 features, 10 tests, 0 architecture changes. ~194 lines total.**

Approve to proceed with implementation.
