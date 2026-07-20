# Phase 16.2-B — Experience Polish Audit

**Date:** 2026-07-20
**Status:** ⏳ **AWAITING HUMAN GATE** — READ-ONLY audit, no code changes.

**Baseline:** v1.0.0 (da953fa), 2804 tests, Phase 16.2-A completed.

---

## Audit Scope

4 areas: Provider Transparency, First Launch UX, Empty States, GitHub Demo Experience.

---

## 1. Provider Transparency — Score: 5/10

### Current State

| Location | Provider Visible? | Evidence |
|----------|------------------|----------|
| **Sidebar** | ❌ | Only user name + tab nav + logout. No model indicator. (`web/app.py:131-158`) |
| **Dashboard** | ❌ | Demo banner ("Demo Mode") only — no active model name. (`web/app.py:216-223`) |
| **Learning tab** | 🟡 | `run_info` expander shows engine/model after pipeline completes. Not visible before/on first view. (`web/app.py:415-440`) |
| **Settings** | ✅ | Full provider center with 8 providers, status, model selector, test connection, troubleshooting. (`web/settings_tab.py`) |

### Gaps

| # | Gap | Severity |
|---|-----|----------|
| 1.1 | **No active provider badge in sidebar.** User must navigate to Settings to see which model is running. Most apps show "GPT-4" or "Claude" in the header. | **P0** |
| 1.2 | **Dashboard says "Demo Mode" but not which model when configured.** If user configured DeepSeek, Dashboard still shows generic "Demo Mode" because it only checks `cfg.provider in ("mock", "rule")`. Should show "🤖 deepseek-chat" instead. | **P0** |
| 1.3 | **No real-time model confirmation during pipeline.** User can't verify "yes, this content came from DeepSeek" during pipeline execution — only after (run_info expander). | P1 |

### Root Cause

Sidebar was designed in Phase 10.1 (pre-provider-transparency). Dashboard demo indicator was added in Phase 16.2-A but uses simplistic check (`is_demo = not cfg.is_configured or cfg.provider in ("mock", "rule")`) without showing the actual provider name when configured.

---

## 2. First Launch UX — Score: 4/10

### Current State

**Flow:** App starts → Onboarding gate → Auth gate → Dashboard

| Step | Current UX | Issues |
|------|-----------|--------|
| 1. Onboarding gate | Thin intro text + 2 buttons: "Get Started" / "Configure LLM First" | `_render_onboarding_gate()` is a generic 10-line gate, NOT the full onboarding page. The full onboarding page (`web/onboarding_page.py`, 359 lines) exists but is only reachable via "Configure LLM First" button. |
| 2. Auth gate | Login/Register/Guest tabs | No "skip" or "continue without account" option on auth screen. Guest login exists but is hidden in a tab. |
| 3. Registration | Email + password + name | Works well. `_render_register()` handles validation. |
| 4. Post-login Dashboard | Demo banner + goal suggestions + custom goal | Phase 16.2-A improvements. Still no guided tour. |

### Gaps

| # | Gap | Severity |
|---|-----|----------|
| 2.1 | **Full onboarding page is buried.** The `welcome → setup` flow in `web/onboarding_page.py` (359 lines) is a much better experience than the 10-line gate. But the gate doesn't use it — it has its own "Get Started" that just sets `_onboarded = True` and jumps to auth. | **P0** |
| 2.2 | **Auth gate has no "skip" option.** User sees Login/Register/Guest tabs. "Guest" is in a separate tab. A "Continue as Guest" button visible on the login tab would reduce friction. | **P0** |
| 2.3 | **Onboarding gate is skipped EVERY session after first.** `st.session_state._onboarded` is persistent within session. If user closes browser and reopens, auth gate shows directly — onboarding is lost. | P2 |
| 2.4 | **No error recovery in auth flow.** If registration fails (email taken), user gets `st.error("Registration failed: ...")` but the form stays filled — good. No "forgot password" flow. | P1 |
| 2.5 | **Guest login doesn't set display context.** Guest user sees "Demo Mode" banner + goal suggestions — same as registered user. No distinction like "👤 Guest Session — create an account to save your progress." | P1 |

### Root Cause

Two onboarding systems: the gate (`web/app.py:174-205`, Phase 10.1 era) and the full page (`web/onboarding_page.py`, Phase 5.0). They were never unified. The gate was a quick replacement for the full onboarding page during UI unification.

---

## 3. Empty States & Error Handling — Score: 6/10

### Current State

