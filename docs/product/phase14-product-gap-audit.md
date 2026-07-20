# Phase 14.0 — Product Reality Audit

**Date:** 2026-07-20  
**Auditor:** Hermes Agent (Read Only)  
**Method:** Source code trace + live API simulation  
**Key Question:** "用户下载后，为什么感觉像Demo？"

---

## Executive Verdict

**A3-Agent v1.0.0 is a demo.** It looks like an AI learning product, but real LLM calls are **inaccessible to all normal users**. The multi-agent pipeline, quiz generation, resource creation, and profile analysis all run in **rule-only template mode** for everyone except PRO/TEACHER/ADMIN role users — roles that are never assigned during normal registration.

---

## Root Cause: The LLM Gate

### The Problem

```python
# src/api/v2/pipeline.py:96-101
llm_provider = None
if role in (Role.PRO, Role.TEACHER, Role.ADMIN):   # ← THIS IS THE GATE
    try:
        from src.core.provider_factory import create_provider
        llm_provider = create_provider()
    except Exception:
        pass  # Fall back to rule-only
```

**All users default to `role="free"`** (line 36 in `src/user/models.py`, line 79 in `src/user/manager.py`). The pipeline only activates LLM for PRO, TEACHER, or ADMIN roles — which are **never assigned** through normal registration.

### Effect Chain

```
User Registers → role="free"
User Configures DeepSeek → API key saved to llm.json
User Clicks "Run Pipeline" → POST /api/v2/learning/run
  → role check: "free" NOT in (PRO, TEACHER, ADMIN)
  → llm_provider = None
  → All 7 agents run in rule-only mode
  → Pipeline duration: 2ms (no API calls)
  → Content generated from templates
  → User sees: "闭包与作用域" for "Python基础" (garbage)
```

---

## Evidence: Live User Simulation

### Setup

```
Register: audit_test@a3.local → role="free"
Configured: DeepSeek API key (saved to llm.json)
Goal: "我要学习Python基础"
```

### Pipeline Run Result

| Metric | Value | Indicator |
|--------|-------|-----------|
| `duration_ms` | **2ms** | ❌ No API calls made |
| `agents using LLM` | **0 of 7** | ❌ All rule-only |
| `plan.nodes` | 4 | ⚠️ Template-based |
| `plan.nodes[0].title` | "闭包与作用域" | ❌ Advanced topic for beginner |
| `evaluation.score` | 95 | ⚠️ Rule-defined constant |

### Quiz Generation

```json
{
  "id": "q1",
  "question": "What is the primary purpose of Python基础?",
  "options": [
    "To solve specific problems efficiently",
    "To replace human decision-making entirely",
    "To store large amounts of unstructured data",
    "To generate random outputs for testing"
  ]
}
```

**Verdict: Template-based.** The quiz engine takes the topic string "Python基础" and plugs it into a generic template — the question doesn't make sense in Chinese context.

### Resource Generation

```markdown
# Python基础
**Level:** beginner
**Concepts covered:** 2
## Overview
This document provides a comprehensive introduction to **Python基础**, 
covering 2 key concepts designed for beginner-level learners.
```

**Verdict: Template-based.** Empty shell with topic name inserted into placeholder text.

### Profile Analysis

```json
{
  "profile": {
    "knowledge_base": "junior_dev",
    "cognitive_style": "visual_dominant",
    "error_prone_bias": "magic_syntax_blind"
  },
  "source": "rule",
  "confidence": 0.0
}
```

**Verdict: Keyword-based, zero AI.** `"source": "rule"`, `"confidence": 0.0` — the ProfileAgent uses keyword matching, not LLM analysis.

---

## Frontend Reality Check

### What Users See vs What Happens

| UI Element | User Expectation | Reality |
|------------|-----------------|---------|
| 🚀 Run Pipeline button | AI agents analyze my goal, generate personalized plan | 7 template functions execute in <2ms, no API calls |
| Progress bar (7 stages) | "ProfileAgent... PlanningAgent..." animating | Progress is simulated from hardcoded stage list, not real agent output |
| "✅ Pipeline complete" | AI has done something intelligent | Rule engine returned templated response |
| Learning Plan expander | Personalized learning path based on my goal | Random Python topics from a static list |
| Quality Score: 95 | AI evaluated the plan quality | Constant value, no evaluation happened |
| Quiz Panel | AI generates questions about MY learning | Template: "What is the purpose of [topic]?" |
| Profile (6 dimensions) | AI analyzed my learning style | Rule-based keyword matching, confidence 0.0 |

