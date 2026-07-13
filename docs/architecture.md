# A3 Multi-Agent System — Architecture

> v2.6 | 18 modules | ~6,500 lines | 241 tests

---

## Overview

A3 is a **multi-agent personalized learning system**. Students describe their goals in natural language, and a pipeline of specialized AI agents collaboratively generates personalized learning paths, recommends resources, evaluates quality, and continuously improves through self-reflection.

---

## Architecture Diagram

```
                         ┌─────────────────────┐
                         │    Student Input     │
                         │  "I want to learn    │
                         │   Multi-Agent AI..." │
                         └──────────┬──────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────┐
│                    Multi-Agent Runtime                             │
│                                                                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │ Profile  │  │ Planner  │  │ Resource │  │Evaluator │         │
│  │  Agent   │→ │  Agent   │→ │Rec Agent │→ │  Agent   │         │
│  └──────────┘  └──────────┘  └──────────┘  └────┬─────┘         │
│                                                  │               │
│                        ┌─────────────────────────┘               │
│                        ▼                                          │
│              ┌──────────────┐    ┌──────────────┐                │
│              │MetaReflector │ →  │Improvement   │                │
│              │ (Reflection) │    │    Loop      │                │
│              └──────────────┘    └──────────────┘                │
│                                                                    │
├───────────────────────────────────────────────────────────────────┤
│                     Infrastructure Layer                           │
│                                                                    │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐           │
│  │Memory    │  │  EventBus    │  │ AgentTrace       │           │
│  │Manager   │  │  (Singleton) │  │  Collector       │           │
│  └──────────┘  └──────────────┘  └──────────────────┘           │
│                                                                    │
│  ┌──────────────┐  ┌──────────────┐                               │
│  │Decision      │  │ Experience   │                               │
│  │Explainer     │  │ Memory       │                               │
│  └──────────────┘  └──────────────┘                               │
└───────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │   Dashboard V2       │
                         │  6-Panel Observatory │
                         │  (Streamlit)         │
                         └─────────────────────┘
```

---

## Agent Roles

| Agent | Responsibility | Reasoning |
|:------|:---------------|:----------|
| **ProfileAgent** | NL → 6-dim DynamicProfile | Rule engine (keywords + priority) |
| **ConversationProfileAgent** | Multi-turn profile collection | Completeness checker +追问 |
| **PlannerAgent** | Profile + curriculum → LearningPlan | 5-level curriculum auto-detection |
| **ResourceRecommendationAgent** | Memory + profile → resource plan | Mastery-based 7-type recommendation |
| **ContentAgent** | 5-asset content generation | LLM-driven (tutorial/mindmap/quiz/extended/sandbox) |
| **ReviewGate** | 3-gate quality check | AST + Pytest + Judge |
| **UserSimulationAgent** | First-person learning simulation | Cognitive-profile-driven scoring |
| **AgentEvaluator** | 4-dim quality scoring | RuleJudge + LLMJudge |
| **MetaReflector** | Failure root-cause analysis | Attempt-count-based diagnosis |
| **ImprovementLoop** | Low-score → strategy update | Evaluation-driven suggestions |

---

## Memory System

```
StudentMemory          ExperienceMemory
┌─────────────────┐    ┌─────────────────┐
│ profile_history  │    │ problem         │
│ mastery_map (EMA)│    │ cause           │
│ weak_points      │    │ solution        │
│ feedback_history │    │ success_rate    │
│ session_summary  │    │ keywords        │
└─────────────────┘    └─────────────────┘
        │                      │
        └──────────┬───────────┘
                   ▼
           MemoryManager
         (unified access)
```

- **EMA α=0.5**: Mastery updates via exponential moving average
- **Keyword recall**: Experience search via token + substring matching
- **Vector-ready**: API designed for future ChromaDB replacement

---

## Data Flow

```
Student NL
    │
    ▼
ProfileAgent (rule-mode, 6-dim extraction)
    │
    ▼
StudentMemory (persist profile + mastery_map)
    │
    ▼
PlannerAgent (auto-detect curriculum → personalized nodes)
    │
    ▼
ResourceRecommendationAgent (7 resource types, explainable)
    │
    ▼
AgentEvaluator (4-dim: correctness/personalization/explainability/efficiency)
    │
    ▼
ImprovementLoop (low-score detection → reflection → strategy)
    │
    ▼
Dashboard V2 (6 panels, demo + runtime modes)
```

All events flow through **EventBus** (singleton) → **AgentTraceCollector** (persisted JSON).

---

## Evaluation Pipeline

| Dimension | Weight | Method |
|:----------|:------:|:-------|
| Correctness | 0.35 | Output structure + field completeness |
| Personalization | 0.30 | Memory integration check |
| Explainability | 0.20 | Reason/evidence presence |
| Efficiency | 0.15 | Step count + redundancy |

---

## Dashboard V2 — 6 Panels

| Panel | Data Source | Demo Content |
|:------|:------------|:-------------|
| System Overview | EventBus + TraceCollector + MemoryManager | 9 agents, 42 traces, 12 lessons |
| Student Intelligence | StudentMemoryStore | 6-dim profile, mastery heatmap |
| Execution Timeline | AgentTraceCollector | 12 events, reasoning_type + latency |
| Decision Explainability | DecisionExplainer | 8 decisions, avg confidence 89% |
| Agent Evaluation | AgentEvaluator | 4 agents, 4 dimensions each |
| Self Improvement | ImprovementLoop + ExperienceMemory | Failure → Reflection → Strategy |

---

## Technical Stack

| Layer | Technology |
|:------|:-----------|
| Agent Runtime | Python 3.11+ |
| Dashboard | Streamlit |
| Event System | AgentEventBus (singleton) |
| Trace Storage | JSON (TraceCollector) |
| Memory Storage | JSON (StudentMemory + ExperienceMemory) |
| Testing | pytest (241 tests) |
| CI/CD | ~/Terence-Agent/ PR workflow |
