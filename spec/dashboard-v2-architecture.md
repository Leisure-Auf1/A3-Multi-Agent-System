# Dashboard V2 — Architecture Proposal

> Design Phase — 2026-07-13
> Status: **Design Complete → Implementation**

---

## 1. Design Goals

打造 **比赛展示版 Demo** — 不只是加指标，而是:
- 6 个可独立展示的区域，每个区域讲述一个系统维度的故事
- 纯展示层，不修改 `src/core` 闭环
- Demo 模式: 零数据时也能展示完整功能
- app.py 只负责区域选择和页面组合

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────┐
│  app.py (Future: page composition only)             │
│  ┌───────────────┐ ┌───────────────┐ ┌────────────┐ │
│  │ System        │ │ Student       │ │ Agent      │ │
│  │ Overview      │ │ Intelligence  │ │ Execution  │ │
│  │               │ │ Dashboard     │ │ Timeline   │ │
│  └───────────────┘ └───────────────┘ └────────────┘ │
│  ┌───────────────┐ ┌───────────────┐ ┌────────────┐ │
│  │ Decision      │ │ Agent         │ │ Self       │ │
│  │ Explainability│ │ Evaluation    │ │ Improvement│ │
│  │ Panel         │ │ Dashboard     │ │ Timeline   │ │
│  └───────────────┘ └───────────────┘ └────────────┘ │
├─────────────────────────────────────────────────────┤
│  web/dashboard/components.py   ← Streamlit render   │
│  web/dashboard/data_providers.py ← Transform layer │
├─────────────────────────────────────────────────────┤
│  src/ (UNCHANGED)                                   │
│  ├── core/agent_trace.py       AgentTraceCollector │
│  ├── core/decision_explainer.py DecisionExplainer  │
│  ├── evaluation/agent_evaluator.py AgentEvaluator  │
│  ├── core/improvement_loop.py   ImprovementLoop    │
│  ├── core/meta_reflector.py     MetaReflector      │
│  ├── memory/student_memory.py   StudentMemoryStore │
│  └── memory/experience_memory.py ExperienceMemory  │
└─────────────────────────────────────────────────────┘
```

### Layer Responsibility

| Layer | Module | Responsibility |
|:------|:-------|:---------------|
| **Rendering** | `components.py` | Pure Streamlit UI. Takes typed data dicts, renders. Zero business logic. |
| **Transform** | `data_providers.py` | Queries src/ layers, transforms to dashboard-ready data structures. All the "wiring". |
| **Core** | `src/` | **Unchanged**. Business logic & storage. |

### Data Contract

Every component receives a single typed dict:

```python
# System Overview
SystemOverviewData = {
    "agents": [{"name": str, "status": str, "trace_count": int, "avg_latency": float}],
    "memory": {"student_count": int, "experience_count": int, "trace_count": int},
    "evaluation": {"total_evaluations": int, "avg_score": float},
    "topology": {"total_agents": int, "active_agents": int}
}

# Student Intelligence
StudentIntelligenceData = {
    "profile": {"knowledge_base": str, "cognitive_style": str, ...},
    "mastery_map": {str: float},
    "weak_points": [{"concept": str, "occurrence_count": int}],
    "learning_preferences": {"preferred_style": str, "avg_pace": str, ...},
    "learning_summary": {...},
    "interaction_count": int,
    "avg_score": float
}

# Execution Timeline
TimelineData = {
    "events": [{"timestamp": str, "agent": str, "action": str, "reasoning_type": str, "latency_ms": float, "status": str}],
    "stats": {"total": int, "by_agent": {str: int}, "avg_latency": float}
}

# Decision Explainability
ExplainabilityData = {
    "explanations": [{"agent": str, "action": str, "decision": str, "reason": str, "confidence": float, "evidence": [str]}],
    "total_decisions": int,
    "avg_confidence": float
}

# Agent Evaluation
EvaluationData = {
    "agents": [{"name": str, "correctness": float, "personalization": float, "explainability": float, "efficiency": float, "overall": float, "suggestions": [str]}],
    "avg_overall": float,
    "total_evaluations": int
}