### Integration Gaps

| Component | Status | Detail |
|-----------|--------|--------|
| Quiz in Pipeline | ❌ **Not integrated** | Quiz panel exists but is NOT rendered after pipeline completion — user never sees it unless they navigate to a separate quiz flow |
| Resource in Pipeline | ❌ **Not integrated** | Resources generated but only visible in Workspace tab (separate navigation) |
| Artifact download | ✅ Exists | Workspace tab shows generated files with download buttons |
| History completeness | ⚠️ **Minimal** | Shows agent name + score + duration — no learning content preview, no quiz history, no resource links |

---

## Backend Flow Trace (Actual Call Chain)

```
User Input "我要学习Python基础"
  │
  ▼
POST /api/v2/learning/run         (pipeline.py:65)
  │
  ├── TokenBudgetManager.check_available(500)  ✅
  ├── UserManager.get_user_by_email()           → role="free"
  ├── role check: "free" ∈ (PRO,TEACHER,ADMIN)? → NO ❌
  ├── llm_provider = None                       ← GATE BLOCKS LLM
  │
  ▼
LearningPipelineService.run(user_id, goal, llm_provider=None)
  │
  ▼
A3Workflow(student_id, llm_provider=None)
  │
  ├── ProfileAgent.run()         → rule: keyword extraction
  ├── PlannerAgent.run()         → rule: picks from static topic list
  ├── ContentGeneratorAgent.run() → rule: template fill
  ├── ResourceAgent.run()        → rule: template document
  ├── ReviewGate                 → rule: constant score 95
  ├── ReflectionAgent.run()      → rule: summary template
  └── MemoryManager.save()       → writes to StudentMemoryStore
  │
  ▼
Response: {profile, plan, resources, evaluation, reflection, memory_saved}
  │
  ▼
web/app.py: _execute_pipeline_with_progress()
  ├── Simulates 7-stage progress bar (all stages say "done (rule-based)")
  ├── _render_pipeline_results()
  │   ├── AI Engine Details  → empty (no run_info from rule mode)
  │   ├── Learning Plan      → shows template nodes
  │   ├── Quality Evaluation → shows 95 (constant)
  │   └── Quiz Panel         → NOT RENDERED (separate component)
```

---

## Answer: "Why Does It Feel Like a Demo?"

### The 5 Demo Indicators

| # | Indicator | Evidence | Severity |
|---|-----------|----------|----------|
| 1 | **LLM never called** | Role gate blocks all normal users; pipeline runs in 2ms | 🔴 **CRITICAL** |
| 2 | **Template output** | Quiz: "What is the purpose of Python基础?" — template with Chinese+English mix | 🔴 **CRITICAL** |
| 3 | **Garbage plan** | "闭包与作用域" for "Python基础" — clearly not LLM-generated | 🔴 **CRITICAL** |
| 4 | **Fake progress** | 7-stage animated progress bar, but all stages complete instantly with "rule-based" | 🟡 **MEDIUM** |
| 5 | **Disconnected components** | Quiz not in pipeline results, resources in separate tab, history minimal | 🟡 **MEDIUM** |

### Dashboard Lies

| Dashboard Metric | What It Shows | What It Actually Means |
|-----------------|---------------|----------------------|
| "📚 1 Session" | User ran pipeline once | Pipeline ran rule-only, no AI |
| "⭐ Avg Score 95%" | Quality evaluation | Constant rule-defined value, not real evaluation |
| "⏱️ Total Time 0min" | 2ms pipeline duration | No real work done |
| "🔢 Tokens 0" | No tokens used | No LLM calls made |

---

## Gap Categories

### A. 已实现但不可见 (Implemented but Invisible)

| Feature | Implementation | Visibility | Fix |
|---------|---------------|------------|-----|
| Quiz scoring + error analysis | `evaluation_agent.py` — full LLM analysis per wrong answer | ❌ Quiz panel not in pipeline results | Wire `render_quiz_panel` into `_render_pipeline_results` |
| Resource generation | `ContentGeneratorAgent` + `ResourceAgent` | ⚠️ Only in Workspace tab | Show resource cards in pipeline results |
| Profile analysis dimensions | 6-dim profile with memory stats | ✅ Visible in Profile tab | OK |
| Model transparency | Phase 13.2 AI Engine expander | ⚠️ Empty when run in rule mode (no info to show) | Fix role gate first |

### B. UI存在但没有真实数据 (UI Exists but No Real Data)

