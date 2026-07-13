# A3 — Multi-Agent Personalized Learning System

> **Research Prototype v2.8** | 12 Agents | 241 Tests | 13k+ LOC
>
> *"Students describe what they want to learn. A team of AI agents does the rest."*

---

## What is A3?

A3 is a research prototype exploring **multi-agent collaboration for personalized learning**. Instead of using a single LLM, A3 deploys a **team of 12 specialized agents** — each with a focused role — collaborating through shared memory and an EventBus.

**This project is the foundation that inspired [Veritas-Core](../Veritas-Core/).**

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
cd projects/A3-Multi-Agent-System

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
| Tests | 241/245 (97.4%) |
| Resource Types | 6 |
| Profile Dimensions | 6 |
| Knowledge Concepts | 46 |
| Experience Lessons | 5→13+ self-growing |
| Dashboard Panels | 6 |

---

## Relationship to Veritas-Core

A3 is the **research prototype** where we explored multi-agent learning concepts. [Veritas-Core](../Veritas-Core/) is the **architectural evolution** that introduces:

- Agent Runtime State Machine
- RAG-enhanced knowledge retrieval
- 3-tier memory (Redis/PostgreSQL/ChromaDB)
- Trust Layer (memory validation, permissions, injection defense)
- Agent+Tool architecture

```
A3 (prototype) ──evolution──→ Veritas-Core (production architecture)
```

---

## License

MIT
