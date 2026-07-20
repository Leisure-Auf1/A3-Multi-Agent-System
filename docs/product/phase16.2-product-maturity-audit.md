# Phase 16.2 — Product Maturity Upgrade Audit

**Date:** 2026-07-20
**Status:** ⏳ **AWAITING HUMAN GATE** — READ-ONLY audit, no code changes.

**Baseline:** v1.0.0 (da953fa), 2767 tests, Phase 16.1 learning loop complete.

---

## Audit Scope

5 audit areas: Memory Visibility, History Experience, Provider Transparency, First Launch Experience, Demo Readiness.

All evidence from actual code paths: `web/app.py`, `web/settings_tab.py`, `web/onboarding_page.py`, `src/api/v2/pipeline.py`, `src/services/learning_pipeline.py`, `src/data/learning_records.py`, `src/data/db.py`.

---

## 1. Memory Visibility — Score: 4/10

### What Works

| Evidence | File | Lines |
|----------|------|-------|
| Profile tab shows 6-dimension learning profile + Memory Stats (interactions, mastery, sessions) | `web/app.py` | 613-652 |
| Pipeline API returns `memory_saved: bool` | `src/api/v2/pipeline.py` | 52 |
| Pipeline service writes memory via A3Workflow | `src/services/learning_pipeline.py` | 71-80 |
| StudentMemoryStore has `interaction_count`, `mastery_map`, `session_summaries` | Profile tab try block | 639-652 |

### Gaps

| # | Gap | Severity | Impact |
|---|-----|----------|--------|
| 1.1 | **`memory_saved=true` not displayed in UI.** Pipeline response has `memory_saved: bool` but `_render_pipeline_results` never shows it. User runs pipeline → "memory saved" is invisible. | P0 | User has no idea AI remembers them |
| 1.2 | **No dedicated "Memory" view.** Profile tab has stats buried in a `try/except` expander. No tab or widget that says "Here's what AI remembers about you." | P0 | Memory is invisible unless user discovers Profile tab |
| 1.3 | **Dashboard shows sessions/score/time, not memory.** The 4 metrics on Dashboard quantify usage but not learning. No mastery map, weak areas, or learning velocity. | P1 | Dashboard is operational, not learning-focused |
| 1.4 | **Memory stats use `.exists()` fallback** — if `store.exists(user_id)` returns false, the entire block is skipped silently. New user sees nothing. | P1 | Memory zero-state is invisible |

### Root Cause

The Veritas-Core memory layer (`veritas/memory/`) stores rich data: `mastery_map`, `weak_points`, `session_summaries`, `profile_history`, `learning_behavior.interaction_count`. But the UI only exposes it through a fragile `try/except` block in Profile tab. The API response `memory_saved` flag is never rendered.

---

## 2. History Experience — Score: 3/10

### What Works

| Evidence | File | Lines |
|----------|------|-------|
| History tab lists past runs with agent/action/date/score/duration | `web/app.py` | 514-545 |
| Learning records persisted to SQLite with user_id FK | `src/data/db.py` | 82-93 |
| Workspace tab shows filesystem artifacts (materials, ppt, images, videos) | `web/app.py` | 552-555 |
| Pipeline service saves plan/profile/resources/eval as JSON to workspace | `src/services/learning_pipeline.py` | 122-173 |

### Gaps

| # | Gap | Severity | Impact |
|---|-----|----------|--------|
| 2.1 | **History shows metadata only — no content replay.** LearningRecordResponse has `id, agent, action, course_id, score, created_at`. No plan, no content, no quiz result, no reflection. User can see they ran "pipeline → Learn Python" but can't see what was generated. | P0 | History is a tombstone, not a journal |
| 2.2 | **`result_json` field exists in DB but unused in API.** `learning_records.result_json TEXT DEFAULT '{}'` stores the full result, but `get_history()` and `/history` endpoint never return it. | P0 | Data is persisted but unreachable |
| 2.3 | **No replay capability.** Clicking a history item shows score + duration only. No way to re-render the plan/content/quiz from a past run. | P0 | User must re-run pipeline to see results again |
| 2.4 | **Workspace artifacts not linked to history runs.** Workspace files are named `plan_{run_id}.json` but History doesn't show `run_id`. Siloed data. | P1 | User can browse files but can't connect them to sessions |
| 2.5 | **Quiz results not in history at all.** Quiz is rendered in `_render_pipeline_results` but never persisted to learning_records. Quiz is session-only. | P1 | Close browser → lose quiz |