| UI Element | Current State | Root Cause |
|------------|--------------|------------|
| Pipeline progress bar | Shows "done (rule-based)" for all stages | LLM never activated |
| Learning plan nodes | Template-generated topics | PlannerAgent in rule mode |
| Quality evaluation score 95 | Constant value | ReviewGate rule mode |
| Quiz questions | Template: "What is the purpose of [topic]?" | EvaluationAgent in rule mode |
| Profile confidence 0.0 | Confidence always zero | ProfileAgent in rule mode |
| Token usage 0 | Always zero | No LLM calls |

### C. Backend存在但未接入 (Backend Exists but Not Connected)

| Backend | Status | Issue |
|---------|--------|-------|
| `create_provider()` | ✅ Reads user config correctly | ❌ Pipeline never calls it for free users |
| `ProviderFactory` (8 providers) | ✅ Full implementation | ❌ Gated behind roles |
| `EvaluationAgent.analyze_wrong_answer()` | ✅ Full LLM error analysis | ❌ Quiz not integrated into pipeline |
| `MetaReflectorAgent` | ✅ Cross-session meta-learning | ❌ No UI mapping at all |
| `TutorAgent` | ✅ Tutoring capability | ❌ No UI tab or integration |

### D. LLM能力缺失 (LLM Capability Gaps)

| Gap | Detail |
|-----|--------|
| **Role gate** | Only PRO/TEACHER/ADMIN can use LLM; normal registration assigns "free" |
| **Permission cascading** | `Permission.available_models` for free = `("mock", "rule")` — even if role gate is bypassed |
| **No LLM fallback visibility** | When rule-only, users see no indication that AI isn't being used |
| **Settings disconnected from pipeline** | User saves DeepSeek key, pipeline ignores it |

### E. Demo感来源 (Sources of Demo Feel)

| Source | Why It Feels Like a Demo |
|--------|--------------------------|
| **Instant pipeline (2ms)** | Real AI takes seconds; instant response = template |
| **Template questions** | "What is the purpose of [topic]?" — obviously not AI-generated |
| **Garbage plan topics** | "闭包与作用域" for beginner Python — no AI would generate this |
| **Fake progress animation** | Yes the bar moves, but all stages say "rule-based" |
| **Zero tokens used** | Real LLM = token cost; zero = no AI |
| **Profile confidence 0.0** | Real AI analysis has measurable confidence |
| **English templates in Chinese context** | Template mismatches reveal non-AI origin |

### F. 推荐修复优先级 (Recommended Fix Priority)

| Priority | Fix | Effort | Impact |
|----------|-----|--------|--------|
| 🔴 **P0** | Remove role gate: allow `create_provider()` to run for all roles | 1 line | Unlocks real AI for all users |
| 🔴 **P0** | Wire `create_provider()` to read user's saved config | Already done | Provider resolution works once gate removed |
| 🟡 **P1** | Integrate quiz panel into pipeline results | ~10 lines | Users see quiz after learning |
| 🟡 **P1** | Show resource cards in pipeline results | ~20 lines | Users see generated content immediately |
| 🟢 **P2** | Add LLM vs Rule indicator in pipeline UI | ~15 lines | Users know when AI is active vs template |
| 🟢 **P2** | Add MetaReflector/TutorAgent UI mapping | ~50 lines | Complete agent coverage |

---

## The Fix (P0)

```python
# src/api/v2/pipeline.py — CURRENT (lines 94-101)
llm_provider = None
if role in (Role.PRO, Role.TEACHER, Role.ADMIN):
    try:
        from src.core.provider_factory import create_provider
        llm_provider = create_provider()
    except Exception:
        pass

# src/api/v2/pipeline.py — FIXED
llm_provider = None
try:
    from src.core.provider_factory import create_provider
    llm_provider = create_provider()
except Exception:
    pass
```

**Effect:** Remove the 1-line role check. `create_provider()` already handles:
- User config from `llm.json` (reads saved API key)
- Environment variable fallback
- Graceful degradation to mock/rule when nothing is configured

---

## Final Answer

**用户下载后感觉像Demo，因为它就是Demo。**

The product has all the UI trappings of an AI learning platform — auth, settings, progress bars, agent names, quiz panels, workspace browser, 2661 tests. But the **LLM is locked behind a role gate** that normal users can never pass. Every interaction the user has — from profile analysis to quiz generation to learning plans — comes from template-based rule engines, not AI.

The fix is one line. Until then, A3-Agent v1.0.0 is a well-polished demo with zero real AI capability accessible to its users.
