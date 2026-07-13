# A3 Multi-Agent Learning System — Project Knowledge

> **Complete technical summary** | v2.6 | 8,727 lines src + 1,810 lines web | 241 tests (97.4% pass)
>
> Generated: 2026-07-13 | Scope: all layers, all agents, full data flow

---

## 1. Project Overview

### Motivation

Traditional AI tutoring systems face four fundamental problems:

1. **One-size-fits-all** — static curricula don't adapt to individual learners
2. **Black-box decisions** — students can't see *why* content was chosen
3. **No self-correction** — systems repeat the same mistakes
4. **No observability** — teachers can't inspect what the AI is doing

### Goals

Build an AI learning system that is:

| Property | Implementation |
|:---------|:---------------|
| **Personalized** | 6-dim student profile extracted from natural language |
| **Explainable** | Every agent decision has evidence + confidence |
| **Self-improving** | Low-quality outputs trigger reflection → stored strategy |
| **Observable** | 6-panel dashboard shows every decision, trace, and evaluation |

### Main Capabilities

1. **Profile extraction** — NL → 6-dim DynamicProfile (rule engine + optional LLM)
2. **Learning path generation** — auto-detect curriculum from goal text, personalize by student profile
3. **Resource recommendation** — 7 resource types with explainable reasons, mastery-gated
4. **Quality evaluation** — 4-dim scoring (correctness/personalization/explainability/efficiency)
5. **Self-reflection** — root-cause analysis of failures → stored improvement strategies
6. **Visualization dashboard** — 6-panel Streamlit observatory with demo + runtime modes

---

## 2. Architecture

### Agent Layer

10 specialized agents with single responsibilities:

```
ProfileAgent → PlannerAgent → ResourceRecommendationAgent → AgentEvaluator
                                                                     │
                                                     ┌───────────────┘
                                                     ▼
                                           MetaReflector → ImprovementLoop
```

| Agent | File | Lines | Responsibility |
|:------|:-----|:-----:|:---------------|
| **ProfileAgent** | `src/agents/profile_agent.py` | 363 | NL → 6-dim DynamicProfile (rule engine + optional LLM) |
| **ConversationProfileAgent** | `src/agents/conversation_profile_agent.py` | 545 | Multi-turn dialogue → gradual profile collection |
| **PlannerAgent** | `src/agents/planner_agent.py` | 541 | Profile + curriculum → LearningPlan (auto-detect + personalize) |
| **ResourceRecommendationAgent** | `src/agents/resource_recommendation_agent.py` | 444 | Memory + profile → resource plan (7 types, explainable) |
| **ContentAgent** | `src/core/content_agent.py` | 243 | Generate 5-asset learning content (tutorial/mindmap/quiz/extended/sandbox) |
| **ReviewGate** | `src/core/review_gate.py` | 741 | 3-gate quality check (AST + Pytest + Judge) |
| **UserSimulationAgent** | `src/core/user_simulation.py` | 836 | First-person cognitive simulation for content scoring |
| **AgentEvaluator** | `src/evaluation/agent_evaluator.py` | 209 | 4-dim quality scoring with RuleJudge + LLMJudge backends |
| **MetaReflector** | `src/core/meta_reflector.py` | 245 | Root-cause analysis of failures → ImprovementSuggestion |
| **ImprovementLoop** | `src/core/improvement_loop.py` | 240 | Low-score detection → reflection → strategy update pipeline |

**Communication:** All agents communicate through `AgentEventBus` (singleton). No direct agent-to-agent coupling.

**Reasoning types:**
- `rule` — deterministic keyword matching (ProfileAgent, PlannerAgent)
- `heuristic` — priority-based decisions (ResourceRecommendationAgent, MetaReflector)
- `llm` — LLM API calls (ContentAgent, optional PlannerAgent extension)
- `memory` — decisions driven by StudentMemory/ExperienceMemory
- `hybrid` — combined rule + memory reasoning

### Runtime Layer

