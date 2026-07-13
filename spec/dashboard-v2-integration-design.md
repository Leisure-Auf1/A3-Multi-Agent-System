# Dashboard V2 — Integration Design

> Phase 7.2 — Design Only (No Implementation)
> Date: 2026-07-13

---

## 1. Preflight

| Item | Value |
|:-----|:------|
| **Git Branch** | `main` |
| **HEAD SHA** | `6a970f7` |
| **Workspace** | 3 untracked: `checkpoints/dashboard-v2-design.md`, `spec/dashboard-v2-architecture.md`, `web/dashboard/` |
| **Risk Tier** | 🟡 MEDIUM (untracked files) |
| **Test Suite** | 233 passed, 4 pre-existing failures in `test_review_gate.py` |
| **Streamlit Entrypoint** | `web/app.py` (248 lines, V1: 5 panels) |
| **Dashboard V2 Status** | Designed + verified (29/29 checks), >1,100 lines across 3 files |

---

## 2. Scan Result

### 2.1 Current V1 Panels (app.py)

| # | Panel | Key Pattern |
|:--|:------|:------------|
| P1 | 画像采集进度 (Completeness) | `st.progress(pct)` + filled/total dims |
| P2 | 动态画像卡片 (Dynamic Profile) | 6-column `st.metric` with emoji map |
| P3 | 学习路径可视化 (Learning Path) | Node iteration with mastery-based status colors |
| P4 | 推荐资源卡片 (Resource Cards) | `st.columns` resource cards with priority stars |
| P5 | Agent Trace (EventBus timeline) | `st.expander` + timestamp-agent-action list |

### 2.2 V1 Initialization Flow

```
st.set_page_config() → st.title()
↓
AgentEventBus.get_instance()
↓
@st.cache_resource → create all 6 agents
↓
Sidebar: student_id + student_text + course + extract_btn
↓
IF extract_btn OR st.session_state.pipeline_done:
    bus.start_session() → profile.extract() → memory.update()
    → planner.plan() → recommender.recommend()
    → bus.get_timeline() → render 5 panels
```

### 2.3 V2 Component Signatures

```
render_system_overview(data: dict, st)           # 9-agent topology table
render_student_intelligence(data: dict, st)      # 6-dim profile + mastery heatmap
render_execution_timeline(data: dict, st)        # 12-event table w/ reasoning icons
render_explainability_panel(data: dict, st)      # Decision cards w/ evidence
render_evaluation_dashboard(data: dict, st)      # 4-agent 4-dim bar chart
render_improvement_timeline(data: dict, st)      # 5-stage vertical flow
```

### 2.4 Key File Stats

| File | Lines | Imports from src/ | Streamlit usage |
|:-----|:------|:-------------------|:----------------|
| `web/app.py` | 248 | core.*, agents.*, memory.* | Heavy |
| `web/dashboard/data_providers.py` | 624 | None at module level | None |
| `web/dashboard/components.py` | 496 | None at module level | Heavy (st parameter) |
| `web/dashboard/__init__.py` | 57 | .data_providers, .components | None |

### 2.5 Duplication Risk Analysis

| Resource | V1 (app.py) | V2 (dashboard) | Risk |
|:---------|:------------|:---------------|:-----|
| `AgentEventBus` | Singleton via `get_instance()` | Passed as arg → uses same singleton | ✅ Safe |
| `MemoryManager` | `@st.cache_resource` | Passed as arg → references same instance | ✅ Safe |
| `ProfileAgent` | `@st.cache_resource` | Not used directly (data passed in) | ✅ Safe |
| `PlannerAgent` | `@st.cache_resource` | Not used directly | ✅ Safe |
| `DecisionExplainer` | Not used | Instantiated on-demand | ✅ Safe |
| `AgentEvaluator` | Not used | Instantiated on-demand | ✅ Safe |
| `AgentTraceCollector` | Not used | Instantiated on-demand | ✅ Safe |