### Root Cause

History API (`/api/v2/learning/history`) returns a minimal `LearningRecordResponse` that strips `result_json` and `duration_ms`. The DB schema supports rich data but the API deliberately discards it. The pipeline service writes 5 artifacts to workspace (profile.json + plan.json + plan.md + resources.json + eval.json) but the History tab never references them.

---

## 3. Provider Transparency — Score: 7/10

### What Works

| Evidence | File | Lines |
|----------|------|-------|
| Settings: 8 production providers with emoji, desc, models, status | `web/settings_tab.py` | 110-146 |
| Settings: Provider selector, model selector, API key, test connection, save | `web/settings_tab.py` | 150-306 |
| Settings: Troubleshooting hints with error-specific suggestions | `web/settings_tab.py` | 394-414 |
| Pipeline results: "AI Engine Details" with engine, model, generation time, fallback, tokens | `web/app.py` | 342-360 |
| Model registry: Capability badges, context length, streaming support | `web/settings_tab.py` | 436-477 |
| Provider status tracker: 🟢/🔴/⚪ per provider | `web/settings_tab.py` | 51-62 |

### Gaps

| # | Gap | Severity | Impact |
|---|-----|----------|--------|
| 3.1 | **Active provider not visible on Dashboard/Learning tabs.** To know which model is running, user must navigate to Settings. | P1 | Model transparency is buried behind navigation |
| 3.2 | **Per-agent provider breakdown not shown.** All agents use same provider — but user doesn't know this. Could be confusing if Orchestrator routes different agents to different models. | P2 | Future Orchestrator routing would be invisible |
| 3.3 | **No cost/token summary on Dashboard after pipeline runs.** Pipeline shows `tokens_used` in run_info but Dashboard summary is all-time aggregate. No per-run cost visibility. | P1 | User can't track cost of individual learning sessions |

### Root Cause

Provider info (`run_info`) is rendered in pipeline results expander but not surfaced to Dashboard or Learning tab headers. The `ProviderStatusTracker` exists but is Settings-only. Token tracking is all-time aggregate — no per-run breakdown.

---

## 4. First Launch Experience — Score: 5/10

### What Works

| Evidence | File | Lines |
|----------|------|-------|
| Onboarding gate: 2-step (Welcome → Provider setup) | `web/app.py` | 108-112, `web/onboarding_page.py` |
| "先体验 Demo" button — skip setup, use mock provider | `web/onboarding_page.py` | 163-168 |
| Empty states: "No learning history yet", "No profile yet" | `web/app.py` | 529, 654 |
| Error-friendly: test connection with troubleshooting hints | `web/onboarding_page.py` | 299-313, `web/settings_tab.py` | 394-414 |

### Gaps

| # | Gap | Severity | Impact |
|---|-----|----------|--------|
| 4.1 | **Two divergent provider lists.** Onboarding uses hardcoded `ONBOARDING_PROVIDERS = ["deepseek", "openai", ...]` while Settings uses `PROVIDER_META` system. Onboarding `PROVIDER_MODELS` only has 4 providers (deepseek, openai, spark, mock). Settings has all 8. | P0 | Onboarding shows incomplete provider catalog |
| 4.2 | **No guided example.** After onboarding, user lands on Dashboard with empty text area. Placeholder says "I'm a CS student..." but no pre-filled suggestion. | P0 | New user doesn't know what to type |
| 4.3 | **Empty Dashboard is a dead end.** 4 metrics at 0/--. Text input. "Start Learning" button. That's it. No "Try this", no "See what A3 can do", no demo walkthrough. | P0 | 5-minute value realization fails |
| 4.4 | **Profile tab empty state is weak.** "No profile yet. Run the Learning Pipeline to create one!" — but doesn't explain what a profile IS or why it matters. | P1 | Feature value is not explained |

### Root Cause

