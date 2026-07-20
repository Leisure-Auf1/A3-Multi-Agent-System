# Phase 16.0 — Product Experience Validation Audit

**Date:** 2026-07-20  
**Auditor:** Hermes Agent  
**Method:** Live API testing + full UI source audit  
**Status:** Read-Only — No Code Modified  

---

## Product Reality Score

| Dimension | Score | Notes |
|-----------|-------|-------|
| Core Learning Loop | **7/10** | Pipeline works, content generated, but quiz disconnected |
| AI Visibility | **4/10** | Provider shown but always "rule-only" with dummy key; no real-time AI indicator |
| Output Quality | **5/10** | Content present but template-based with dummy key; real key untested |
| User Journey | **6/10** | Complete path exists but quiz+resource disconnected from pipeline |
| Provider Ecosystem | **8/10** | All 10 providers in UI; factory supports all 8 production |
| Overall | **6.0/10** | Functional product with demo artifacts in key places |

---

## 1. First User Journey Audit

### Step-by-Step Trace

| Step | UI Entry | API Called | Real Data? | Gap |
|------|----------|-----------|------------|-----|
| **Register** | ✅ `render_auth_gate()` → Register tab | `POST /api/v2/auth/register` | ✅ Token returned | — |
| **Login** | ✅ Login tab | `POST /api/v2/auth/login` | ✅ JWT in session | — |
| **Onboarding** | ✅ Welcome screen | N/A (static) | ✅ Intro text | "Configure LLM First" button exists but buried in onboarding |
| **Dashboard** | ✅ Quick stats + "Start Learning" | `GET /stats`, `GET /usage` | ✅ Sessions/Score/Time/Tokens | — |
| **Configure LLM** | ✅ Settings tab → Provider selector | `POST /settings/llm`, `POST /settings/test` | ✅ 10 providers listed | — |
| **Enter Goal** | ✅ Text area "Learning Goal" | N/A | ✅ User input | — |
| **Run Pipeline** | ✅ "🚀 Run Pipeline" button | `POST /api/v2/learning/run` | ⚠️ Partial | Progress bar is simulated, not real agent progress |
| **View Results** | ✅ Pipeline results section | (data from API response) | ⚠️ Mixed | Content/resource cards present but template quality |
| **AI Engine Details** | ✅ "⚡ AI Engine Details" expander | run_info field | ⚠️ Always "rule-only" with dummy key | No real provider name detection without real key |
| **Generated Lesson** | ✅ "📝 AI-Generated Lesson" expander | content field | ⚠️ Template chapters | 4 chapters but template content |
| **Learning Plan** | ✅ "🗺️ Learning Plan" expander | plan.nodes | ⚠️ Template nodes | Shows topics, no concepts filled in |
| **Quality Evaluation** | ✅ "📊 Quality Evaluation" expander | evaluation.score | ⚠️ Constant 95 | No detailed evaluation text |
| **Answer Quiz** | ❌ **NOT RENDERED** | — | ❌ | Quiz panel exists but never wired into pipeline results |
| **Error Analysis** | ❌ Not accessible | — | ❌ | `analyze_wrong_answer()` exists but quiz not integrated |
| **Review Feedback** | ⚠️ Score only | evaluation | ⚠️ | Shows "95 / Passed" — no learning feedback text |
| **Browse Resources** | ✅ Resource cards + Workspace tab | `GET /resources/*` + direct import | ⚠️ Title only | "mindmap: Python" — no description or content |
| **Check History** | ✅ History tab | `GET /learning/history` | ⚠️ Minimal | Score + duration + date — no content preview |
| **Check Profile** | ✅ Profile tab | `GET /profile` | ✅ 6 dimensions | Source="stored" or "rule" |
| **Logout** | ✅ Sidebar button | `POST /auth/logout` | ✅ | — |

### Flow Breaks

| Breakpoint | Where | What's Missing |
|-----------|-------|---------------|
| **Pipeline → Quiz** | `_render_pipeline_results` | Quiz panel `render_quiz_panel()` never called |
| **Pipeline → Error Analysis** | quiz_panel not rendered | Per-question AI error analysis inaccessible |
| **Pipeline → Chat** | No tab in main nav | Chat is sidebar-only, discoverable only by chance |
| **Onboarding → LLM Config** | Onboarding gate | "Configure LLM First" is optional, many users skip it |

---

## 2. AI Visibility Audit

### Provider Visibility