# Self Improvement
ImprovementData = {
    "timeline": [{"stage": str, "content": str, "agent": str, "severity": str}],
    "pending_suggestions": int,
    "experience_count": int
}
```

### Demo Mode

When no real session data exists, every data provider returns **seed demo data** — showcase-ready synthetic data that demonstrates all 6 panels working.

```python
def get_demo_mode() -> DashboardDemo:
    """Return a fully populated demo for all 6 panels."""
```

---

## 3. File Change List

```
NEW  web/dashboard/__init__.py           # Package exports
NEW  web/dashboard/data_providers.py     # Data access/transformation layer (~300 lines)
NEW  web/dashboard/components.py         # 6 Streamlit rendering components (~400 lines)
NEW  spec/dashboard-v2-architecture.md   # This document
```

**Protected files (NOT modified):**
- `src/core/*` — All core modules unchanged
- `src/evaluation/*` — Evaluation engine unchanged
- `src/memory/*` — Memory layer unchanged
- `src/agents/*` — Agents unchanged
- `web/app.py` — Existing app unchanged (V1 preserved)
- `tests/*` — All existing tests unchanged

**Future (not in this phase):**
- `web/app_v2.py` — V2 app that composes the 6 panels (after review)

---

## 4. Implementation Plan

### Phase 1: Data Providers (`data_providers.py`)

| Step | Task | Data Source | Output Type |
|:-----|:-----|:------------|:------------|
| 1.1 | `get_system_overview()` | EventBus + TraceCollector + MemoryManager + Evaluator | `SystemOverviewData` |
| 1.2 | `get_student_intelligence(student_id)` | StudentMemoryStore.get_learning_summary() | `StudentIntelligenceData` |
| 1.3 | `get_execution_timeline(session_id)` | AgentTraceCollector.query() | `TimelineData` |
| 1.4 | `get_explainability_data(profile, plan, recommendations)` | DecisionExplainer.* | `ExplainabilityData` |
| 1.5 | `get_evaluation_data(evaluator)` | AgentEvaluator.get_summary() | `EvaluationData` |
| 1.6 | `get_improvement_timeline(loop, experience)` | ImprovementLoop + ExperienceMemory | `ImprovementData` |
| 1.7 | `DashboardDemo.get_all()` | Synthetic seed data | Dict of all 6 |

### Phase 2: Rendering Components (`components.py`)

| Step | Component | Renders |
|:-----|:----------|:--------|
| 2.1 | `render_system_overview(data)` | Topology stats, agent table, memory/EVAL/trace status cards |
| 2.2 | `render_student_intelligence(data)` | 6-dim radar via 6-column metrics, mastery heatmap, weak_points table |
| 2.3 | `render_execution_timeline(data)` | Sortable table: timestamp/agent/action/reasoning/latency/status |
| 2.4 | `render_explainability_panel(data)` | Card per decision: decision, evidence list, confidence bar, reason |
| 2.5 | `render_evaluation_dashboard(data)` | Per-agent 4-bar scores + overall, suggestions table |
| 2.6 | `render_improvement_timeline(data)` | Vertical flow: failure→evaluation→reflection→experience→strategy |

### Phase 3: Export & Verify

| Step | Task |
|:-----|:-----|
| 3.1 | `__init__.py` with clean exports |
| 3.2 | Verify `import web.dashboard` works without app.py |
| 3.3 | Run full test suite: `python -m pytest tests/ -q` |
| 3.4 | Write checkpoint |

---

## 5. Demo Data Strategy

Each panel's demo data is crafted to tell a coherent story:

**System Overview**: 7 agents (Profile, Planner, Resource, Content, Review, UserSim, Evaluator), 3 active, 42 traces, 5 students, 12 experience records, avg eval 0.82

**Student Intelligence**: Demo student "demo_student" with junior_dev profile, visual learning style, 3 weak points, 12 interactions, avg score 7.8

**Execution Timeline**: 12 trace events across 3 agents, mixed reasoning types (rule/llm/heuristic/memory/hybrid), latencies 5-340ms, 1 error dramatized

**Decision Explainability**: 8 decisions — 6 from ProfileAgent (dimension detection) + 2 from PlannerAgent (skip closure node, boost decorator node)

**Agent Evaluation**: 4 agents scored (Profile 0.88, Planner 0.82, Resource 0.78 simulator, Content 0.72), with suggestions for low scorers

**Self Improvement**: 5-stage timeline showing a failure→evaluation→reflection→experience→strategy chain for PlannerAgent decorator weakness
