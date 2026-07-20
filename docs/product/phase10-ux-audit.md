# Phase 10.4-D — UX Audit

> **Date**: 2026-07-20
> **Audit Target**: `web/app.py` + all web/ components
> **Baseline**: 2586 tests, 0 failures

---

## 1. Current Architecture

```
web/app.py (327 lines)
  ├── Auth Gate       web/components/auth.py       render_auth_gate()
  ├── Sidebar Nav     5-tab buttons                Dashboard, Learning, Chat, Profile, Settings
  ├── Dashboard Tab   _render_dashboard_tab()       3 quick stats + goal input
  ├── Learning Tab    _render_learning_tab()        goal → execute pipeline → show plan nodes
  ├── Chat Tab        _render_chat_tab()           delegates to render_chat_main()
  ├── Profile Tab     _render_profile_tab()        6 profile dimensions
  ├── Settings Tab    _render_settings_tab()       delegates to web/settings_tab.py
  └── Logout          render_logout()
```

```
web/utils/api.py (266 lines)
  └── A3APIClient     REST client for all /api/v2/* endpoints
```

```
Supporting files (unused by app.py):
  web/onboarding_page.py    354 lines — LLM provider setup (used by app_v3.py only)
  web/app_v3.py             610 lines — Legacy dashboard with onboarding
  web/app_v2.py             179 lines — V2 standalone Streamlit
  web/demo_dashboard.py     173 lines — Demo with mock data
  web/chat_demo.py           348 lines — Chat demo
  web/v1/                    V1 interactive pipeline (Streamlit)
  web/dashboard/              Dashboard components (684 + 778 lines)
  web/components/            Auth, Chat, Quiz, Material panels
```

---

## 2. UX Flow Analysis

### Current User Journey

```
Launch → Auth Gate (Login/Register) → Dashboard
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    ▼                      ▼                      ▼
              Learning Tab            Chat Tab              Settings Tab
              (goal→spinner→plan)     (conversation)        (LLM config)
```

### Missing UX Nodes

| Requirement | Status | Gap |
|:------------|:------:|:----|
| Onboarding (first launch) | ⚠️ | Exists in `onboarding_page.py` but NOT wired into `app.py` |
| Dashboard (stats + quick start) | ✅ | Minimal — 3 metrics |
| Pipeline execution visualization | ❌ | `st.spinner()` only — no progress, no agent trace, no live feedback |
| Run history    | ❌ | No history view — results lost on page refresh |
| Artifact browser | ❌ | Artifacts saved to disk but no UI to browse/download |
| Error handling | ⚠️ | Basic try/except with `st.warning/error` — no recovery UX |
| Learning workspace | ❌ | No unified view of user's learning data |
| Profile page   | ⚠️ | 6 dimensions shown but no profile history or evolution |

---

## 3. Component Inventory

### web/app.py — Current Tab Renderers

| Tab | Function | Lines | Renders |
|:----|:---------|:-----:|:--------|
| Dashboard | `_render_dashboard_tab()` | 44 | 3 metric cards + goal text area + "Start Learning" button |
| Learning | `_render_learning_tab()` + `_execute_pipeline()` | 90 | Goal input + pipeline execution with spinner + plan nodes expander |
| Chat | `_render_chat_tab()` | 3 | Delegates to `render_chat_main()` |
| Profile | `_render_profile_tab()` | 35 | 6 profile dimension metrics in 3 columns |
| Settings | `_render_settings_tab()` | 11 | Delegates to `web/settings_tab.py` |

### Unused but Available Assets

| File | Lines | Content | Value |
|:-----|:-----:|:--------|:------|
| `web/onboarding_page.py` | 354 | LLM provider onboarding wizard | Wire into app.py first-launch |
| `web/dashboard/data_providers.py` | 778 | System overview, student intelligence, execution timeline, evaluation dashboard | Rich data for enhanced dashboard |
| `web/dashboard/components.py` | 684 | `render_system_overview()`, `render_student_intelligence()`, `render_execution_timeline()`, etc. | Ready-made visualization components |
| `web/v1/pipeline.py` | 139 | Agent init + pipeline execution | Real-time pipeline visualization with EventBus |
| `web/v1/components.py` | 391 | `render_profile_completeness()`, `render_dynamic_profile()`, `render_learning_path()`, `render_resource_cards()`, `render_agent_trace()` | Rich visual panels for pipeline results |

---

## 4. Gap Analysis

### 4.1 — Pipeline Execution Visualization

**Current**: `st.spinner("🔍 Analyzing your profile...")` — a static spinner with no indication of which agent is running.

**What's needed**:
- Live agent progress (ProfileAgent → PlannerAgent → ContentGenerator → Resource → Review → Reflection)
- Progress bar or step indicator
- EventBus trace display (already available in API response!)
- Duration per agent step