| State | Handling | Quality |
|-------|----------|---------|
| Empty history | "No learning history yet. Run the Learning Pipeline to get started!" | ✅ Good |
| Empty workspace | "No {category} artifacts yet..." | ✅ Good |
| No profile | "No profile yet. Run the Learning Pipeline to create one!" | ✅ Good |
| Dashboard (first login) | 0's across stats + demo banner + goal suggestions | ✅ Good |
| Missing API key (Settings) | "No AI provider configured — running in Demo mode" | ✅ Good |
| Failed LLM connection | Error with troubleshooting hints in expander | ✅ Good — `_get_error_hints()` in settings_tab.py handles 401/timeout/rate/model errors |
| Pipeline error (401) | "Session expired. Please log in again" + Go to Login button | ✅ Good |
| Pipeline error (429) | "Usage limit reached" + daily budget suggestion | ✅ Good |
| Pipeline error (422) | "Invalid input" | 🟡 Adequate |
| Pipeline error (500) | "Server error" + retry button | ✅ Good |
| Import error (Settings) | "Settings module not available" | ✅ Good |
| Import error (Workspace) | "Workspace browser will be available after running..." | ✅ Good |
| Workspace load error | "Could not load workspace: {e}" | 🟡 Adequate |

### Gaps

| # | Gap | Severity |
|---|-----|----------|
| 3.1 | **No "Forgot password" flow.** Registration shows email-taken error. Login shows "Login failed: ..." but no password reset link. | P1 |
| 3.2 | **Empty Dashboard could be more welcoming.** Shows 0's everywhere — less intimidating would be showing the goal suggestions ABOVE the stats (reorder: demo banner → goal suggestions → stats). | P2 |
| 3.3 | **Quiz unavailable message shows only in expander.** When `create_provider()` returns None, quiz shows "Quiz unavailable — configure an LLM provider in Settings" as a caption. Very subtle — user may miss it. | P2 |

### Root Cause

Error handling is one of the strongest areas. Phase 10.4-D error handler (`handle_api_error`) covers 401/429/422/500 with recovery actions. Settings tab has `_get_error_hints()` with provider-specific troubleshooting. Main gap is auth-side error recovery (no password reset).

---

## 4. GitHub Demo Experience — Score: 4/10

### Current State

| Element | Status | Evidence |
|---------|--------|----------|
| README hero | ✅ | Banner SVG + badge row |
| Pipeline example | ✅ | ASCII terminal demo with 7 agent stages |
| Badges | ❌ | "tests-2661/2661" → should be **2804**. All badges need updating. |
| Install instructions | ✅ | Streamlit Cloud, Windows, Linux, Docker, source |
| Architecture diagram | ✅ | ASCII art (API → Security → Pipeline → Agent → Data) |
| Doc links | ✅ | Getting started, installation, FAQ, architecture, API, demo script, changelog |
| Current feature list | ❌ | Lists 7 features but **none from Phase 16.1/16.2**: no quiz, no reflection, no history replay, no memory card, no demo goal suggestions, no trace-driven progress |
| Demo script | 🟡 | `docs/demo/demo-script.md` exists but references pre-Phase-16.1 state: 8 scenes, no quiz, no reflection, no replay. Hardcoded PIPELINE_STAGES, not trace-driven. |
| Getting started | 🟡 | `docs/user/getting-started.md`: mentions "Quick Start" (→ now "Custom Goal"). Doesn't mention goal suggestions or "Try These" cards. |
| Screenshots/GIFs | ❌ | Zero visual assets. No product screenshot, no demo GIF, no animation. |

### Gaps

| # | Gap | Severity |
|---|-----|----------|
| 4.1 | **Badges are stale.** Test count: 2661 → 2804. Release: v1.0.0 (tag exists but release assets may be stale). | **P0** |
| 4.2 | **README missing Phase 16.1/16.2 features.** No mention of: interactive quiz with error analysis, reflection output, history replay, memory card, demo goal suggestions, trace-driven progress. Feature table says "2661 tests" when it's now 2804. | **P0** |
| 4.3 | **No product screenshots.** README has architecture ASCII art and terminal demo text — but no visual of the actual UI. GitHub visitors can't see what the product looks like. | **P0** |
| 4.4 | **Demo script is stale.** References hardcoded PIPELINE_STAGES (pre-Phase 16.1). Doesn't cover quiz, reflection, replay, or memory card. References "2640 tests" (Phase 10.4-D era). | P1 |
| 4.5 | **Getting-started doc is stale.** "Quick Start" was renamed to "Custom Goal" in Phase 16.2-A. Doesn't mention "Try These" goal cards. | P1 |

### Root Cause

Phase 10.4-E (Release Documentation) generated docs at 2640 tests. Phase 11.0–12.0 updated README for v1.0.0 release. Phase 13.2 added model transparency. Phase 14–15 added LLM wiring + unification. Phase 16.0–16.2 added quiz/reflection/replay/memory/demo. None of these updated the README or docs.

