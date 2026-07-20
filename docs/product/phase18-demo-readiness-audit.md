# Phase 18.0 — Production Demo Readiness Audit

**Date:** 2026-07-20
**Status:** ⏳ **AWAITING HUMAN GATE** — READ-ONLY audit.

**Baseline:** v1.0.0 (da953fa), 2857 tests.

---

## 1. First-Time User Experience — Score: 7/10

### Current Flow (from open to first pipeline)

```
Step 1: Open app → Onboarding page
  🚀 "开始配置" or 🎭 "先体验 Demo"
  Time: 5 seconds

Step 2: Auth gate (Login / Register / Guest)
  Guest tab → "Continue as Guest" → instant access
  Time: 5 seconds

Step 3: Dashboard
  🎭 Demo Mode banner
  🎯 "Try These" — 3 clickable goals
  Time: 5 seconds

Step 4: Click goal → Learning tab → Run Pipeline
  Time: ~600ms (cold), ~5ms (warm)
```

**Total time-to-value: ~15 seconds.** ✅

### Asset Check

| Asset | Status | Notes |
|-------|--------|-------|
| Onboarding page (welcome + setup) | ✅ | 359 lines, 2 steps, provider selector |
| Demo path ("先体验 Demo") | ✅ | Sets mock provider, skips API key |
| Goal suggestions | ✅ | 3 clickable cards on Dashboard |
| Guest login | ✅ | Instant access, full pipeline |
| Streamlit Cloud | ✅ | Returns 303 (app exists) |
| Empty state handling | ✅ | History, workspace, profile all have messages |

### Gaps

| # | Gap | Severity |
|---|-----|----------|
| 1.1 | **Demo mode pipeline is rule-only** — no LLM. User sees generic content ("个性化学习教材 — mid_level") with generic quiz options. Doesn't showcase AI capabilities. | **P0** |
| 1.2 | **Onboarding has 9 providers** (hardcoded in `ONBOARDING_PROVIDERS`) while Settings has 10 (including `rule`). Divergent lists. | P1 |
| 1.3 | **Demo goal suggestions are static** — always the same 3 goals. Not context-aware. | P2 |

---

## 2. GitHub Showcase — Score: 6/10

### Asset Check

| Asset | Status | Evidence |
|-------|--------|----------|
| README hero + banner SVG | ✅ | Banner renders, badges display |
| CI badge | ✅ | `test.yml` workflow badge working |
| Test badge | ❌ | **Says 2804 — actual is 2857** |
| Architecture diagram | ✅ | ASCII art with 5 layers |
| Pipeline example | ✅ | Terminal demo with 6 agents |
| Feature table | ✅ | 7 features listed |
| Screenshots section | 🟡 | 5 SVG placeholders ("replace with actual screenshot") |
| Quick Start (4 methods) | ✅ | Streamlit Cloud, Win, Linux, Docker, Source |
| Release assets (v1.0.0) | 🟡 | Only Linux `.tar.gz` — **no Windows `.zip`** |
| Release title | ✅ | "A3-Agent v1.0.0 — First Stable Release 🎉" |
| Docs links | ✅ | 8 links across user/developer/release/demo |
| License | ✅ | MIT |

### Gaps

| # | Gap | Severity |
|---|-----|----------|
| 2.1 | **Test count badge stale: "2804" → "2857"** — 53 tests behind. README also says "2804 tests" in hero paragraph and feature table. | **P0** |
| 2.2 | **Screenshots are SVG text placeholders** — GitHub visitors see "A3 — Dashboard (replace with actual screenshot)" instead of real UI. | **P0** |
| 2.3 | **No Windows release asset for v1.0.0** — only `A3-Agent-v1.0.0-linux-x64.tar.gz`. Windows `.zip` only exists for v7.1.0/v7.1.1. | **P0** |
| 2.4 | **No CONTRIBUTING.md** — open-source contribution guide missing. | P2 |
| 2.5 | **Streamlit Cloud URL untested** — returns HTTP 303 (redirect), but app functionality not verified. | P1 |

---

## 3. AI Credibility — Score: 6/10

### What Works

| Capability | Demo Mode | Real LLM |
|-----------|-----------|----------|
| Pipeline execution | ✅ Rule-based | ✅ LLM-enhanced |
| Profile extraction | ✅ 6 dimensions | ✅ AI-enriched |
| Content generation | ✅ Templates | ✅ LLM-generated |
| Quiz generation | ✅ Generic questions | ✅ AI-personalized |
| Reflection | ✅ Rule summary | ✅ LLM analysis |
| AI Execution Card | ✅ Shows "rule" everywhere | ✅ Shows provider/model |
| Trace metadata | ✅ `source: rule` | ✅ `source: llm, provider: deepseek` |
| Provider badge | ✅ "🎭 Demo Mode" | ✅ "🤖 Deepseek · deepseek-chat" |

### Gaps

| # | Gap | Severity |
|---|-----|----------|
| 3.1 | **Demo mode doesn't showcase AI.** All 7 agents show `source: rule` in trace. AI Execution Card says "Agents (Rule): 7". User can't see AI capabilities without configuring a real LLM. | **P0** |
| 3.2 | **No pre-configured demo API key.** The demo uses mock — no way to show "Here's what real AI looks like" without user bringing their own key. | P1 |
| 3.3 | **Token count shows 0 in demo.** `run_info.tokens_used=0` — looks broken, not "offline mode." | P1 |

---

## 4. Benchmark Data — Score: 8/10