| Component | File | Lines | Responsibility |
|:----------|:-----|:-----:|:---------------|
| **EventBus** | `src/core/event_bus.py` | 199 | Singleton event system — all agents emit events (agent/action/status/duration) |
| **AgentRouter** | `src/core/agent_router.py` | 240 | Dual-engine routing — frontend agents (fast) vs backend agents (DeepSeek) |
| **TraceCollector** | `src/core/agent_trace.py` | 226 | Listens to EventBus → enhanced TraceEvents with reasoning_type → JSON persistence |
| **FeedbackLoop** | `src/core/feedback_loop.py` | 298 | UserSim scores → MetaReflector recall → prompt optimization → re-generation |
| **PromptInjector** | `src/core/prompt_injector.py` | - | Dual-track prompt: profile-aware + teaching strategy injection |
| **Contracts** | `src/core/contracts.py` | 253 | FeedbackRecord + Lesson data models |
| **Sandbox** | `src/core/sandbox.py` | 713 | Transaction sandbox for safe code execution |
| **Quarantine** | `src/core/quarantine.py` | - | Freeze/isolation layer for failed content |
| **ReverseCommitter** | `src/core/reverse_committer.py` | - | HITL (Human-in-the-Loop) commit validation |

**Execution flow:**
```
Agent.execute()
    │
    ▼
AgentEventBus.emit(agent, action, input, output, status, duration)
    │
    ├──→ AgentTraceCollector.sync_from_bus()  [enhance with reasoning_type]
    │         │
    │         └──→ collector.save()  [JSON → storage/memory/traces/]
    │
    └──→ Web Dashboard reads EventBus.get_timeline()
```

### Memory Layer

```
┌─────────────────────────────────────────────┐
│              MemoryManager                    │
│         (unified access point)                │
├─────────────────┬───────────────────────────┤
│ StudentMemory   │ ExperienceMemory           │
│                 │                             │
│ profile_history │ problem / cause             │
│ mastery_map     │ context / solution          │
│ (EMA α=0.5)     │ applicable_profile          │
│ weak_points     │ success_rate                │
│ feedback_history│ usage_count                 │
│ session_summary │ keywords                    │
│                 │                             │
│ JSON storage:   │ JSON storage:               │
│ storage/memory/ │ storage/memory/             │
│ students/<id>.json│ experience/records.json   │
└─────────────────┴───────────────────────────┘
```

| Component | File | Lines | Key Feature |
|:----------|:-----|:-----:|:------------|
| **StudentMemoryStore** | `src/memory/student_memory.py` | 353 | EMA mastery tracking (α=0.5), profile history, weak points |
| **ExperienceMemoryStore** | `src/memory/experience_memory.py` | 375 | Keyword-matched recall, success-rate weighted, 5 pre-seeded lessons |
| **MemoryManager** | `src/memory/memory_manager.py` | 170 | Unified API, auto-seeding, batch update |

**Mastery tracking:** `new_mastery = old × 0.5 + update × 0.5` (exponential moving average). Thresholds: ≥0.8 → mastered (skip), ≤0.3 → weak (boost).

**Experience recall:** Token-based matching → substring matching → success-rate ranking. API designed for future ChromaDB/Vector DB replacement.

### Evaluation Layer

| Component | File | Lines | Responsibility |
|:----------|:-----|:-----:|:---------------|
| **RuleJudge** | `src/evaluation/judge.py` | 264 | Deterministic scoring: checks output structure, field completeness |
| **LLMJudge** | `src/evaluation/judge.py` | (same) | Reserved: LLM-powered nuanced evaluation |
| **AgentEvaluator** | `src/evaluation/agent_evaluator.py` | 209 | 4-dim scoring per agent, history tracking, batch evaluation |
| **EvaluationRunner** | `src/evaluation/evaluator.py` | 483 | Benchmark runner: 20 simulated students, batch scoring |

**Scoring dimensions:**
| Dimension | Weight | RuleJudge checks |
|:----------|:------:|:-----------------|
| Correctness | 0.35 | Output structure, field presence, format validity |
| Personalization | 0.30 | Memory integration, mastery-aware decisions |
| Explainability | 0.20 | Reason fields present, evidence chains |
| Efficiency | 0.15 | Step count, redundancy detection |

**Baseline scoring:** Empty outputs get 0.25 (not 0.0) to prevent unstable weighted sums. Personalization + explainability default to 0.3 baseline.

### Dashboard Layer

```
web/
├── app.py              (70 lines)   V1 bootstrap → delegates to web/v1/
├── app_v2.py           (179 lines)  V2 standalone 6-panel observatory
├── v1/
│   ├── pipeline.py     (139 lines)  Agent init + pipeline execution
│   └── components.py   (217 lines)  5 panel renderers + landing
└── dashboard/
    ├── data_providers.py (625 lines) Data access + demo seed (6 get_* functions)
    └── components.py     (496 lines) Pure Streamlit rendering (6 render_* functions)
```

