# Phase 13.0 — User Value Audit

**Date:** 2026-07-20  
**Auditor:** Hermes Agent (Read Only)  
**Scope:** A3-Agent v1.0.0 end-to-end user experience  
**Method:** Source code static analysis of all UI layers, API routes, Agent pipeline, and Provider configuration  
**Tests:** 2661 passed, 0 failures (unchanged — no code modified)  

---

## Executive Summary

**A3-Agent v1.0.0 is a functional AI learning platform with genuine student-facing value.** The core learning loop (Plan → Generate → Quiz → Score → Reflect) is fully implemented end-to-end. Key strengths include interactive quiz with AI error analysis, multi-agent pipeline visualization, and a polished dark-themed UI. However, **provider discoverability is significantly constrained** — only 3 of 8 supported LLM providers are exposed in the Settings UI.

---

## User Journey Audit

### Journey Map

```
Register → Login → Onboarding → Dashboard → Configure LLM → Start Learning
    → Profile Analysis → Learning Plan → Resource Generation
    → Quiz Generation → Answer Submission → AI Scoring → Error Analysis
    → Reflection → Memory Update → History Review → Workspace Browse
```

### Step-by-Step Findings

| # | Journey Step | UI Component | Backend | Verdict | Evidence |
|---|-------------|-------------|---------|---------|----------|
| 1 | **Register** | `render_auth_gate()` in `web/components/auth.py` | `POST /api/v2/auth/register` | ✅ | JWT-based registration with email+password; guest mode supported |
| 2 | **Login** | Auth gate token management | `POST /api/v2/auth/login` | ✅ | JWT token stored in session_state; session persistence |
| 3 | **Onboarding** | `_render_onboarding_gate()` in `web/app.py` line 173 | N/A (static) | ✅ | "Welcome to A3" intro + "Get Started" / "Configure LLM First" buttons |
| 4 | **Dashboard** | `_render_dashboard()` in `web/app.py` line 211 | `GET /api/v2/learning/stats`, `GET /api/v2/usage` | ✅ | Quick stats (sessions, avg score, total time, tokens), Quick Start text area |
| 5 | **Configure LLM** | `web/settings_tab.py` line 62 | `src/config/llm_config.py` + `POST /api/v2/settings/test` | ⚠️ | Only 3 providers discoverable in UI (see §Provider Gap) |
| 6 | **Define Goal** | Text area in Learning tab line 264 | N/A | ✅ | Free-text input: "Describe your background and what you want to learn..." |
| 7 | **Run Pipeline** | `_execute_pipeline_with_progress()` line 289 | `A3Workflow` via `LearningPipelineService` | ✅ | 7-stage animated progress bar with agent-by-agent status |
| 8 | **Profile Analysis** | Profile tab showing 6 dimensions | `ProfileAgent` → `GET /api/v2/profile` | ✅ | knowledge_base, cognitive_style, error_prone_bias, learning_pace, interaction_preference, frustration_threshold |
| 9 | **Learning Plan** | Plan expander with nodes + estimated hours | `PlannerAgent` via `src/agents/planner_agent.py` | ✅ | Ordered node list with concepts and time estimates |
| 10 | **Resource Generation** | Workspace tab with artifact browser | `ContentGeneratorAgent` → `ResourceAgent` → `WorkspaceManager` | ✅ | materials, ppt, images, videos — browsable + downloadable |
| 11 | **Quiz Generation** | `web/components/quiz_panel.py` line 81 | `EvaluationAgent.generate_quiz()` | ✅ | 3 dynamically generated questions per topic, difficulty auto-detected |
| 12 | **Answer Submission** | Radio buttons per question line 114 | `StudentAnswer` dataclass → `agent.score_quiz()` | ✅ | Inline radio selection + "Submit Answers" button |
| 13 | **AI Scoring** | Results display after submission | `QuizResult` (score_percent, weak_areas, strong_areas) | ✅ | Score percentage + weak/strong area breakdown |
| 14 | **Error Analysis** | `render_quiz_panel` line 138-153 | `EvaluationAgent.analyze_wrong_answer()` → `ErrorAnalysis` | ✅ | Per-wrong-question: error_type, explanation, correct_reasoning, related_concepts, recovery_plan, next_exercise |
| 15 | **Reflection** | Pipeline trace via expander | `ReflectionAgent` → `ReflectionResult` | ✅ | Quality evaluation score + passed/failed gate |
| 16 | **Memory Update** | Profile tab memory stats line 518-529 | `MemoryManager` → `StudentMemoryStore` | ✅ | interaction_count, mastery_map concepts, session_summaries |
| 17 | **History** | History tab line 393 | `GET /api/v2/learning/history` | ✅ | Per-run score + duration + course_id; 20 most recent |