### Collected Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| **Tests** | **2857** | 100% pass rate, 0 failures |
| **Pipeline latency (cold)** | ~600ms | First run after fresh start |
| **Pipeline latency (warm)** | ~5ms | Subsequent runs (DB/memory cached) |
| **Agents per pipeline** | 7 | ProfileAgent → PlannerAgent → ContentGenerator → ResourceAgent → ReviewAgent → ReflectionAgent → Memory |
| **Trace events** | 9 | Includes System + Workflow events |
| **Production providers** | 8 | Anthropic, DeepSeek, Google, Grok, Kimi, OpenAI, Qwen, Spark |
| **Demo providers** | 2 | mock, rule |
| **Agent files** | 15 | Including PPT/Image/Video generators |
| **Test files** | 95 | All passing |
| **UI lines** | 901 | `web/app.py` |
| **Release size (Linux)** | 86 MB | `.tar.gz` |
| **Release size (Win v7.1.1)** | 54 MB | `.zip` |

### Gaps

| # | Gap | Severity |
|---|-----|----------|
| 4.1 | **Windows release for v1.0.0 is missing** — latest tag only has Linux asset. | **P0** |
| 4.2 | **No benchmark suite** — latency is ad-hoc measured, not from a dedicated benchmark script. | P2 |

---

## 5. Demo Flow Assessment — Score: 6/10

### Demo Script Analysis (`docs/demo/demo-script.md`)

| Scene | Status | Issue |
|-------|--------|-------|
| 1: First Launch (30s) | ✅ | Onboarding now uses full page |
| 2: Create Account (30s) | ✅ | Guest path available for faster demo |
| 3: Dashboard (30s) | ✅ | Now has goal suggestions + memory card |
| 4: Run Pipeline (2 min) | 🟡 | References 7 hardcoded stages → now trace-driven |
| 5: Browse History (30s) | 🟡 | Now has replay, not mentioned |
| 6: Browse Workspace (30s) | ✅ | Artifacts still work |
| 7: Configure LLM (1 min) | 🟡 | 8 providers → script mentions 3 |
| 8: Profile View (30s) | ✅ | Memory stats now present |

### Timeline

```
Open → Register → Demo goal click → Pipeline complete → Results view
  ~5s      ~5s         ~1s              ~0.6s           scroll

Total demo time: ~30 seconds (guest path)
Full guided demo: ~5 minutes (all 8 scenes)
```

### Gaps

| # | Gap | Severity |
|---|-----|----------|
| 5.1 | **Demo script is Phase 10.4-D era** — doesn't mention quiz, reflection, history replay, memory card, AI Execution Card, trace-driven progress, goal suggestions, provider badge, demo mode badge. | **P0** |
| 5.2 | **No 30-second "elevator pitch" demo path** — fastest path still requires register + click + wait for pipeline. | P1 |
| 5.3 | **Demo mode content is generic** — quiz options are "To solve specific problems efficiently" etc. Doesn't demonstrate AI intelligence. | P1 |

---

## 6. Score Summary

| Area | Score | Key Gap |
|------|-------|---------|
| 1. First-Time UX | **7/10** | Demo mode is rule-only — doesn't showcase AI |
| 2. GitHub Showcase | **6/10** | Stale badges; placeholder screenshots; no Windows asset |
| 3. AI Credibility | **6/10** | Can't see real AI without user API key |
| 4. Benchmark | **8/10** | Strong metrics; missing Windows release |
| 5. Demo Flow | **6/10** | Demo script stale; no 30-second pitch path |

**Demo Readiness: 6.6/10**

---

## 7. P0 Fix Plan

| # | Fix | Area | Effort |
|---|-----|------|--------|
| P0-1 | **Update test count: 2804 → 2857** in README badge + hero + feature table | Area 2 | +3 |
| P0-2 | **Build Windows release for v1.0.0** — `A3-Agent-v1.0.0-win64.zip` | Area 2/4 | Manual (Wine build) |
| P0-3 | **Replace SVG placeholders with real screenshots** — 5 PNGs of actual UI | Area 2 | Manual (browser screenshots) |
| P0-4 | **Update demo script** for Phase 16-17 features: quiz, reflection, replay, memory card, AI card, goal suggestions, provider badge | Area 5 | ~20 lines |
| P0-5 | **Add pre-configured demo LLM path** — use env var `DEMO_API_KEY` to showcase real AI in demo mode | Area 1/3 | ~15 lines |

---

## 8. Recommended Demo Flow (5 minutes)

```
0:00 — Open app → 🎭 "先体验 Demo"
0:05 — Guest login → Dashboard
0:10 — 🎯 Click "Learn Python basics"
0:15 — Pipeline runs → 7 agents, 9 trace events
0:30 — 📋 "Session Replay" — open full results
1:00 — 🤖 "AI Execution Card" — show per-agent LLM usage
1:30 — ✅ Quiz — answer 3 questions, see score
2:00 — 💭 Reflection — AI analysis
2:30 — 📜 History — browse past runs with replay
3:00 — ⚙️ Settings — 8 LLM providers, test connection
3:30 — 🧠 Memory — "AI remembers 12 concepts"
4:00 — 📂 Workspace — downloadable artifacts
4:30 — 🏠 Dashboard — goal suggestions, stats
5:00 — Q&A / Wrap-up
```

---

## ⏳ Awaiting Human Gate

**5 P0 items: README badges, Windows release, real screenshots, demo script update, demo LLM path.**