**Dashboard V1 (web/app.py):**
5 interactive panels — student inputs text, pipeline runs, results displayed live:
1. Profile completeness bar
2. Dynamic profile card
3. Learning path visualization
4. Resource recommendation cards
5. Agent trace timeline

**Dashboard V2 (web/app_v2.py):**
6-panel read-only observatory, demo + runtime dual mode:
1. System Overview (9-agent topology, memory/eval stats)
2. Student Intelligence (6-dim profile, mastery heatmap, weak points)
3. Execution Timeline (12 events with reasoning_type + latency)
4. Decision Explainability (8 decisions with evidence + confidence)
5. Agent Evaluation (4 agents, 4 dimensions each)
6. Self Improvement (failure → eval → reflection → experience → strategy)

**Architecture constraint:** Dashboard NEVER creates agents. It reads from shared infrastructure (EventBus singleton, TraceCollector, MemoryManager). Demo mode uses seed data with zero runtime dependencies.

---

## 3. Data Flow — Complete Lifecycle

```
                        ┌──────────────────────┐
                        │   Student Input (NL)  │
                        │   "I want to learn    │
                        │   Multi-Agent AI..."  │
                        └──────────┬───────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                              ▼
          ┌──────────────────┐          ┌──────────────────┐
          │ProfileAgent      │          │ConversationProfile│
          │(rule-mode, 6-dim)│          │Agent (multi-turn)│
          │                  │          │                  │
          │knowledge_base:   │          │completeness check│
          │  junior_dev      │          │追问 missing dims  │
          │cognitive_style:  │          │max 8 rounds      │
          │  visual_dominant │          └────────┬─────────┘
          │learning_pace:    │                   │
          │  normal          │                   │
          │ ...              │                   │
          └────────┬─────────┘                   │
                   │                             │
                   └──────────┬──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  StudentMemory    │
                    │  persist profile  │
                    │  + mastery_map    │
                    └────────┬─────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ PlannerAgent      │
                    │                   │
                    │ detect_course()   │
                    │ → multi_agent_ai  │
                    │                   │
                    │ Generate 16 nodes │
                    │ 5 levels          │
                    │ personalize by:   │
                    │  - pace           │
                    │  - cognitive      │
                    │  - mastery        │
                    └────────┬─────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ResourceRecAgent   │
                    │                   │
                    │ Read mastery_map  │
                    │ weak<0.3 → boost  │
                    │ visual→graphics   │
                    │                   │
                    │ 6 resources       │
                    │ with reasons      │
                    └────────┬─────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ AgentEvaluator    │
                    │                   │
                    │ 4-dim scoring:    │
                    │ correctness 0.35  │
                    │ personalization   │
                    │   0.30            │
                    │ explainability    │
                    │   0.20            │
                    │ efficiency 0.15   │
                    └────────┬─────────┘
                              │
                    ┌─────────┴──────────┐
                    │ score ≥ 0.5?       │
                    └────┬────────┬──────┘
                    YES  │        │  NO
                         │        │
                         ▼        ▼
                    PASS    ┌──────────────────┐
                            │ MetaReflector     │
                            │ root cause:       │
                            │ "difficulty       │
                            │  mismatch"        │
                            └────────┬─────────┘
                                     │
                                     ▼
                            ┌──────────────────┐
                            │ ImprovementLoop   │
                            │ → suggestion      │
                            └────────┬─────────┘
                                     │
                                     ▼
                            ┌──────────────────┐
                            │ ExperienceMemory  │
                            │ persist lesson    │
                            └────────┬─────────┘
                                     │
                                     ▼
                            Next run: auto-fix

        ═══════════════════════════════════════
        All events flow through EventBus →
        TraceCollector → Dashboard V2
        ═══════════════════════════════════════
```

---

## 4. Design Decisions

### Why EventBus?

**Problem:** 10 agents need to communicate without creating a spaghetti of direct dependencies.

**Decision:** Singleton EventBus with publish-subscribe pattern.

**Trade-offs:**
- ✅ Decoupled agents — ProfileAgent doesn't import PlannerAgent
- ✅ Universal observability — Dashboard reads one source for all events
- ✅ Test isolation — `reset_instance()` between tests
- ⚠️ Global state — singleton pattern requires careful test cleanup

### Why Multi-Agent?

**Problem:** Single LLM systems face context dilution, no self-correction, and no audit trail.

**Decision:** 10 specialized agents, each with a single responsibility.

