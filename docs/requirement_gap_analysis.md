# Competition Requirement Gap Analysis

> Phase 11 — v2.7 → v2.8 Competition Compliance Upgrade
> Date: 2026-07-13
> Baseline: A3 Multi-Agent System v2.7 (10 Agents, 18 Modules, 241 Tests)

---

## Requirement Summary Table

| # | Requirement | Status | Coverage | Priority |
|:--|:------------|:-------|:---------|:---------|
| 1 | LLM-based implementation | 🟡 Partial | 60% | P1 |
| 2 | Multi-agent collaboration | 🟢 Complete | 90% | — |
| 3 | Student profile extraction | 🟢 Complete | 85% | — |
| 4 | Personalized resource generation | 🟡 Partial | 70% | P2 |
| 5 | Learning path planning | 🟢 Complete | 85% | — |
| 6 | Multi-modal resources | 🔴 Missing | 10% | P3 |
| 7 | Learning evaluation | 🟢 Complete | 80% | — |
| 8 | Anti-hallucination | 🔴 Missing | 5% | P5 |
| 9 | Streaming interaction | 🔴 Missing | 0% | P4 |
| 10 | Course knowledge base | 🔴 Missing | 15% | P0 |
| 11 | Xunfei AI compliance | 🟡 Partial | 50% | P6 |

**Overall Coverage: 52%** → Target: ≥85%

---

## Detailed Analysis

### 1. LLM-Based Implementation

**Requirement:** System must use large language models as core reasoning engine, with a clean provider abstraction layer.

**Current Status:** 🟡 Partial (60%)

**Evidence:**
- `src/core/agent_router.py` — Dual-engine router (Xunfei Spark + DeepSeek) with `urllib` direct API calls
- `AgentRouter.route_request()` dispatches to Spark (frontend) or Core (backend)
- Raw HTTP calls hardcoded — no provider interface, no mock for testing
- ProfileAgent and PlannerAgent are rule-only (no LLM for these agents)

**Missing Parts:**
1. No abstract `LLMProvider` interface — each agent calls APIs differently
2. No `MockProvider` for deterministic testing
3. No clean `XunfeiProvider` encapsulation (raw `urllib` in router)
4. No provider registry — adding a new provider requires modifying router

**Priority:** P1 — Foundation for all LLM-dependent features

---

### 2. Multi-Agent Collaboration

**Requirement:** Multiple AI agents with distinct roles must collaborate through shared infrastructure (EventBus, Memory).

**Current Status:** 🟢 Complete (90%)

**Evidence:**
- 10 specialized agents: Profile, ConversationProfile, Planner, ResourceRec, Content, ReviewGate, UserSim, AgentEvaluator, MetaReflector, ImprovementLoop
- `src/core/event_bus.py` — Singleton EventBus with `AgentEventBus.emit()`
- `src/memory/memory_manager.py` — Unified MemoryManager coordinating StudentMemory + ExperienceMemory
- `src/core/agent_trace.py` — AgentTraceCollector monitoring all agent activity
- Dashboard V2 shows 9-agent topology in System Overview panel

**Missing Parts:**
- No agent orchestration framework (agents are pipeline, not autonomous)
- No inter-agent negotiation protocol
- Minor: some agents (ReviewGate, ContentAgent) operate standalone

**Priority:** — (minor gaps only)

---

### 3. Student Profile Extraction

**Requirement:** System extracts multi-dimensional student profiles from natural language input.

**Current Status:** 🟢 Complete (85%)

**Evidence:**
- `src/agents/profile_agent.py` — Rule + LLM dual-mode 6-dim extraction
- `src/agents/conversation_profile_agent.py` — Multi-turn profile collection with completeness check
- 6 dimensions: knowledge_base, cognitive_style, error_prone_bias, learning_pace, interaction_preference, frustration_threshold
- 23 tests in `test_profile_agent.py` + 18 tests in `test_conversation_profile_agent.py`

**Missing Parts:**
- No confidence scores on extracted dimensions
- No profile versioning/history diff
- Conversation profiles are rule-only (no LLM enrichment for unclear inputs)

**Priority:** — (minor gaps)

---

### 4. Personalized Resource Generation