Onboarding page (Phase 5.0) predates Settings redesign (Phase 13.2). Their provider lists diverged. Dashboard (Phase 10.4-D) was designed as a command center for active users, not a welcoming first screen. The "Quick Start" section assumes user knows what to write.

---

## 5. Demo Readiness — Score: 5/10

### What Works

| Evidence | File | Lines |
|----------|------|-------|
| Demo mode works end-to-end: register → pipeline → plan/content/quiz/reflection | Full user journey |
| Pipeline produces real output in demo mode (rule-based, no API key) | `src/core/provider_factory.py` | 70-110 |
| Quiz works in mock mode (rule-based questions) | `web/components/quiz_panel.py` | 81-95 |
| All 6 tabs functional in demo mode | `web/app.py` tab routing |

### Gaps

| # | Gap | Severity | Impact |
|---|-----|----------|--------|
| 5.1 | **No pre-populated demo goal.** User must type their own goal. No "Click here to try a demo lesson" button. | P0 | 5-minute value window: 2 min wasted on "what to type?" |
| 5.2 | **No guided tour.** No tooltips, no walkthrough, no "next step" guidance. Tabs are self-serve. | P1 | User must explore randomly |
| 5.3 | **Pipeline takes 3+ clicks.** Enter goal → click "Run Pipeline" → wait → scroll. No one-click "Show me what this does" path. | P1 | Time-to-value: ~3 minutes |
| 5.4 | **Dashboard doesn't advertise pipeline.** Only text input + button. No screenshot, no example output, no "what you'll get" preview. | P2 | Dashboard looks like a chat box, not a learning system |

### Root Cause