**Trade-offs:**
- ✅ Clear accountability — each agent has defined input/output contracts
- ✅ Independent evaluation — AgentEvaluator can grade every agent
- ✅ Replaceable components — swap PlannerAgent without touching ProfileAgent
- ⚠️ More infrastructure — EventBus, TraceCollector, MemoryManager required

### Why Memory?

**Problem:** Without memory, the system is amnesiac — repeats recommendations, forgets mastery, can't learn from mistakes.

**Decision:** Two-tier memory: StudentMemory (per-learner state) + ExperienceMemory (cross-learner lessons).

**Trade-offs:**
- ✅ Personalized paths — PlannerAgent reads mastery_map
- ✅ Self-improvement — MetaReflector stores → ImprovementLoop recalls
- ✅ Cross-session continuity — persistence survives restarts
- ⚠️ JSON storage — simple but not scalable; Vector DB migration path designed

### Why Evaluation?

**Problem:** Without self-evaluation, the system can't detect when it produces bad output.

**Decision:** RuleJudge (deterministic, no API cost) for baseline scoring; LLMJudge reserved for nuanced evaluation.

**Trade-offs:**
- ✅ Deterministic scores — reproducible, auditable
- ✅ Triggers improvement — low scores activate MetaReflector
- ✅ Zero API cost — RuleJudge runs locally
- ⚠️ Limited nuance — RuleJudge checks structure, not semantic quality

### Why Reflection?

**Problem:** Detecting failure is not enough — the system needs to *understand why* and *remember the fix*.

**Decision:** MetaReflector analyzes attempt history → diagnoses root cause → ImprovementLoop generates strategies → ExperienceMemory persists.

**Trade-offs:**
- ✅ Closed loop — failure → diagnosis → fix → prevent recurrence
- ✅ Growing intelligence — ExperienceMemory accumulates lessons over time
- ✅ Pre-seeded — 5 default lessons ship with the system
- ⚠️ Heuristic diagnosis — attempt-count-based, not semantic understanding

### Why Dashboard?

**Problem:** Multi-agent systems are inherently complex. Without visualization, judges and users can't see what's happening.

**Decision:** 6-panel Streamlit observatory with demo + runtime dual mode.

**Trade-offs:**
- ✅ Full observability — every decision, trace, and evaluation visible
- ✅ Instant showcase — demo mode works with zero runtime data
- ✅ Zero core coupling — dashboard reads shared infrastructure, never creates agents
- ⚠️ Python-only — Streamlit dependency, not a web-native SPA

---

## 5. File Map

### Source Layer (`src/`)

#### Agents (`src/agents/`)
| File | Lines | Responsibility |
|:-----|:-----:|:---------------|
| `profile_agent.py` | 363 | NL → 6-dim DynamicProfile (rule engine + optional LLM) |
| `conversation_profile_agent.py` | 545 | Multi-turn dialogue → gradual profile collection (8 rounds max) |
| `planner_agent.py` | 541 | Profile + curriculum → personalized LearningPlan; auto-detect course from goal text |
| `resource_recommendation_agent.py` | 444 | Memory + profile → resource plan (7 types, explainable reasons) |

#### Core Runtime (`src/core/`)
| File | Lines | Responsibility |
|:-----|:-----:|:---------------|
| `event_bus.py` | 199 | Singleton EventBus: emit/get_timeline/reset/clear |
| `agent_router.py` | 240 | Dual-engine: frontend (fast) vs backend (DeepSeek) agent routing |
| `agent_trace.py` | 226 | TraceCollector: enhance EventBus events → JSON persistence |
| `decision_explainer.py` | 281 | Explain profile/plan/recommendation/memory decisions with evidence |
| `improvement_loop.py` | 240 | Low-score detection → reflection → ImprovementSuggestion generation |
| `meta_reflector.py` | 245 | Root-cause analysis: attempt count → diagnosis type |
| `feedback_loop.py` | 298 | UserSim scores → MetaReflector recall → prompt optimization |
| `content_agent.py` | 243 | 5-asset content generation contract |
| `contracts.py` | 253 | FeedbackRecord + Lesson data models |
| `prompt_injector.py` | - | Dual-track prompt injection (profile-aware + teaching strategy) |
| `review_gate.py` | 741 | 3-gate quality check: AST + Pytest + Judge |
| `sandbox.py` | 713 | Transaction sandbox for safe code execution |
| `user_simulation.py` | 836 | First-person cognitive simulation: profile-driven content scoring |
| `quarantine.py` | - | Freeze/isolation layer for failed content |
| `reverse_committer.py` | - | Human-in-the-Loop commit validation |