**Requirement:** System generates personalized learning resources adapted to student profiles.

**Current Status:** 🟡 Partial (70%)

**Evidence:**
- `src/agents/resource_recommendation_agent.py` — Decides WHAT resources to recommend (7 types)
- `src/core/content_agent.py` — 5-asset contract: tutorial, mindmap, quiz, extended, sandbox
- Mastery-based recommendation: mastery<0.3 → basics, ≥0.8 → challenges
- Visual-dominant profiles auto-trigger visual resources

**Missing Parts:**
1. No **ResourceGenerationAgent** — ContentAgent exists but generates via LLM, not a dedicated agent
2. Missing dedicated agents for: course_notes, mind_map, exercises, code_labs, video_scripts
3. Content generation is tightly coupled to LLM calls — no offline/cached generation
4. No resource versioning or quality grading

**Priority:** P2 — New ResourceGenerationAgent with 5 sub-generators

---

### 5. Learning Path Planning

**Requirement:** System plans personalized learning paths based on student profiles and course structure.

**Current Status:** 🟢 Complete (85%)

**Evidence:**
- `src/agents/planner_agent.py` — 541 lines, 26 tests
- 3 courses: python_basics (4 nodes), python_advanced (4 nodes), multi_agent_ai (16 nodes, 5 levels)
- Auto-detection: `detect_course()` with 22 Chinese/English keywords
- Profile-driven: pace affects depth, skip_detail_nodes, exercise_count
- Alternative paths generated for different profiles

**Missing Parts:**
- Knowledge graph is hardcoded in Python (not loaded from structured files)
- No prerequisite validation across courses
- No real-time path adjustment based on student performance

**Priority:** — (addressed in P0 — KB extraction)

---

### 6. Multi-Modal Resources

**Requirement:** Learning resources must include multiple modalities: text, diagrams, videos, code, interactive labs.

**Current Status:** 🔴 Missing (10%)

**Evidence:**
- ContentAgent generates Mermaid mindmaps (text-based diagrams)
- ResourceRecommendationAgent lists resource types but doesn't generate multimodal content
- No image generation, no video, no audio narration
- Dashboard V2 displays text-only resource cards
- `[MULTI_MODAL_SLOT: ...]` placeholder exists but no backend filling

**Missing Parts:**
1. No multimedia resource generation pipeline
2. Dashboard cards are text-only — no `document`/`mindmap`/`video`/`code` visual card types
3. No resource format registry
4. No file-based resource storage (all in-memory)

**Priority:** P3 — Multimodal resource cards in Dashboard

---

### 7. Learning Evaluation

**Requirement:** System evaluates learning quality through multiple mechanisms and provides feedback.

**Current Status:** 🟢 Complete (80%)

**Evidence:**
- `src/evaluation/judge.py` — RuleJudge + LLMJudge, 4-dimension scoring
- `src/evaluation/agent_evaluator.py` — AgentEvaluator per-agent scoring
- `src/evaluation/evaluator.py` — RuleBasedJudge + EvaluationRunner
- `src/core/review_gate.py` — 3-gate content review (AST + Pytest + Judge)
- `src/core/user_simulation.py` — First-person learning simulation
- `src/core/improvement_loop.py` — Low-score → reflection → strategy update
- 20-student benchmark dataset

**Missing Parts:**
- No student-facing quiz engine (only RuleJudge for agent evaluation)
- No learning analytics dashboard (mastery trends over time)
- UserSim scores content quality, not student learning outcomes

**Priority:** — (minor gaps)

---

### 8. Anti-Hallucination

**Requirement:** System must prevent AI hallucinations through knowledge grounding, confidence scoring, and feedback loops.

**Current Status:** 🔴 Missing (5%)

**Evidence:**
- ReviewGate's AST Gate validates code syntax (prevents code hallucination at structural level)
- UserSimulationAgent scores content quality (<85 triggers hotfix)
- ExperienceMemory stores failure patterns
- No explicit hallucination detection mechanism
- No confidence scores on generated content
- No knowledge grounding against authoritative sources
- No documentation of anti-hallucination design