---

## Audit Checklist Results

### 1. 用户是否能看到生成题目？

**✅ YES** — `web/components/quiz_panel.py` renders fully interactive quiz questions. Flow:

```
[Verify Learning] button → EvaluationAgent.generate_quiz()
  → QuizQuestion dataclass (id, question, options, correct_index, difficulty)
  → Rendered as radio buttons with A/B/C/D labels
  → Questions stored in session_state (never exposed to client)
```

### 2. 用户是否能在线答题？

**✅ YES** — Radio button selection per question → `StudentAnswer` collection → "Submit Answers" button → `agent.score_quiz()`. Full interactive loop.

### 3. 用户是否看到 AI 评分和解释？

**✅ YES** — Two-tier feedback:

| Tier | Data | Source |
|------|------|--------|
| **Score** | `score_percent`, `weak_areas[]`, `strong_areas[]` | `QuizResult` |
| **Error Analysis** | `error_type`, `explanation`, `correct_reasoning`, `related_concepts[]`, `recovery_plan`, `next_exercise` | `ErrorAnalysis` per wrong answer |

Error analysis includes **actionable recovery** — not just "you got it wrong" but "here's why + what concept to review + next exercise to try".

### 4. 用户是否看到学习资源？

**✅ YES** — Two access points:

| Access | Implementation |
|--------|---------------|
| **Workspace Tab** | `WorkspaceManager` → browse artifacts by category (materials/ppt/images/videos) + download button |
| **Material Panel** | `web/components/material_panel.py` — dedicated component for in-pipeline material display |

### 5. DeepSeek provider 是否存在且 UI 可配置？

**✅ YES** — `deepseek` is in `SUPPORTED_PROVIDERS` (frozenset), with models: `deepseek-chat`, `deepseek-v4-pro`, `deepseek-reasoner`. Settings tab renders it as "🌊 DeepSeek" with description "高性价比，中文能力强".

### 6. OpenAI/Claude/Qwen/Ollama 等模型是否可发现？

**⚠️ PARTIAL — Significant Gap**

| Provider | In ProviderFactory | In SUPPORTED_PROVIDERS | In Settings UI |
|----------|-------------------|------------------------|----------------|
| **OpenAI** | ✅ `OpenAIProvider` | ✅ `openai` | ✅ Discoverable |
| **DeepSeek** | ✅ `DeepSeekProvider` | ✅ `deepseek` | ✅ Discoverable |
| **Spark (讯飞)** | ✅ `SparkProvider` | ✅ `spark` | ✅ Discoverable |
| **Claude (Anthropic)** | ✅ `AnthropicProvider` | ❌ **MISSING** | ❌ Not discoverable |
| **Gemini (Google)** | ✅ `GoogleProvider` | ❌ **MISSING** | ❌ Not discoverable |
| **Qwen (通义千问)** | ✅ `QwenProvider` | ❌ **MISSING** | ❌ Not discoverable |
| **Kimi (Moonshot)** | ✅ `KimiProvider` | ❌ **MISSING** | ❌ Not discoverable |
| **Grok (xAI)** | ✅ `GrokProvider` | ❌ **MISSING** | ❌ Not discoverable |
| **Ollama** | ❌ No provider | ❌ | ❌ Not supported at all |

**Root Cause:** `src/config/llm_config.py` line 38 hardcodes `SUPPORTED_PROVIDERS = frozenset({"deepseek", "openai", "spark", "mock", "rule"})` — while `src/providers/factory.py` supports 8 providers. The Settings tab reads from `SUPPORTED_PROVIDERS`, creating a hard disconnect between backend capability and UI discoverability.

**Impact:** Users cannot configure Claude, Gemini, Qwen, Kimi, or Grok through the UI despite full backend support. Advanced users would need to manually edit config files.

### 7. Dashboard 是否面向学生而非开发者？

**✅ Mostly YES — with caveat**

