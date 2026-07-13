# Phase 13 — Final Execution Plan

> Prioritized implementation roadmap: 89% → 95% competition readiness
> Date: 2026-07-13 | A3 v2.8 → v2.9

---

## Summary

| Tier | Features | Lines | Hours | Impact |
|:-----|:---------|:------|:------|:------:|
| **A** | 4 features | ~310 | 4-6h | +4% readiness |
| **B** | 2 features | ~140 | 2-3h | +2% readiness |
| **C** | 3 deferred | 0 | 0 | — |
| **Total** | 9 assessed | ~450 | 6-9h | **89% → 95%** |

---

## Priority A: Must Implement

### A1: Xunfei Spark Live Provider Switch

| Aspect | Detail |
|:-------|:-------|
| **Feature** | Add `LLM_PROVIDER=xunfei` environment config + provider factory |
| **Value** | 🟢🟢🟢🟢🟢 Judges expect real LLM calls |
| **Files** | `src/core/provider_factory.py` (NEW, 30 lines), `web/chat_demo.py` (+15 lines) |
| **Estimated lines** | ~55 |
| **Risk** | 🟢 Low — provider interface exists, adapter handles fallback |
| **Test strategy** | Manual: set `LLM_PROVIDER=mock`, verify pipeline works. Set `LLM_PROVIDER=none`, verify rule fallback. |
| **Dependencies** | Valid `XF_SPARK_API_KEY` for production testing |

### A2: Trust & Safety Panel

| Aspect | Detail |
|:-------|:-------|
| **Feature** | 7th dashboard panel: grounding confidence, evaluation scores, review status, hallucination check |
| **Value** | 🟢🟢🟢🟢🟢 Directly answers "how do you prevent hallucinations?" |
| **Files** | `web/dashboard/components.py` (+60), `web/dashboard/data_providers.py` (+50), `web/app_v2.py` (+10), `web/dashboard/__init__.py` (+5) |
| **Estimated lines** | ~125 |
| **Risk** | 🟢 Low — read-only display of existing data |
| **Test strategy** | Verify panel renders without error in Streamlit. Check data provider returns valid dict. |
| **Dependencies** | `CourseKnowledgeBase` loaded, `AgentEvaluator` available |

### A3: Pipeline Progress Visualization

| Aspect | Detail |
|:-------|:-------|
| **Feature** | EventBus-driven progress bar showing each agent step with latency |
| **Value** | 🟢🟢🟢🟢 Shows agents collaborating in real-time |
| **Files** | `web/v1/components.py` (+40), `web/dashboard/components.py` (+30), `web/v1/pipeline.py` (+10) |
| **Estimated lines** | ~80 |
| **Risk** | 🟢 Low — EventBus already captures all events |
| **Test strategy** | Run pipeline, verify events appear in timeline. Check progress bar reaches 100%. |
| **Dependencies** | EventBus (already integrated) |

### A4: Competition Demo Script Finalization

| Aspect | Detail |
|:-------|:-------|
| **Feature** | Exact 5-minute script with pre-seeded data, talking points, and Q&A responses |
| **Value** | 🟢🟢🟢🟢🟢 Prevents demo-day improvisation |
| **Files** | `docs/final_competition_story.md` (update with exact inputs/outputs) |
| **Estimated lines** | ~50 (documentation) |
| **Risk** | 🟢 Low — all necessary components exist |
| **Test strategy** | Run through script 3 times, timing each scene. Adjust if over 5 minutes. |
| **Dependencies** | All A1-A3 features implemented |

---

## Priority B: Good Enhancements

### B1: Extended Reading Resource Type

| Aspect | Detail |
|:-------|:-------|
| **Feature** | 6th resource type: curated extended reading list from `resources.json` |
| **Value** | 🟢🟢🟢 Shows knowledge breadth; connects to curated references |
| **Files** | `src/agents/resource_generation_agent.py` (+82), `web/v1/components.py` (+10) |
| **Estimated lines** | ~92 |
| **Risk** | 🟢 Low — reads existing JSON, no new models |
| **Test strategy** | Add test: verify `generate_extended_reading()` returns valid dict with references |
| **Dependencies** | `CourseKnowledgeBase` or hardcoded fallback refs |

### B2: StreamingSimulator Dashboard Integration

| Aspect | Detail |
|:-------|:-------|
| **Feature** | Integrate `StreamingSimulator` into Chat Demo content display |
| **Value** | 🟢🟢 Shows real-time content generation (streaming requirement) |
| **Files** | `web/chat_demo.py` (+30), `web/v1/pipeline.py` (+10) |
| **Estimated lines** | ~40 |
| **Risk** | 🟢 Low — simulator already tested |
| **Test strategy** | Toggle streaming mode, verify content appears progressively |
| **Dependencies** | `utils/streaming.py` (already exists) |

---

## Priority C: Defer — Do NOT Implement

### C1: Animation Storyboard Generator

**Why deferred:** Not enough competition value. 6 resource types (A1 + B1) already demonstrate multimodal capability. Animation storyboard is a prompt format — doesn't show actual animation.

### C2: Real-Time Learning Path Adjustment

**Why deferred:** Requires student interaction tracking infrastructure. Competition demo is about initial path generation, not mid-course adaptation. The personalization story is complete without this.

### C3: Voice / Audio Support

**Why deferred:** External dependencies (STT/TTS), adds complexity, dilutes the multi-agent architecture story which is our core differentiation.

---

## Implementation Order

```
Day 1: A1 (Spark provider switch) + A2 (Trust panel)
       → Test offline + Test with Spark API key

Day 2: A3 (Pipeline progress) + A4 (Demo script finalization)
       → Verify EventBus events + Run through script 3x

Day 3: B1 (Extended reading) + B2 (Streaming integration)
       → Only if time permits after A1-A4 complete

Day 4: Full rehearsal
       → 5-minute timed run × 5
       → Q&A practice
       → Fix any issues
```

---

## Risk Matrix

| Risk | Likelihood | Impact | Mitigation |
|:-----|:----------:|:------:|:-----------|
| Spark API key issues | Low | High | Verify 24h before; MockProvider backup |
| New panel breaks Dashboard layout | Low | Medium | Feature-flag new panel; can disable |
| Demo exceeds 5 minutes | Medium | Medium | Trim B-priority content; practice timing |
| Test regression from new code | Low | High | Run full test suite after each A-priority feature |
| Spark API slow response | Low | Medium | Pre-load demo data; show cached results |

---

## Success Criteria

After implementing Priority A:

1. ✅ `LLM_PROVIDER=xunfei` → real Spark calls visible in demo
2. ✅ `LLM_PROVIDER=mock` → same pipeline, different backend (zero code change)
3. ✅ `LLM_PROVIDER=none` → pure rule mode (demonstrates fallback)
4. ✅ Trust & Safety panel visible in Dashboard V2
5. ✅ Pipeline progress bar shows agent steps with real latency
6. ✅ 5-minute demo script executable without improvisation
7. ✅ 241 tests pass (all existing)
8. ✅ ~50 new test lines for new features

**Target: 95% competition readiness** (up from 89%).