| Provider | In Settings UI | In API /settings/llm | In ProviderFactory | User Can Discover |
|----------|---------------|---------------------|-------------------|-------------------|
| DeepSeek | ✅ | ✅ | ✅ | ✅ |
| OpenAI | ✅ | ✅ | ✅ | ✅ |
| Claude | ✅ | ✅ | ✅ | ✅ |
| Gemini | ✅ | ✅ | ✅ | ✅ |
| Qwen | ✅ | ✅ | ✅ | ✅ |
| Kimi | ✅ | ✅ | ✅ | ✅ |
| Grok | ✅ | ✅ | ✅ | ✅ |
| Spark | ✅ | ✅ | ✅ | ✅ |
| Mock | ✅ (Demo section) | ✅ | ✅ (via Veritas) | ✅ |
| Rule | ✅ (Demo section) | ✅ | ✅ (pure code) | ✅ |

### Runtime Observability (Pipeline Results)

| Metric | In API Response | In UI | Shows Real Data? | Issue |
|--------|----------------|-------|-----------------|-------|
| **AI Engine** | ✅ run_info.engine | ✅ "AI Engine Details" | ⚠️ "rule-only" with dummy key | Would show "deepseek" with real key |
| **Model Name** | ✅ run_info.model | ✅ | ⚠️ "deepseek-chat" | Correct when provider created |
| **Generation Time** | ✅ run_info.generation_time_ms | ✅ | ✅ 668ms | Real time recorded |
| **Token Usage** | ⚠️ run_info.tokens_used | ✅ "Tokens used: 0" | ❌ 0 | No token tracking in agent trace |
| **Fallback Status** | ✅ run_info.is_fallback | ✅ Warning banner | ✅ True | Shows when no real LLM |
| **Provider Status Icons** | ✅ ProviderStatusTracker | ✅ 🟢/🔴/⚪ | ⚠️ All ⚪ | Never connected because dummy key fails |

### "AI Is Working" Indicator

| Signal | Present? | Issue |
|--------|---------|-------|
| Pipeline progress animation | ✅ 7-stage bar | Shows "rule-based" for all stages |
| AI Engine badge | ✅ | Shows "rule-only" instead of real provider |
| Generation time > 0 | ✅ 668ms | Time includes failed API attempts |
| Token count > 0 | ❌ 0 | No agent records tokens in trace |
| Content source badge | ✅ "🤖 Generated by AI" or "⚙️ Template" | Shows "Template-generated" |
| Profile source | ⚠️ "stored" or "rule" | Never "llm" in current flow |

---

## 3. Learning Output Quality Audit

### Profile Output

```json
{
  "source": "stored",
  "knowledge_base": "junior_dev",
  "cognitive_style": "visual_dominant",
  "learning_pace": "normal",
  "confidence": N/A
}
```

| Issue | Severity |
|-------|----------|
| Source always "stored" or "rule" — never "llm" | 🟡 |
| Confidence never shown | 🟡 |
| Same values for all users (junior_dev/visual_dominant) | 🟡 |

### Learning Plan Output

```
4 nodes:
  1. "闭包与作用域" (~1h)
  2. "装饰器入门" (~1h)
  3. "带参装饰器与类装饰器" (~1h)
  4. "生成器与迭代器" (~1h)
```

| Issue | Severity |
|-------|----------|
| Nodes from static topic list, not AI-generated | 🟡 |
| "闭包与作用域" for "Python数据分析" — completely wrong topic | 🔴 |
| No concepts filled in (empty arrays) | 🟡 |
| No personalized path based on profile | 🟡 |

### Content Output

```
4 chapters, generation_source: "rule"
```

| Issue | Severity |
|-------|----------|
| Template-generated content | 🟡 |
| Chapters exist but content is generic | 🟡 |
| Source badge correctly shows "Template-generated" | ✅ |

### Quiz Output

```
Q: "What is the primary purpose of Python data analysis?"
Q: "Which of these is a key concept in Python data analysis?"
```

| Issue | Severity |
|-------|----------|
| Template questions ("What is the purpose of [topic]?") | 🟡 |
| Quiz NOT rendered in pipeline results | 🔴 |
| Answer submission and error analysis inaccessible | 🔴 |

### Resource Output

```
3 artifacts: document "Python", mindmap "Python", exercise "Python"
```

| Issue | Severity |
|-------|----------|
| All titles identical ("Python") | 🟡 |
| No descriptions in pipeline resource cards | 🟡 |
| Content from template (TextProvider) | 🟢 |

---

## 4. UI Capability Mapping