**Conclusion**: No hard duplication risk. V2's data providers accept existing V1 agents as arguments, not as new instances.

---

## 3. Architecture Proposal

### 3.1 Recommended Approach: Sidebar Mode Switch (Single Entrypoint)

```
web/app.py  (rewritten as lightweight router)
  │
  ├── MODE SELECTOR (sidebar radio)
  │     ├── "🎓 V1: 教学平台"  → render_v1_dashboard()
  │     └── "🔬 V2: 智能观测台" → render_v2_observatory()
  │
  ├── Shared state
  │     ├── AgentEventBus.get_instance()       [shared]
  │     ├── agents dict (cached)               [shared]
  │     └── st.session_state.mode              [V1/V2 toggle]
  │
  └── Architecture
        ┌──────────────────────────────────────────────┐
        │  app.py (router, ~50 lines)                  │
        ├──────────────────┬───────────────────────────┤
        │  V1 path         │  V2 path                  │
        │  (existing logic │  web/dashboard/           │
        │   extracted to   │  ├── data_providers.py    │
        │   web/v1/*.py)   │  └── components.py        │
        └──────────────────┴───────────────────────────┘
```

**Why sidebar switch over alternatives:**

| Approach | V1 Safety | V2 Isolation | Code Clarity | UX |
|:---------|:----------|:-------------|:-------------|:---|
| Sidebar Switch | ✅ High | ✅ Independent | ✅ Clean | ✅ Intuitive |
| Tabs | ⚠️ V1 flow breaks | ✅ Independent | 🟡 Moderate | 🟡 Tab overload |
| Separate Entrypoint | ✅ Max | ✅ Max | ✅ Max | ⚠️ Two URLs |
| Inline Mix | ❌ High regression | ❌ No isolation | ❌ Messy | ⚠️ Overwhelming |

### 3.2 State Isolation Strategy

```python
# app.py shared state
st.session_state.v1_mode = True   # V1 pipeline state
st.session_state.v2_mode = True   # V2 observatory state

# Mode switch clears V1-specific state
if mode_changed:
    st.session_state.pop("pipeline_done", None)
    st.rerun()
```

V1 state (`pipeline_done`, etc.) is scoped to V1 mode; V2 has no persistent session state (stateless rendering).

### 3.3 Data Flow (V2 Mode)

```
app.py sidebar
  │
  ├── mode == "V2"
  │     │
  │     ├── demo_mode checkbox
  │     │
  │     ├── IF demo:
  │     │     demo = get_demo_all()
  │     │     → render 6 panels from demo dict
  │     │
  │     └── IF live:
  │           │
  │           ├── get_system_overview(bus, collector, memory, evaluator)
  │           ├── get_student_intelligence(id, memory, profile)
  │           ├── get_execution_timeline(collector, bus)
  │           ├── get_explainability_data(explainer, profile, mastery)
  │           ├── get_evaluation_data(evaluator)
  │           └── get_improvement_timeline(loop, experience, reflector)
  │
  └── render_*() for all 6 panels
```

---

## 4. User Experience Design

### 4.1 Mode Selector

```
┌─ Sidebar ──────────────────────────┐
│                                     │
│  📊 Dashboard Mode                  │
│  ○ 🎓 V1: 教学平台                  │
│  ● 🔬 V2: 智能观测台  ← selected   │
│                                     │
│  ── V2 Options ──                  │
│  ☑ Demo Mode (展示用)               │
│                                     │
│  [Student ID: demo_student  ]       │
│  (live mode only)                   │
│                                     │
│  ── Info ──                        │
│  🟢 EventBus active                 │
│  📊 233 tests passed                │
└─────────────────────────────────────┘
```

### 4.2 Panel Layout (V2 Mode)

- **Full-width layout** (`layout="wide"`)
- 6 panels stacked vertically, each with `st.header` + `st.divider`
- Demo mode: all panels pre-populated → instant showcase
- Live mode: panels populate as data arrives from agents

### 4.3 Page Title Strategy

