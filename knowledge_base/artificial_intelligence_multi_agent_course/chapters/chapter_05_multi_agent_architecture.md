# Chapter 5: Multi-Agent Architecture

> **Learning Objective**: Design and implement multi-agent systems with role specialization, communication protocols, and shared memory.

---

## 5.1 Why Multi-Agent?

### The Monolithic LLM Problem

A single LLM trying to do everything faces:

- **Attention Dilution**: Long prompts mean important instructions get buried
- **Role Confusion**: One model switching between roles loses coherence
- **No Accountability**: Which part of the system failed? Hard to debug
- **No Specialization**: Jack of all trades, master of none

### The Multi-Agent Solution

```
Monolithic:                    Multi-Agent:
┌──────────────┐          ┌────┐ ┌────┐ ┌────┐ ┌────┐
│  One model   │          │ A1 │ │ A2 │ │ A3 │ │ A4 │
│  does all:   │    vs    └──┬─┘ └──┬─┘ └──┬─┘ └──┬─┘
│  profile     │            │      │      │      │
│  plan        │       ┌────┴──────┴──────┴──────┴────┐
│  generate    │       │  EventBus + Shared Memory     │
│  evaluate    │       └──────────────────────────────┘
└──────────────┘
```

---

## 5.2 Core Design Patterns

### Pattern 1: Pipeline (Sequential)

Agents execute in fixed order. Each agent's output feeds the next.

```
ProfileAgent → PlannerAgent → ContentAgent → ReviewGate → UserSim
```

**Pros**: Predictable, easy to debug, low communication overhead
**Cons**: No parallelism, single point of failure
**Best for**: Well-defined workflows with clear dependencies

### Pattern 2: Router (Conditional)

A central router dispatches tasks to specialized agents based on input type.

```
                    ┌──────────┐
                    │  Router  │
                    └────┬─────┘
            ┌────────────┼────────────┐
            ▼            ▼            ▼
       ┌────────┐  ┌────────┐  ┌────────┐
       │Agent A │  │Agent B │  │Agent C │
       └────────┘  └────────┘  └────────┘
```

**A3 implementation**: `AgentRouter` dispatches frontend agents to Xunfei Spark, backend agents to DeepSeek.

### Pattern 3: Blackboard (Shared Workspace)

Agents read from and write to a shared memory workspace.

```
┌─────────────────────────────────────┐
│           Blackboard                │
│  ┌─────────────────────────────┐   │
│  │    Shared Knowledge Base    │   │
│  └─────────────────────────────┘   │
└───┬──────────┬──────────┬──────────┘
    │          │          │
┌───┴───┐ ┌───┴───┐ ┌───┴───┐
│Agent 1│ │Agent 2│ │Agent 3│
└───────┘ └───────┘ └───────┘
```

**A3 implementation**: `MemoryManager` provides StudentMemory and ExperienceMemory for all agents.

### Pattern 4: Debate (Adversarial)

Multiple agents generate competing outputs; an arbiter selects the best.

```
Agent A ──→ Candidate Solution A ──┐
                                    ├──→ Arbiter ──→ Final Solution
Agent B ──→ Candidate Solution B ──┘
```

**A3 implementation**: `ReviewGate` evaluates ContentAgent output; `UserSimulationAgent` provides adversarial testing.

---

## 5.3 Inter-Agent Communication

### Message Passing

| Method | Format | Latency | Use Case |
|:-------|:-------|:--------|:---------|
| **Direct Call** | Function call | Synchronous | Pipeline stages |
| **Event Bus** | Pub/sub events | Async | Status updates, tracing |
| **Shared Memory** | Read/write DB | Async | Persistent state |
| **Message Queue** | FIFO queue | Async | Decoupled agents |

### A3 Event System

```python
# Publishing an event
from src.core.event_bus import AgentEventBus

bus = AgentEventBus.get_instance()
bus.emit(
    agent="ProfileAgent",
    action="profile_extraction",
    input_summary="Student: Xiao Lin, network engineering",
    output_summary="visual_dominant, fast_track",
    status="success",
    duration_ms=120
)

# Subscribing to events
from src.core.agent_trace import AgentTraceCollector

collector = AgentTraceCollector()
collector.sync_from_bus()  # Pulls all events into trace
```

---

## 5.4 Agent Role Design

### Principles of Good Agent Design

1. **Single Responsibility**: Each agent does ONE thing well
2. **Clear Contract**: Defined input/output schema (use dataclasses)
3. **Observability**: Every action emits events and traces
4. **Graceful Degradation**: Failures don't crash the system
5. **Explainability**: Every decision has a documented reason