The product was built for demo at competitions (Phase 8.0's `competition_demo.py` one-click pipeline), but when that was removed for production UI (Phase 10.1), the one-click path was lost. The current Dashboard is a command center for repeat users, not a discovery tool for new users.

---

## Score Summary

| Area | Score | Key Gap |
|------|-------|---------|
| 1. Memory Visibility | **4/10** | `memory_saved` flag invisible; no "what AI remembers" view |
| 2. History Experience | **3/10** | Metadata-only history; no replay; `result_json` unused |
| 3. Provider Transparency | **7/10** | Good settings UI; missing Dashboard-level visibility |
| 4. First Launch Experience | **5/10** | Divergent provider lists; no guided example |
| 5. Demo Readiness | **5/10** | No one-click demo; no pre-populated goal |

**Overall Product Maturity: 4.8/10 (weighted: 24/50)**

### Phase 16.2 Target: 7.0/10 → 9.0/10

---

## Prioritized Fix Plan

### P0 (3 items) — Missing value signals, blocks user journey

| # | Fix | Area | Effort | Lines |
|---|-----|------|--------|-------|
| P0-1 | **Unify provider lists.** Replace `ONBOARDING_PROVIDERS`/`PROVIDER_MODELS` with `PROVIDER_META` import from settings_tab. Show all 8 providers in onboarding. | Area 4 | Low | ~15 |
| P0-2 | **Smart goal suggestions on Dashboard.** Show 3 clickable example goals ("Learn Python basics", "Understand machine learning", "Master data structures"). Click → auto-fills and jumps to Learning tab. | Area 4/5 | Low | ~20 |
| P0-3 | **Show `memory_saved` in pipeline results.** Add a badge/indicator in `_render_pipeline_results`: "🧠 AI remembered this session" when `memory_saved=true`. | Area 1 | Low | +5 |

### P1 (5 items) — Enrichment, improves but doesn't block

| # | Fix | Area | Effort | Lines |
|---|-----|------|--------|-------|
| P1-1 | **History with replay.** Extend `LearningRecordResponse` to include `result_json` and `run_id`. Add "Replay" button in History that renders plan/content/eval from stored JSON. | Area 2 | Medium | ~40 |
| P1-2 | **Memory Dashboard card.** Add a metrics row on Dashboard: "🧠 Mastery: 12 concepts", "📝 Weak: 3 areas", "📈 Sessions: 5". Pull from StudentMemoryStore. | Area 1 | Medium | ~25 |
| P1-3 | **Active provider badge on Dashboard.** Show small badge: "🤖 deepseek-chat" (or "🎭 Demo Mode") in sidebar or Dashboard header. | Area 3 | Low | +8 |
| P1-4 | **Per-run token display in History.** Add `duration_ms` and `result_json` token count to history items. | Area 2/3 | Low | +5 |
| P1-5 | **Profile tab zero-state explanation.** When `store.exists(user_id)` is false, show "Run the Learning Pipeline to create your personalized learning profile. A3 will analyze your learning style, pace, and knowledge gaps." | Area 4 | Low | +5 |

### P2 (3 items) — Polish, nice-to-have

| # | Fix | Area | Effort | Lines |
|---|-----|------|--------|-------|
| P2-1 | **One-click demo button on Dashboard.** "🎯 Quick Demo: Learn Python generators" → runs pipeline with pre-set goal. | Area 5 | Low | ~15 |
| P2-2 | **Link History runs to Workspace artifacts.** Show "📂 View artifacts" link in History expander → jump to Workspace tab filtered by run_id. | Area 2 | Medium | ~20 |
| P2-3 | **Per-agent provider transparency (future-proof).** Add agent-level provider info to run_info when Orchestrator routes to different models. | Area 3 | Low | ~10 |

---

## Implementation Plan (if approved)

### Wave 1: P0 fixes (3 items, ~40 lines, 2 files)
```
web/onboarding_page.py  — Unify provider lists
web/app.py              — Goal suggestions + memory_saved badge
```

### Wave 2: P1 fixes (5 items, ~83 lines, 3 files)
```
web/app.py              — Memory Dashboard card + active provider badge
src/api/v2/learning.py  — Extended LearningRecordResponse with result_json
web/app.py              — History replay rendering + Profile zero-state
```

### Wave 3: P2 fixes (3 items, ~45 lines, 2 files)
```
web/app.py              — One-click demo + History→Workspace links
src/api/v2/pipeline.py  — Per-agent provider info in run_info
```

### Test Plan: ~15 new tests in `tests/test_phase16_maturity.py`

| # | Test |
|---|------|
| 1-3 | Goal suggestions rendered in Dashboard |
| 4 | `memory_saved` shown in pipeline results |
| 5-6 | History API returns result_json and run_id |
| 7-8 | History replay renders plan/content |
| 9-10 | Memory Dashboard card with mastery/weakness/sessions |
| 11 | Active provider badge on Dashboard |
| 12-13 | Onboarding provider list matches Settings |
| 14 | Profile zero-state message |
| 15 | One-click demo button on Dashboard |

---

## Architecture Impact

| Component | Modified? | How |
|-----------|----------|-----|
| `src/core/` | ❌ No | — |
| A3Workflow | ❌ No | — |
| Agents | ❌ No | — |
| Veritas-Core | ❌ No | — |
| `web/app.py` | ✅ Yes | Goal suggestions, memory_saved badge, memory card, provider badge, one-click demo, history replay |
| `web/onboarding_page.py` | ✅ Yes | Unify provider lists |
| `src/api/v2/learning.py` | ✅ Yes | Extended history response |
| **Total** | 3 files | ~168 lines |

---

## Before/After User Journey

### Before (Phase 16.1 — 8.0/10)
```
Onboarding → "I don't know what to type" → Empty Dashboard
  → Type goal manually → Run Pipeline
  → See plan + content + quiz + reflection ✅
  → memory_saved=true (invisible ❌)
  → History shows "pipeline — run" with score only ❌
  → Settings shows real provider 👍
  → Dashboard doesn't show provider or memory ❌
```

### After (Phase 16.2 target — 9.0/10)
```
Onboarding → All 8 providers visible ✅
  → "先体验 Demo" or configure real key
Dashboard → "Try: Learn Python basics" click ✅
  → "🤖 deepseek-chat" badge ✅
  → "🧠 12 concepts mastered · 3 weak areas" ✅
Run Pipeline → "🧠 AI remembered this session" ✅
History → "Replay" button → see plan, content, eval ✅
  → "📂 View artifacts" link → Workspace ✅
Profile → "Run the Learning Pipeline to create your learning profile" ✅
```

---

## ⏳ Awaiting Human Gate

**3 waves, 11 fixes, 15 tests, 3 files, ~168 lines. 0 architecture changes.**

Approve to proceed with implementation plan.