```python
st.set_page_config(page_title="A3 Intelligent Observatory", page_icon="🔬", layout="wide")
st.title("🔬 A3 Multi-Agent Intelligence Observatory")
st.caption("比赛展示版 Demo — 6-Panel Dashboard")
```

---

## 5. Data Provider Strategy

### 5.1 Demo Mode (Default)

```python
demo = get_demo_all()
# → 6 dicts with 9 agents, 8 concepts, 12 events, 8 decisions, 4 evals, 5 stages
```

**Trigger**: checkbox `☑ Demo Mode` checked OR no live data sources available.

**Advantage**: Zero configuration showcase — works on first launch without running pipeline.

### 5.2 Runtime Data Connection

```python
# In app.py, after agent initialization:
from web.dashboard import get_system_overview, get_student_intelligence, ...

# Shared bus (singleton)
bus = AgentEventBus.get_instance()

# Optional: TraceCollector (create once)
from core.agent_trace import AgentTraceCollector
collector = AgentTraceCollector()
collector.sync_from_bus()

# Optional: DecisionExplainer
from core.decision_explainer import DecisionExplainer
explainer = DecisionExplainer()

# Optional: AgentEvaluator
from evaluation.agent_evaluator import AgentEvaluator
evaluator = AgentEvaluator()

# Wire data
system_data = get_system_overview(
    event_bus=bus, trace_collector=collector,
    memory_manager=agents["memory"], evaluator=evaluator,
)
```

### 5.3 Future Replacement Path

| Current | Future | Trigger |
|:--------|:-------|:--------|
| `data_providers.py` → `get_*()` | Same interface, new backend | When underlying storage changes (JSON → Vector DB) |
| `components.py` → `render_*()` | Same interface, maybe add `plotly` | When richer viz needed |
| Demo data inline | External JSON/YAML seed files | When demo data >500 lines |

---

## 6. File Changes Plan

```
Phase 7.2 (Design — THIS PHASE)
  NEW   spec/dashboard-v2-integration-design.md        ← This document

Phase 7.3 (Implementation — NEXT PHASE)

  Phase A: Extract V1 to module
  ─────────────────────────────
  NEW   web/v1/__init__.py                              V1 package init
  NEW   web/v1/components.py                            V1 panel renderers (extracted from app.py)
  NEW   web/v1/pipeline.py                              V1 pipeline runner (extract→plan→recommend)

  Phase B: Create V2 entrypoint
  ─────────────────────────────
  NEW   web/app_v2.py                                    Standalone V2 entrypoint (demo-first)

  Phase C: Unified router
  ─────────────────────────────
  MODIFY web/app.py                                      Rewrite as mode router (~50 lines)
  MODIFY web/requirements.txt                            (unchanged: streamlit only)

  NOT MODIFIED
  src/agents/*      —  zero changes
  src/core/*         —  zero changes
  src/memory/*       —  zero changes
  src/evaluation/*   —  zero changes
  tests/*            —  zero changes
  web/dashboard/*    —  zero changes (already verified)
```

---

## 7. Risk Assessment

### 7.1 Regression Risks

| Risk | Severity | Mitigation |
|:-----|:---------|:-----------|
| V1 breaks when extracted to module | 🟡 MEDIUM | Phase A done first, tested independently before Phase C |
| `@st.cache_resource` invalidated by refactor | 🟢 LOW | Same function signature preserved |
| Agent singleton conflicts | 🟢 LOW | EventBus is singleton, agents passed by reference |
| `st.session_state` namespace collision | 🟡 MEDIUM | V1/V2 use different keys (`v1_*` vs `v2_*`) |
| Import path breakage | 🟢 LOW | `sys.path.insert` unchanged |

### 7.2 Streamlit State Risks

| Risk | Impact | Mitigation |
|:-----|:-------|:-----------|
| Mode switch clears V1 pipeline state | 🟢 LOW | Explicit `st.session_state.pop()` on mode change |
| Double-render on `st.rerun()` | 🟡 MEDIUM | Use `st.session_state.mode_initialized` guard |
| `st.cache_resource` across mode switch | 🟢 LOW | Agents cached once, reused across modes |

