# A3 — Multi-Agent Personalized Learning System

> **Research Prototype v3.0** | 12 Agents + Workflow Orchestrator | 283 Tests | 15k+ LOC
>
> *"Students describe what they want to learn. A team of AI agents does the rest."*

---

## 🔗 Project Navigation

| Role | Repository | Description |
|:-----|:-----------|:------------|
| 🏠 Portfolio Hub | [Terence-Agent](https://github.com/Leisure-Auf1/Terence-Agent) | AI Agent Research Portfolio |
| 🏗️ Next Evolution | [Veritas-Core](https://github.com/Leisure-Auf1/Veritas-Core) | Production-grade Agent Infrastructure |

```
A3-Multi-Agent-System
        │
        │  Research Prototype
        │  Multi-agent experimentation
        │  Prototype validation
        ↓
Veritas-Core
```

**A3 is the research foundation. Veritas-Core is the architectural evolution.**

---

## What is A3?

A3 is a research prototype exploring **multi-agent collaboration for personalized learning**. Instead of using a single LLM, A3 deploys a **team of 12 specialized agents** — each with a focused role — collaborating through shared memory and an EventBus.

A3 focuses on:
- Multi-agent experimentation
- Agent collaboration patterns
- Event-driven architecture
- Prototype validation

The architectural ideas discovered here continue into [Veritas-Core](https://github.com/Leisure-Auf1/Veritas-Core).

---

## Architecture

```
Student Input (Natural Language)
         │
         ▼
┌─────────────────────────────────────────────┐
│          Multi-Agent Runtime                 │
│                                              │
│  ProfileAgent → PlannerAgent → ResourceRec  │
│  ResourceGenAgent → ContentAgent            │
│       │              │              │        │
│       └──────────────┼──────────────┘        │
│                      ▼                       │
│              AgentEvaluator                  │
│                      │                       │
│          ┌───────────┴───────────┐           │
│          ▼                       ▼           │
│   MetaReflector          ImprovementLoop     │
├──────────────────────────────────────────────┤
│  Infrastructure: EventBus | Memory | Trace   │
│  LLMProvider | ReviewGate | DecisionExplainer│
└──────────────────────────────────────────────┘
         │
         ▼
    Dashboard (6-panel Streamlit)
```

---

## Core Features

### Multi-Agent Collaboration
12 specialized agents with single responsibilities, communicating through a Singleton EventBus.

### Student Profiling
6-dimension profiles extracted from natural language via rule engine (70% confidence) and LLM (85% confidence).

### Personalized Learning Paths
Course auto-detection + pace/cognitive/mastery adjustments produce different paths for different students.

### Resource Generation (6 types)
- 📄 Course Notes (Markdown)
- 🧠 Mind Maps (Mermaid)
- ✏️ Exercises (3 difficulty levels)
- 💻 Code Labs (runnable Python)
- 🎬 Video Scripts (scene-by-scene)
- 📖 Extended Reading

### Self-Improvement Loop
Evaluation → MetaReflector → ExperienceMemory → ImprovementLoop → Strategy injection

### Content Safety (3-Gate ReviewGate)
Gate 1: AST static syntax check → Gate 2: Pytest dynamic validation → Gate 3: LLM-as-Judge quality scoring

### Explainable Decisions
DecisionExplainer produces evidence chains, confidence scores, and reasoning for every agent action.

---

## Quick Start

```bash
git clone https://github.com/Leisure-Auf1/A3-Multi-Agent-System.git
cd A3-Multi-Agent-System

# Install
pip install -r web/requirements.txt

# Run tests
python -m pytest tests/ -q

# Launch Dashboard
streamlit run web/app_v3.py
```

---

## Knowledge Base

```
knowledge_base/artificial_intelligence_multi_agent_course/
├── course_intro.md
├── chapters/           # 6 chapters (AI intro, LLM, Prompt, RAG, Agent, Evaluation)
├── resources.json      # External references
└── exercises.json      # 24 exercises across 6 chapters
```

---

## Metrics

| Metric | Value |
|:-------|:------|
| Agents | 12 |
| Source Lines | 13,048 Python |
| Tests | 283/287 (98.6%) |
| Resource Types | 6 |
| Profile Dimensions | 6 |
| Knowledge Concepts | 46 |
| Experience Lessons | 5→13+ self-growing |
| Dashboard Panels | 6 |

---

## Complete Agent Workflow

A3 demonstrates: **"From user intent to personalized execution through multi-agent collaboration."**

```bash
python examples/full_pipeline_demo.py
```

### Pipeline Architecture

```
User Goal ("Learn Python Network Programming")
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│                  A3Workflow Orchestrator                 │
│                                                         │
│  ① ProfileAgent    — Extract learner profile            │
│        │                                                │
│        ▼                                                │
│  ② PlannerAgent    — Generate personalized learning path│
│        │                                                │
│        ▼                                                │
│  ③ ResourceAgent   — Recommend matching resources       │
│        │                                                │
│        ▼                                                │
│  ④ ReviewGate      — Evaluate quality & relevance       │
│        │                                                │
│        ▼                                                │
│  ⑤ ReflectionAgent — Analyze success & improvements     │
│        │                                                │
│        ▼                                                │
│  ⑥ Memory          — Save learning experience           │
├─────────────────────────────────────────────────────────┤
│  Infrastructure: EventBus | TraceCollector | MemoryManager│
└─────────────────────────────────────────────────────────┘
    │
    ▼
 WorkflowResult { profile, plan, resources, reflection }
```

### What happens at each step

| Step | Agent | Input | Output |
|:-----|:------|:------|:-------|
| 1 | **ProfileAgent** | Natural language goal | 6-dim DynamicProfile |
| 2 | **PlannerAgent** | Profile + course KB | LearningPlan (nodes + strategies) |
| 3 | **ResourceAgent** | Profile + goal + knowledge gaps | Personalized resources (5 types) |
| 4 | **ReviewGate** | Plan + resources | Quality score + issues |
| 5 | **ReflectionAgent** | Execution results | Success evaluation + improvements |
| 6 | **Memory** | All outputs | Persistent student memory |

### Running the demo

```
================================
A3 Multi-Agent Demo
================================

User Goal:
  Learn Python Network Programming

[ProfileAgent]
  Analyzing learner profile...

[PlannerAgent]
  Generating personalized learning path...

[ResourceAgent]
  Finding matching resources...

[ReviewAgent]
  Evaluating quality...

[ReflectionAgent]
  Post-execution reflection...

[Memory]
  Saving learning experience...

================================
Completed — Score: 95/100 ✅
================================
```

### Key innovations demonstrated

- **Agent communication through EventBus** — Every agent action is traced and visible
- **Shared memory usage** — Profile history, mastery tracking, experience recall
- **Intermediate results** — Plan nodes, resource recommendations, quality scores
- **Final reflection** — Post-execution analysis of what worked and what to improve

New in v3.0:
- `src/agents/resource_agent.py` — Simplified resource recommendation for pipeline demo
- `src/agents/reflection_agent.py` — Post-execution success/improvement analysis
- `src/workflow/` — A3Workflow orchestrator with full pipeline coordination
- `src/core/event_trace.py` — Enhanced TraceCollector with timeline rendering
- `examples/full_pipeline_demo.py` — Runnable demo showing the complete collaboration
- `tests/integration/test_full_pipeline.py` — 42 integration tests (pipeline + EventBus + memory)

---

## Project Evolution

```
A3-Multi-Agent-System
        │
        │  Research Foundation
        │  Multi-agent experimentation
        │  Prototype validation
        ↓
Veritas-Core
        │
        │  Engineering Evolution
        │  Production-grade infrastructure
        │  Runtime + Trust + Memory
```

A3 is the **research prototype** where we explored multi-agent learning concepts. [Veritas-Core](https://github.com/Leisure-Auf1/Veritas-Core) is the **architectural evolution** that introduces:

- Agent Runtime State Machine
- RAG-enhanced knowledge retrieval
- 3-tier memory (Redis/PostgreSQL/ChromaDB)
- Trust Layer (memory validation, permissions, injection defense)
- Agent+Tool architecture

**A3 and Veritas-Core are independent repositories — not a rename, but an evolution.**

---

## License

MIT