| Capability | Backend | API Endpoint | UI Component | User Visible |
|------------|---------|-------------|-------------|--------------|
| **Profile Analysis** | ProfileAgent | `POST /profile/assess` | Profile tab (6 metrics) | ✅ |
| **Learning Plan** | PlannerAgent | `POST /learning/plan` | Pipeline results expander | ✅ |
| **Content Generation** | ContentGeneratorAgent | `POST /learning/run` → content | "AI-Generated Lesson" expander | ✅ |
| **Resource Recommendation** | ResourceAgent | `POST /learning/run` → resources | Resource cards expander | ✅ |
| **Quiz Generation** | EvaluationAgent | `POST /evaluation/quiz/generate` | ❌ NOT RENDERED | ❌ |
| **Quiz Scoring** | EvaluationAgent | `POST /evaluation/quiz/score` | ❌ NOT RENDERED | ❌ |
| **Error Analysis** | EvaluationAgent | (internal) analyze_wrong_answer() | ❌ NOT RENDERED | ❌ |
| **Reflection** | ReflectionAgent | `POST /learning/run` → reflection | ❌ Not displayed | ❌ |
| **Memory/Persistence** | MemoryManager | (internal) | Profile tab memory stats | ✅ |
| **Artifact Browsing** | WorkspaceManager | (direct import) | Workspace tab | ✅ |
| **Learning History** | learning_records | `GET /learning/history` | History tab | ✅ |
| **LLM Configuration** | llm_config | `POST /settings/llm` | Settings tab | ✅ |
| **Provider Health** | ProviderStatusTracker | (internal) | Settings status icons | ✅ |
| **Pipeline Observability** | _build_run_info | `POST /learning/run` → run_info | AI Engine Details expander | ✅ |
| **MetaReflection** | MetaReflectorAgent | (internal) | ❌ No UI | ❌ |
| **Tutoring** | TutorAgent | `POST /chat/message` | Chat sidebar (hidden) | ⚠️ |
| **Multimodal** | Image/PPT/Video Generators | `POST /resources/generate` | Workspace tab | ⚠️ |

---

## 5. Demo vs Product Gap Analysis

### P0 — Blocks Real Product Use

| # | Gap | Evidence | Fix |
|---|-----|----------|-----|
| P0-1 | **Quiz not rendered in pipeline** | `render_quiz_panel()` exists but `_render_pipeline_results` never calls it | Wire quiz into pipeline results |
| P0-2 | **No quiz → answer → feedback flow** | User runs pipeline, gets plan, but never sees quiz | Integrate quiz → score → error analysis |
| P0-3 | **Learning plan wrong for user goal** | "Python数据分析" → "闭包与作用域" (closures, not data analysis) | Plan is from static KB, not AI-generated with dummy key |

### P1 — Severely Impacts Experience

| # | Gap | Evidence | Fix |
|---|-----|----------|-----|
| P1-1 | **Reflection not displayed** | ReflectionAgent runs but output never shown in UI | Add reflection expander |
| P1-2 | **Token tracking missing** | run_info.tokens_used = 0 even when LLM calls happen | Record tokens in agent trace events |
| P1-3 | **Resource titles all identical** | "Python", "Python", "Python" for different resource types | Template provides need meaningful titles |
| P1-4 | **Confidence never shown** | Profile confidence always N/A or 0 | Add confidence display |
| P1-5 | **Progress bar is simulated** | Shows 7 stages regardless of actual agent execution | Read actual trace events for real-time progress |
| P1-6 | **History shows no content** | Only score + duration + date | Include goal text and content preview |

### P2 — Optimization

| # | Gap | Evidence | Fix |
|---|-----|----------|-----|
| P2-1 | **Chat not in main navigation** | Only in sidebar, no tab | Add "💬 Chat" tab |
| P2-2 | **MetaReflector no UI** | Cross-session insights invisible | Add to Profile tab |
| P2-3 | **Workspace bypasses API** | Uses direct `WorkspaceManager` import | Route through API |
| P2-4 | **Onboarding doesn't guide LLM config** | "Configure LLM First" is optional | Make it the primary path |

---

## Current State Summary

### What Works (Real Product)
- ✅ Full auth flow (register/login/guest)
- ✅ 10 providers in settings with connection test
- ✅ Pipeline executes all 7 agents
- ✅ Content/resource/evaluation generated
- ✅ AI Engine Details with provider/model/latency
- ✅ Workspace with artifact browser + download
- ✅ Learning history with stats
- ✅ Profile with 6 dimensions + memory stats

### What's Demo-Like
- ❌ Quiz panel exists but never reaches user
- ❌ Learning plan uses static topics (wrong for user goal)
- ❌ All content template-generated with dummy key
- ❌ Progress bar animation is fake (not real agent status)
- ❌ "AI Engine" always says "rule-only"
- ❌ Resources all have same title
- ❌ History shows no learning content

### What Users Never See
- ReflectionAgent output
- MetaReflectorAgent insights
- TutorAgent as a main feature
- Quiz error analysis
- Real-time agent progress (fake progress bar)
- AI-generated profile (always rule-based)

---

## Recommendation for Phase 16.1

**Priority: Wire quiz into pipeline results → answer → score → error analysis flow.**

This is the single biggest gap. The quiz code exists, works, and has AI error analysis. It's just not connected to the pipeline results page.

**Estimated effort:** ~30 lines in `web/app.py`  
**Impact:** Users see complete learning loop: learn → quiz → score → learn more

Report: `docs/product/phase16-product-experience-audit.md`