### 7.3 Import Risks

| Risk | Impact | Mitigation |
|:-----|:-------|:-----------|
| Circular imports (app → v1 → app) | 🔴 HIGH | V1 module imports agents directly, not from app |
| `web.dashboard` depends on `src/` | 🟢 LOW | Only at runtime when live mode is active |
| Module-level Streamlit calls in V1 extract | 🟡 MEDIUM | Ensure module functions avoid `st.*` at import time |

### 7.4 Performance Risks

| Risk | Impact | Mitigation |
|:-----|:-------|:-----------|
| 6 panels = 6 data queries in live mode | 🟡 MEDIUM | Demo mode is instant; live mode queries are all O(1) dict lookups |
| `AgentTraceCollector.load()` reads JSON | 🟢 LOW | Cached in session state |
| Large timeline rendering (100+ events) | 🟢 LOW | Demo capped at 12; live pagination can be added later |

---

## 8. Implementation Roadmap

### Phase A: Extract V1 to Module (Low Risk)

```
Goal: app.py → web/v1/ without breaking existing behavior.

Steps:
  A1. Create web/v1/__init__.py
  A2. Create web/v1/pipeline.py  ← extract pipeline logic
        - run_pipeline(student_id, student_text, course, agents, bus)
        - Returns: (profile, plan, resource_plan, events)
  A3. Create web/v1/components.py ← extract 5 panel renderers
        - render_profile_completeness(profile_data, result)
        - render_dynamic_profile(profile_data, result)
        - render_learning_path(plan, mastery)
        - render_resource_cards(resource_plan)
        - render_agent_trace(events)
  A4. Rewrite app.py to import from web/v1/
  A5. Run: streamlit run web/app.py → verify identical output

Verification:
  - V1 pipeline produces same output
  - All 233 tests still pass
  - No import errors
```

### Phase B: Create V2 Standalone Entrypoint (Low Risk)

```
Goal: web/app_v2.py — pure V2, demo-first, zero V1 dependency.

Steps:
  B1. Create web/app_v2.py
        - st.set_page_config(...)
        - Demo mode default: get_demo_all() → render 6 panels
        - Optional live mode: wire agents → get_*_data() → render 6 panels
  B2. Run: streamlit run web/app_v2.py → verify 6 panels render
  B3. No tests needed (pure UI)

Verification:
  - streamlit run web/app_v2.py shows all 6 panels
  - Demo mode works with zero setup
  - Live mode shows real data after V1 pipeline runs
```

### Phase C: Unified Router (Medium Risk)

```
Goal: single app.py with mode switch, delegating to v1/ and dashboard/.

Steps:
  C1. Create web/app.py v2 (router)
        - Detect mode from sidebar radio
        - V1 mode → import web.v1.pipeline → run + render
        - V2 mode → import web.dashboard → get_demo_all() → render
  C2. Verify: streamlit run web/app.py → both modes work
  C3. Full regression: python -m pytest tests/ -q

Verification:
  - Mode switch preserves V1 behavior
  - Mode switch to V2 shows 6 panels
  - 233 tests pass (no changes to src/)
```

---

## 9. Design Decision Log

| Decision | Rationale |
|:---------|:----------|
| **Sidebar switch** over separate entrypoints | Single URL for demo; cleaner than two separate Streamlit runs |
| **Phase A (extract V1)** before Phase C (router) | De-risk — V1 extraction tested independently before mixing modes |
| **Phase B (app_v2.py)** as standalone deliverable | V2 is immediately demo-ready without touching app.py |
| **Demo-first** data provider design | Showcase use case: zero setup, instant visual impact |
| **`st` parameter injection** in components | Testability; components don't import Streamlit at module level |
| **No new dependencies** | `streamlit>=1.28.0` already the only requirement |