**Missing Parts:**
1. No confidence scoring in content generation
2. No knowledge grounding (RAG against knowledge base)
3. No source attribution for generated facts
4. No anti-hallucination design documentation

**Priority:** P5 — Documentation + confidence score framework

---

### 9. Streaming Interaction

**Requirement:** System should support streaming (token-by-token) response delivery for real-time UX.

**Current Status:** 🔴 Missing (0%)

**Evidence:**
- All agent communication is synchronous batch (no streaming)
- `AgentRouter._call_api()` uses `urllib.request.urlopen()` — no SSE/streaming support
- Dashboard panels display final results only
- No streaming demo or simulation mechanism

**Missing Parts:**
1. No streaming protocol in any provider
2. No token-level event emission
3. No streaming visualization in dashboard
4. No streaming simulation utility

**Priority:** P4 — Streaming demo utility + EventBus integration

---

### 10. Course Knowledge Base

**Requirement:** System must have a structured, file-based course knowledge base with chapters, resources, and exercises.

**Current Status:** 🔴 Missing (15%)

**Evidence:**
- PlannerAgent has 3 hardcoded knowledge graphs in Python dicts
- `multi_agent_ai` course: 16 nodes in `DEFAULT_KNOWLEDGE_GRAPH`
- `COURSE_KEYWORDS`: 22 keyword strings for detection
- No separate knowledge base files (all embedded in code)
- No chapter-level organization with descriptions
- No exercise bank or resource library files

**Missing Parts:**
1. No `knowledge_base/` directory structure
2. No chapter files with learning objectives
3. No structured `resources.json` / `exercises.json`
4. Knowledge is code, not data — hard to extend without code changes
5. Competition requires a visible, browsable knowledge base

**Priority:** P0 — Foundation for all content-related requirements

---

### 11. Xunfei AI Compliance

**Requirement:** System must demonstrate compliance with Xunfei (讯飞) Spark AI competition requirements, including API integration point.

**Current Status:** 🟡 Partial (50%)

**Evidence:**
- `AgentRouter` has Xunfei Spark API integration: `XF_SPARK_API_KEY`, `XF_SPARK_BASE_URL`
- Frontend agents (ContentAgent, ProfileAgent, OnboardingAgent) route to Spark
- `DynamicProfile.to_system_prompt_hint()` generates Spark-compatible prompts
- `agent_router.py:240` — runnable CLI demo

**Missing Parts:**
1. No compliance documentation explaining how the system meets Xunfei requirements
2. No API integration guide or configuration reference
3. No mention of Spark model version compatibility
4. No rate limiting or quota management documentation
5. No fallback/graceful degradation when Spark is unavailable

**Priority:** P6 — Compliance documentation + API guide

---

## Implementation Plan

| Phase | Priority | Deliverable | Estimated Lines |
|:------|:---------|:------------|:----------------|
| P0 | 🔴 Critical | `knowledge_base/` — 6 chapters, resources.json, exercises.json | ~800 |
| P1 | 🔴 High | `src/llm/` — provider.py, mock_provider.py, xunfei_provider.py | ~300 |
| P2 | 🟡 Medium | `src/agents/resource_generation_agent.py` — 5 generators | ~400 |
| P3 | 🟡 Medium | Dashboard multimodal resource cards (document/mindmap/video/code) | ~200 |
| P4 | 🟢 Low | `utils/streaming.py` — token streaming simulation | ~150 |
| P5 | 🟢 Low | `docs/safety_design.md` — anti-hallucination design | ~300 |
| P6 | 🟢 Low | `docs/ai_tools_compliance.md` — Xunfei compliance | ~200 |

**Total estimated new code: ~2,350 lines**

---

## Risk Assessment

| Risk | Severity | Mitigation |
|:-----|:---------|:-----------|
| LLM abstraction breaks existing AgentRouter | Medium | Provider interface wraps existing API calls; AgentRouter delegates to provider |
| Knowledge base out of sync with PlannerAgent | Medium | PlannerAgent reads from KB files; auto-validate on test |
| ResourceGenerationAgent duplicates ContentAgent | Low | ContentAgent handles LLM content; ResourceGenerationAgent handles format transformation |
| Streaming adds EventBus overhead | Low | Optional; only enabled in demo mode |