**Available assets**: `web/v1/components.py` has `render_pipeline_progress(events, st)` and `render_agent_trace(results["events"], st)` — these already work but aren't wired into app.py.

### 4.2 — Run History

**Current**: Results stored in `st.session_state` — lost on page refresh. No history view.

**What's needed**:
- List of past runs (from `GET /api/v2/learning/history`)
- Click to view previous run details
- Run metadata: date, goal, score, duration

**Available assets**: `GET /api/v2/learning/history` returns learning records. `GET /api/v2/learning/stats` returns aggregated stats.

### 4.3 — Artifact Browser

**Current**: Pipeline saves artifacts to `~/.a3-agent/workspace/{uid}/artifacts/` but no UI to view or download.

**What's needed**:
- List generated artifacts (plan JSON, plan MD, resources JSON, evaluation JSON)
- Preview content inline (JSON/MD)
- Download button for each artifact
- Workspace overview showing file counts by category

**Available assets**: `WorkspaceManager.list_artifacts()`, `WorkspaceManager.load_artifact()` — already functional. `WorkspaceManager.get_workspace_info()` provides metadata.

### 4.4 — Error Handling

**Current**: Basic try/except with `st.error()` or `st.warning()`. No recovery suggestions.

**What's needed**:
- API error → specific user-friendly message with recovery action
- Token expired → auto-redirect to login
- Budget exceeded → show usage + upgrade hint
- Network error → retry button
- Consistent error display component

**Available assets**: `A3APIError` class with `status` + `detail`. Status codes: 401 (unauthorized), 429 (budget), 422 (validation).

### 4.5 — Onboarding

**Current**: `onboarding_page.py` exists but only imported by `app_v3.py` (legacy). `app.py` doesn't use it.

**What's needed**: Wire into `app.py` as a first-launch gate before the auth gate.

---

## 5. Recommended Changes

### Phase 10.4-D Implementation Plan

| # | Change | Target File | Lines (est) | Test Impact |
|:--|:-------|:------------|:-----------:|:-----------:|
| 1 | Wire onboarding into app.py | `web/app.py` | +10 | None (pre-auth gate) |
| 2 | Pipeline execution visualization | `web/app.py` | +40 | New tests |
| 3 | Run history component | `web/app.py` | +50 | New tests |
| 4 | Artifact browser component | `web/app.py` (new) | +80 | New tests |
| 5 | Enhanced error handling | `web/app.py` | +30 | New tests |
| 6 | Dashboard enhancements | `web/app.py` | +20 | New tests |
| **Total** | | | **~230** | **30+ new tests** |

### Implementation Strategy

Reuse existing assets wherever possible:
- Pipeline visualization → import from `web/v1/components.py` (`render_pipeline_progress`, `render_agent_trace`)
- Dashboard data → import from `web/dashboard/data_providers.py` (demo data providers)
- Onboarding → import from `web/onboarding_page.py` (already functional)
- All communication through `A3APIClient` (no direct src/ imports)

### Test Strategy (30+ tests)

- Pipeline visualization state transitions (8 tests)
- Run history listing and detail view (6 tests)  
- Artifact browser listing and download (6 tests)
- Error handling for each HTTP code (6 tests)
- Dashboard metric rendering (4 tests)
- Onboarding flow (2 tests)

---

## 6. Risk Assessment

| Risk | Level | Mitigation |
|:-----|:-----:|:-----------|
| Breaking existing tab navigation | 🟢 LOW | Additive changes only |
| Streamlit rerender loops | 🟡 MEDIUM | Use `st.session_state` + `st.rerun()` pattern from existing code |
| Test isolation (Streamlit state) | 🟡 MEDIUM | Use dedicated TestClient + A3APIClient._test_client pattern |
| API dependency (needs running server) | 🟢 LOW | Tests use TestClient (in-process FastAPI) |

---

## 7. UX Target State

```
Launch → Onboarding (LLM setup, first time only)
           ↓
    Auth Gate (Login/Register)
           ↓
    Dashboard
    ┌────────┼────────┬──────────┬──────────┐
    ▼        ▼        ▼          ▼          ▼
  Learning  History  Workspace   Profile   Settings
  (pipeline (past    (artifacts  (profile  (LLM
   + live   runs)    browser)    view)     config)
   progress)
```

Each tab now has:
- **Learning**: Goal input → Live pipeline visualization (agent-by-agent progress) → Results (plan, resources, trace)
- **History**: List of past runs with scores, click to expand details
- **Workspace**: Artifact browser with file listing, content preview, download buttons
- **Profile**: Profile dimensions + history evolution
- **Settings**: LLM config (unchanged)

---

*End of Phase 10.4-D — UX Audit*