#### Memory (`src/memory/`)
| File | Lines | Responsibility |
|:-----|:-----:|:---------------|
| `student_memory.py` | 353 | StudentMemoryStore: profile history, EMA mastery, weak points, feedback |
| `experience_memory.py` | 375 | ExperienceMemoryStore: keyword search, success-rate ranking, seeding |
| `memory_manager.py` | 170 | Unified API: get/update student, recall/store experience |

#### Evaluation (`src/evaluation/`)
| File | Lines | Responsibility |
|:-----|:-----:|:---------------|
| `agent_evaluator.py` | 209 | 4-dim per-agent scoring, history tracking, batch evaluation |
| `judge.py` | 264 | RuleJudge (deterministic) + LLMJudge (reserved) unified interface |
| `evaluator.py` | 483 | Benchmark runner: 20 simulated students, EvaluationReport generation |

### Web Layer (`web/`)
| File | Lines | Responsibility |
|:-----|:-----:|:---------------|
| `app.py` | 70 | V1 bootstrap: page config → sidebar → pipeline → panels |
| `app_v2.py` | 179 | V2 standalone: 6-panel observatory, demo/runtime mode switch |
| `v1/pipeline.py` | 139 | Agent init (@st.cache_resource) + pipeline execution (profile→plan→rec) |
| `v1/components.py` | 217 | 5 V1 panel renderers + landing page |
| `dashboard/data_providers.py` | 625 | Data access/transform layer: 6 get_* + get_demo_all + seed data |
| `dashboard/components.py` | 496 | Pure Streamlit rendering: 6 render_* panel functions |

### Tests (`tests/`)
| File | Tests | Scope |
|:-----|:-----:|:------|
| `test_profile_agent.py` | 23 | Profile extraction, keyword matching, LLM extension |
| `test_planner_agent.py` | 26 | Plan generation, pace/cognitive adjustments, multi-agent curriculum |
| `test_conversation_profile_agent.py` | 18 | Multi-turn dialogue, completeness checking |
| `test_resource_recommendation_agent.py` | 11 | Resource recommendation, mastery-gating |
| `test_student_memory.py` | 16 | CRUD, EMA mastery, persistence |
| `test_experience_memory.py` | 11 | Search, recall, success rate, seeding |
| `test_memory_integration.py` | 13 | Agent ↔ Memory integration |
| `test_memory_changes_behavior.py` | 8 | Memory-aware behavior changes |
| `test_event_bus.py` | 12 | Emit, timeline, singleton, reset |
| `test_agent_trace.py` | 19 | Trace collection, reasoning_type, persistence |
| `test_evaluation.py` | 14 | RuleJudge/LLMJudge, benchmark runner |
| `test_agent_evaluation.py` | 21 | AgentEvaluator, ImprovementLoop integration |
| `test_review_gate.py` | 30 | AST/Pytest/Judge gates, full pipeline |
| `test_user_simulation.py` | 16 | Cognitive simulation, profile-driven scoring |
| `test_feedback_loop.py` | 13 | UserSim → Feedback → re-generation |

### Data (`datasets/`, `storage/`, `checkpoints/`)
| Path | Purpose |
|:-----|:--------|
| `datasets/students/benchmark.json` | 20 simulated student profiles (8 beginner + 6 intermediate + 4 advanced + 2 edge) |
| `storage/memory/students/<id>.json` | Per-student memory (profile, mastery, feedback) |
| `storage/memory/experience/records.json` | Cross-student experience lessons |
| `storage/memory/traces/<session>.json` | Persistent trace events |
| `storage/demo/` | Demo scenario data |
| `checkpoints/` | Development phase completion records |

### Documentation (`docs/`)
| File | Purpose |
|:-----|:--------|
| `architecture.md` | Full system architecture with ASCII diagrams |
| `demo_story.md` | 5-minute competition demo script (6 scenes) |
| `competition_outline.md` | 10-slide PPT structure |
| `competition_qa.md` | 10 prepared Q&A answers |
| `screenshots/README.md` | Dashboard screenshot capture guide |

---

## 6. Development Timeline

### Phase 1-3: Foundation (v1.0)
- Core agents: ContentAgent, ReviewGate, UserSimulationAgent, FeedbackLoop
- Pipeline: content generation → quality gate → simulation → feedback
- Contracts: FeedbackRecord, Lesson data models
- Sandbox + Quarantine + ReverseCommitter for safe content handling