| Dashboard | Target | Evidence |
|-----------|--------|----------|
| **Main app.py Dashboard** | Student ✅ | "Your AI-powered learning command center", Quick Start text area, stats (sessions, avg score, total time, tokens) |
| **web/dashboard.py** | Developer ⚠️ | Separate app at `streamlit run web/dashboard.py` — "Veritas Core — Runtime Dashboard", RuntimeBus snapshot, state machine observability. **Not linked from student dashboard.** |

The main student dashboard is appropriately student-facing. The developer dashboard (`web/dashboard.py`) exists as a separate entry point and is not accidentally exposed to students. Recommendation: add a "Developer Tools" link in Settings for power users.

### 8. Agent 能力是否都有 UI 映射？

**✅ Largely YES — with two gaps**

| Agent | UI Mapping | Status |
|-------|-----------|--------|
| `ProfileAgent` | Profile Tab (6 dimensions) | ✅ |
| `PlannerAgent` | Learning Plan expander (nodes + hours) | ✅ |
| `ContentGeneratorAgent` | Material panel + Workspace browser | ✅ |
| `ResourceAgent` | Workspace Tab (resource recommendations) | ✅ |
| `EvaluationAgent` | Quiz Panel (generate + score + error analysis) | ✅ |
| `ReflectionAgent` | Pipeline trace + quality evaluation expander | ✅ |
| `MetaReflectorAgent` | **No UI mapping** | ❌ |
| `TutorAgent` | **No explicit UI mapping** | ⚠️ |
| `VideoGeneratorAgent` | Workspace category (videos) | ✅ |
| `ImageGeneratorAgent` | Workspace category (images) | ✅ |
| `PPTGeneratorAgent` | Workspace category (ppt) | ✅ |

---

## UI Architecture Analysis

### Tab Structure

```
web/app.py (main entry, port 8501)
├── Onboarding Gate (_render_onboarding_gate)
├── Auth Gate (render_auth_gate)
└── 6-Tab Interface
    ├── 🏠 Dashboard     (_render_dashboard)      — Quick stats + start learning
    ├── 🎓 Learning      (_render_learning)       — Pipeline execution
    ├── 📜 History       (_render_history)        — Last 20 sessions
    ├── 📂 Workspace     (_render_workspace)      — Artifact browser
    ├── 👤 Profile       (_render_profile)        — 6-dim profile + memory stats
    └── ⚙️ Settings      (_render_settings)       — LLM provider config
```

### Sidebar

- User display name + ID
- Navigation buttons (6 tabs)
- Chat threads sidebar (optional, `render_chat_sidebar`)
- Logout

### Theme

Dark professional theme (`#0d1117` background, GitHub-style). Custom CSS for metrics, buttons, cards, progress bars, and agent status indicators.

---

## API Endpoint Coverage

### v2 Endpoints (Student-Facing)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v2/auth/register` | User registration |
| POST | `/api/v2/auth/login` | JWT login |
| POST | `/api/v2/auth/guest` | Guest session |
| GET | `/api/v2/auth/me` | Current user info |
| POST | `/api/v2/chat/message` | Chat message |
| POST | `/api/v2/chat/stream` | Streaming chat |
| GET | `/api/v2/chat/threads` | Chat thread list |
| POST | `/api/v2/profile/assess` | Profile analysis |
| GET | `/api/v2/profile` | Get profile |
| POST | `/api/v2/learning/plan` | Generate learning plan |
| POST | `/api/v2/learning/run` | Full pipeline run |
| GET | `/api/v2/learning/history` | Learning history |
| GET | `/api/v2/learning/stats` | Learning stats |
| GET | `/api/v2/resources/courses` | Course listing |
| POST | `/api/v2/resources/generate` | Generate resources |
| POST | `/api/v2/evaluation/quiz/generate` | Quiz generation |
| POST | `/api/v2/evaluation/quiz/score` | Quiz scoring |
| POST | `/api/v2/evaluation/open/assess` | Open-ended assessment |
| GET | `/api/v2/evaluation/results` | Evaluation results |
| GET | `/api/v2/settings/llm` | Get LLM config |
| POST | `/api/v2/settings/llm` | Save LLM config |
| POST | `/api/v2/settings/test` | Test connection |

---

## Provider Gap Analysis (Detailed)

### Root Cause Chain