### A3 Agent Roles

| Agent | Input | Output | Reasoning Type |
|:------|:------|:-------|:---------------|
| **ProfileAgent** | Natural language | DynamicProfile (6-dim) | Rule engine |
| **PlannerAgent** | Profile + course | LearningPlan (nodes) | Rule + curriculum |
| **ResourceRecAgent** | Memory + profile | ResourcePlan (7 types) | Mastery-based heuristics |
| **ContentAgent** | Plan + profile | 5-asset content | LLM generation |
| **AgentEvaluator** | Agent output | 4-dim score | RuleJudge |
| **MetaReflector** | Failure context | Root cause analysis | Heuristic |
| **ImprovementLoop** | Low scores | Strategy suggestions | Rule-based mapping |

---

## 5.5 Memory Architecture

### Two-Tier Memory System

```
┌───────────────────────────────────────┐
│         MemoryManager                  │
│                                        │
│  ┌─────────────┐  ┌─────────────┐     │
│  │  Student    │  │ Experience  │     │
│  │  Memory     │  │  Memory     │     │
│  │             │  │             │     │
│  │ • Profile   │  │ • Failures  │     │
│  │ • Mastery   │  │ • Solutions │     │
│  │ • History   │  │ • Success%  │     │
│  │ • Feedback  │  │ • Keywords  │     │
│  └─────────────┘  └─────────────┘     │
│                                        │
│  Storage: JSON files (Vector-ready)    │
└───────────────────────────────────────┘
```

### Mastery Tracking (EMA α=0.5)

```python
# Exponential Moving Average for mastery
new_mastery = old_mastery * 0.5 + latest_score * 0.5

# Strengths: mastery ≥ 0.7 → skip in plan
# Weaknesses: mastery ≤ 0.3 → add remedial nodes
```

---

## 5.6 A3 Complete Pipeline

```
Student Input: "I want to learn Multi-Agent AI"
        │
        ▼
┌──────────────────┐
│ Conversation     │  Multi-turn profile building
│ ProfileAgent     │
└────────┬─────────┘
         ▼
┌──────────────────┐
│ ProfileAgent     │  6-dim: visual_dominant, fast_track, ...
└────────┬─────────┘
         ▼
┌──────────────────┐
│ PlannerAgent     │  Auto-detect: "multi_agent_ai" course
│                  │  → 16-node learning path
└────────┬─────────┘
         ▼
┌──────────────────┐
│ ResourceRecAgent │  Mastery-based resource selection
│                  │  → 6 resources with reasons
└────────┬─────────┘
         ▼
┌──────────────────┐
│ ContentAgent     │  5-asset generation (lecture/mindmap/quiz/...)
└────────┬─────────┘
         ▼
┌──────────────────┐
│ ReviewGate       │  AST + Pytest + Judge → score
└────────┬─────────┘
         ▼
┌──────────────────┐
│ UserSimulation   │  Simulate student learning → quality score
└────────┬─────────┘
    score < 85?
    YES ────→ FeedbackLoop → MetaReflector → Retry
    NO ─────→ Commit output
         ▼
┌──────────────────┐
│ AgentEvaluator   │  4-dim evaluation for all agents
└────────┬─────────┘
         ▼
┌──────────────────┐
│ ImprovementLoop  │  Low-score agents → strategy suggestions
└──────────────────┘
```

---

## Chapter 5 Exercises

1. Design a 3-agent system for code review: which patterns would you use?
2. Compare pipeline vs. blackboard — when would you choose each?
3. Implement a minimal EventBus with emit/subscribe in 50 lines of Python
4. Analyze: what happens in A3 if the PlannerAgent fails? How should it degrade?

---

## Key Terms

- **Multi-Agent System** · **Pipeline Pattern** · **Router Pattern**
- **Blackboard Pattern** · **Debate Pattern** · **EventBus**
- **Shared Memory** · **Agent Role** · **Single Responsibility**
- **EMA Mastery** · **Graceful Degradation** · **Explainability**

---

## Further Reading

- Wooldridge, *An Introduction to MultiAgent Systems* (2nd Edition)
- Shoham & Leyton-Brown, *Multiagent Systems: Algorithmic, Game-Theoretic, and Logical Foundations*
- Park et al., "Generative Agents: Interactive Simulacra of Human Behavior" (2023)
- Li et al., "CAMEL: Communicative Agents for 'Mind' Exploration" (2023)