---

## 5. Score Summary

| Area | Score | Key Gap |
|------|-------|---------|
| 1. Provider Transparency | **5/10** | No active provider visible in sidebar/Dashboard |
| 2. First Launch UX | **4/10** | Full onboarding page buried; auth gate has no quick guest |
| 3. Empty States | **6/10** | Strong error handling; minor auth recovery gaps |
| 4. GitHub Demo Experience | **4/10** | Stale badges; no screenshots; docs from Phase 10 era |

**Overall Experience Polish: 4.8/10**

### Phase 16.2-B Target: 7.0/10 (→ cumulative 9.0/10 product maturity)

---

## Prioritized Fix Plan

### P0 (5 items) — Visitor/user can't see core value

| # | Fix | Area | Effort |
|---|-----|------|--------|
| P0-1 | **Show active provider in sidebar.** Below user name: `🤖 deepseek-chat` or `🎭 Demo Mode`. Use `load_llm_config()` to detect. | Area 1 | Low (+5) |
| P0-2 | **Dashboard: show real provider name instead of generic "Demo Mode."** When configured: `🐋 DeepSeek Chat` badge. When demo: `🎭 Demo Mode — rule-based agents only.` | Area 1 | Low (+5) |
| P0-3 | **Update README badges + feature list.** Test count → 2804. Add: Quiz, Reflection, History Replay, Memory Card, Goal Suggestions, Trace Progress. | Area 4 | Low (+15) |
| P0-4 | **Add product screenshots to README.** Dashboard with goal suggestions, Pipeline results with reflection+quiz, History replay. ASCII art is good but visuals are essential for GitHub. | Area 4 | Medium (+5 screenshots) |
| P0-5 | **Fix onboarding: use full onboarding page, not thin gate.** Replace `_render_onboarding_gate()` with `web.onboarding_page.render_onboarding_page()` import. Or add a "Skip to Demo" option directly on the gate. | Area 2 | Low (+10) |

### P1 (4 items) — Documentation and UX refinement

| # | Fix | Area | Effort |
|---|-----|------|--------|
| P1-1 | **Update `docs/user/getting-started.md`** for Phase 16.2 features: goal suggestions, reflection, quiz, memory card, history replay. | Area 4 | Low (+10) |
| P1-2 | **Update `docs/demo/demo-script.md`** for Phase 16.2: add quiz scene, reflection scene, replay scene. Update agent names to trace-driven. Update test count. | Area 4 | Low (+15) |
| P1-3 | **Add "Continue as Guest" button on Login tab.** Reduce friction — 1 click instead of switching tabs. | Area 2 | Low (+3) |
| P1-4 | **Guest login: show session context.** "👤 Guest Session — create a free account to save your progress and access history replay." | Area 2 | Low (+3) |

### P2 (2 items) — Polish, nice-to-have

| # | Fix | Area | Effort |
|---|-----|------|--------|
| P2-1 | **Reorder Dashboard: goal suggestions BEFORE stats.** New users see "Try These" first, not zero-stats. | Area 3 | Low (+5) |
| P2-2 | **Auth: "forgot password" flow.** Simple: show "Contact admin" or "Create new account" suggestion on login failure. | Area 3 | Low (+3) |

---

## Implementation Plan

### Wave 1: P0 fixes (5 items, ~40 lines + 5 screenshots)
```
web/app.py             — Provider badge in sidebar + Dashboard
README.md              — Update badges + feature table + screenshots
web/app.py             — Unify onboarding gate with full page
```

### Wave 2: P1 fixes (4 items, ~31 lines)
```
docs/user/getting-started.md   — Update for Phase 16.2
docs/demo/demo-script.md       — Update for Phase 16.2
web/components/auth.py         — Guest button + guest context
```

### Wave 3: P2 fixes (2 items, ~8 lines)
```
web/app.py  — Reorder Dashboard
web/components/auth.py  — Password reset suggestion
```

### Test Plan: ~15 new tests in `tests/test_phase16_experience.py`

---

## Architecture Impact

| Component | Modified? |
|-----------|----------|
| `src/core/` | ❌ No |
| A3Workflow | ❌ No |
| Agents | ❌ No |
| Veritas-Core | ❌ No |
| `web/app.py` | ✅ Yes (sidebar, dashboard, onboarding) |
| `web/components/auth.py` | ✅ Yes (guest) |
| `README.md` | ✅ Yes |
| `docs/` | ✅ Yes |

---

## ⏳ Awaiting Human Gate

**3 waves, 11 fixes, 15 tests, ~79 code lines + 5 screenshots + doc updates. 0 architecture changes.**

Approve to proceed with implementation plan.