```
src/providers/factory.py          — 8 providers supported (full backend)
        ↓ NO CONNECTION
src/config/llm_config.py          — 5 providers in frozen set (hardcoded gate)
        ↓
web/settings_tab.py               — reads SUPPORTED_PROVIDERS → only 3 real + 2 mock
web/onboarding_page.py            — reads hardcoded ONBOARDING_PROVIDERS → only 3 real + mock
```

### Missing from UI but Available in Backend

| Provider | Provider Key | Default Model | Has Provider Class |
|----------|-------------|---------------|-------------------|
| Claude (Anthropic) | `anthropic` / `claude` | `claude-sonnet` | `AnthropicProvider` |
| Gemini (Google) | `google` / `gemini` | `gemini-pro` | `GoogleProvider` |
| Qwen (通义千问) | `qwen` | `qwen3.5` | `QwenProvider` |
| Kimi (Moonshot) | `kimi` / `moonshot` | `kimi-k3` | `KimiProvider` |
| Grok (xAI) | `grok` / `xai` | `grok` | `GrokProvider` |

### Remediation

Adding these 5 providers to `SUPPORTED_PROVIDERS` in `src/config/llm_config.py` and updating `PROVIDER_LABELS`/`PROVIDER_MODELS`/`PROVIDER_DESCRIPTIONS` in both `settings_tab.py` and `onboarding_page.py` would unlock full backend provider parity in the UI. Estimated effort: ~30 lines of config changes across 2 files.

---

## Strengths

1. **Complete Learning Loop**: Plan → Generate → Quiz → Score → Error Analysis → Reflection → Memory — all stages have UI presence
2. **Error Analysis Depth**: Per-question AI analysis with recovery plans and next exercises is a genuine educational value-add
3. **Polished UI**: Dark theme, animated progress bars, agent status indicators, responsive layout — professional quality
4. **Student-First Dashboard**: Focus on learning goals and progress, not developer metrics
5. **Dual-Mode Operation**: Works with or without LLM (rule-based fallback + mock mode)
6. **Artifact Management**: Full workspace browser with download capability across multiple content types
7. **JWT Auth**: Registration, login, guest mode, session persistence — production-ready
8. **API Coverage**: 24+ v2 endpoints covering the full user journey

## Gaps

| # | Severity | Gap | Impact |
|---|----------|-----|--------|
| 1 | **MEDIUM** | 5 of 8 providers not discoverable in Settings UI | Users can't use Claude/Gemini/Qwen/Kimi/Grok without manual config editing |
| 2 | **MEDIUM** | Ollama not supported at all (no provider class) | Local model users have no integration path |
| 3 | **LOW** | `MetaReflectorAgent` has no UI mapping | Cross-session meta-learning insights invisible |
| 4 | **LOW** | `TutorAgent` has no explicit UI tab | Tutoring capability exists but not surfaced as a dedicated tab |
| 5 | **LOW** | Chat feature exists but is sidebar-only, not a main tab | Chat discovery requires sidebar exploration |
| 6 | **NOTE** | `web/dashboard.py` (developer dashboard) is a separate app | Not linked from student UI — no risk of confusion |

---

## Verdict

| Criterion | Result |
|-----------|--------|
| Does the product demonstrate real AI learning capability? | ✅ **YES** — Multi-agent pipeline with LLM-driven content generation, quiz scoring, and error analysis |
| Is it more than a Demo UI? | ✅ **YES** — Full backend pipeline, JWT auth, workspace persistence, 2661 tests |
| Can a student complete a learning cycle? | ✅ **YES** — Register → Set goal → Get plan → Take quiz → See results → Review history |
| Can the student use their own LLM key? | ⚠️ **PARTIAL** — Only 3 providers exposed; 5 more available in code but hidden |

**Overall: Functionally complete product with a configuration discoverability gap.** The platform genuinely demonstrates AI learning capability — it's not just a mock UI. A student can register, configure DeepSeek/OpenAI/Spark, define a learning goal, receive a personalized plan, take an AI-generated quiz, get scored with per-question error analysis, and review their learning history. The primary value-add (AI-powered personalized learning with actionable feedback) is fully delivered.

---

## Recommendation

**Not Release-Blocking.** The provider discoverability gap (5 hidden providers) is a configuration UX issue, not a functional defect. The product is usable and valuable with the 3 exposed providers.

**Suggested next step:** Phase 13.1 — Provider UX parity update (add missing 5 providers to `SUPPORTED_PROVIDERS` and Settings UI, ~30 lines of config).