### Phase 4: ContentAgent 5-Asset Contract
- Standardized output: tutorial, mindmap, quiz, extended reading, sandbox exercise
- `content_agent.py` — strong-type output contract

### Phase 5: Student Entry + Feedback Loop (v2.0)
- `ProfileAgent` — NL → 6-dim DynamicProfile (rule engine + LLM extension)
- `PlannerAgent` — Profile + curriculum → LearningPlan
- `FeedbackLoop` — UserSim → MetaReflector → prompt optimization
- Streamlit Web Demo v1

### Phase 6: Memory System (v2.1)
- `StudentMemoryStore` — profile history, mastery map (EMA α=0.5), weak points
- `ExperienceMemoryStore` — failure pattern library, keyword search, 5 pre-seeded lessons
- `MemoryManager` — unified access layer, auto-seeding

### Phase 7: Platform Upgrade (v2.3-v2.4)
- `EventBus` — singleton agent event system
- `ResourceRecommendationAgent` — 7 resource types, explainable recommendations
- `EvaluationRunner` + `Benchmark Dataset` — 20 simulated students, batch scoring

### Phase 7.3A: Dashboard V1 Extraction
- `app.py` → `web/v1/pipeline.py` + `web/v1/components.py`
- Thin bootstrap pattern: 70-line app.py delegates to extracted modules

### Phase 7.3B: Dashboard V2 (v2.5)
- 6-panel observatory: `web/dashboard/data_providers.py` + `components.py`
- `web/app_v2.py` — standalone entry point
- Demo mode: instant showcase with seed data, zero runtime dependencies

### Phase 7.4: Runtime Replay & Demo Validation
- End-to-end verification: ProfileAgent → StudentMemory → PlannerAgent → ResourceRecommendationAgent → AgentEvaluator → ImprovementLoop → Dashboard
- All 14 runtime checks pass
- Demo data seed created

### Phase 7.5: Planner Curriculum Expansion
- New curriculum: `multi_agent_ai` (16 topics, 5 levels: LLM→Agent→Architecture→Runtime→Optimization)
- `detect_course()` — keyword-based curriculum auto-detection (22 keywords, EN+ZH)
- 8 new tests, backward compatible with existing Python curriculum

### Phase 8: Competition Demo Package
- `README.md` — complete project README with badges, architecture, quick start
- `docs/demo_story.md` — 6-scene, 5-minute competition demo script
- `docs/architecture.md` — full architecture with ASCII diagrams
- `docs/competition_outline.md` — 10-slide PPT structure
- Demo data polish: Python concepts → Agent concepts across all 6 panels

### Phase 9: Competition Rehearsal & Final Polish
- `docs/competition_qa.md` — 10 prepared Q&A answers
- `docs/screenshots/README.md` — screenshot capture guide
- Documentation review: consistent terminology across all files
- Final regression: 241/245 tests pass, imports verified

---

## 7. Future Roadmap

### Near-term (Post-Competition)

| Priority | Item | Effort | Impact |
|:---------|:-----|:------:|:------:|
| 🔴 | Real student A/B testing | 2 weeks | Validation |
| 🔴 | ChromaDB/Vector DB migration | 1 week | Scalable experience search |
| 🟡 | LLM-powered PlannerAgent | 3 days | Beyond keyword matching |
| 🟡 | Fix 4 test_review_gate failures | 2 hours | Clean CI |
| 🟢 | Multi-modal content generation | 1 week | Diagrams, videos, interactive sim |

### Long-term Vision

| Item | Description |
|:-----|:------------|
| **Cross-domain curriculum auto-generation** | Scan textbooks/syllabi → auto-build knowledge graphs |
| **Federated learning** | Aggregate experience across student cohorts without sharing private data |
| **Real-time collaboration** | Multiple students learn same topic, agents coordinate group activities |
| **Adaptive difficulty** | Real-time mastery tracking → dynamic difficulty adjustment during sessions |
| **Teacher dashboard** | Instructor view: class-level insights, intervention suggestions, cohort analysis |

### Architecture Evolution

```
Current (v2.6)              →  Near-term                →  Long-term
─────────────────────────────────────────────────────────────────────
JSON Memory                  →  ChromaDB/Vector          →  Federated stores
Rule-based PlannerAgent      →  LLM + Rule hybrid        →  Full semantic planning
Python-only dashboard        →  React SPA                →  Mobile + Web
Single-user pipeline         →  Multi-user isolation      →  Cohort-aware
Static curriculum            →  Auto-generated            →  Real-time adaptive
```
