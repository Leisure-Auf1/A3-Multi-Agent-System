# Designing Multi-Agent Collaboration with EventBus and Workflow Isolation

**Series Part 2 of 6** · 2026-07

---

## The Communication Problem

When you have 12 agents that need to work together, the first question isn't "what does each agent do?" — it's "how do they talk to each other without creating a tangled mess?"

In a naive multi-agent system, Agent A directly calls Agent B, which calls Agent C, which calls back to Agent A. After three iterations, you have a dependency graph that looks like spaghetti and breaks every time you change one agent's interface.

A3-Agent uses two patterns to avoid this: **EventBus** for agent communication and **workflow isolation** for concurrent request safety.

---

## EventBus: Publish-Subscribe for Agents

The EventBus is a lightweight in-process publish-subscribe system. Agents don't call each other directly. Instead:

1. **Agents publish events** when they complete work
2. **Other agents subscribe** to events they care about
3. **The bus delivers** events to all subscribers

```python
# ProfileAgent publishes its result
event_bus.publish(Event(
    type="profile.completed",
    data={"student_id": "s1", "dimensions": {...}},
    agent="ProfileAgent"
))

# PlannerAgent subscribes to profile completion
@event_bus.subscribe("profile.completed")
def on_profile_completed(event):
    plan = planner.generate_plan(event.data)
    event_bus.publish(Event(
        type="plan.completed",
        data=plan,
        agent="PlannerAgent"
    ))
```

### Why This Matters

**Decoupled development**: ProfileAgent doesn't know PlannerAgent exists. It just publishes its output. PlannerAgent doesn't know who produced the profile — it just reacts to the event. This means agents can be developed, tested, and replaced independently.

**Testable in isolation**: You can test PlannerAgent by publishing a fake `profile.completed` event — no need to run ProfileAgent or set up an LLM.

**Traceable execution**: Every event passes through a `TraceCollector` that records what happened, when, and by which agent. This powers the execution timeline and explainability dashboard.

**Extensible**: Adding a new agent means subscribing to existing events and publishing new ones. No existing agent code changes.

### Event Types in A3-Agent

| Event | Publisher | Subscribers |
|:------|:----------|:------------|
| `profile.completed` | ProfileAgent | PlannerAgent, TraceCollector |
| `plan.completed` | PlannerAgent | ResourceAgent, TraceCollector |
| `resources.generated` | ResourceAgent | TutorAgent, TraceCollector |
| `evaluation.completed` | EvaluationAgent | ReflectionAgent, TraceCollector |
| `reflection.completed` | ReflectionAgent | TraceCollector |

The `TraceCollector` subscribes to everything — it's the universal observer that enables the dashboard and explainability features.

---

## Workflow Isolation: The Concurrency Challenge

EventBus is a global singleton by default — convenient for single-user desktop usage, but dangerous for multi-user API servers. Two concurrent API requests sharing the same EventBus would see each other's events, cross-contaminating session data.

### The Solution: Per-Request EventBus Injection

A3-Agent uses a backward-compatible injection pattern:

```python
class A3Workflow:
    def __init__(self, bus: Optional[AgentEventBus] = None):
        self._bus = bus if bus is not None else AgentEventBus.get_instance()
        self._owns_bus = bus is not None  # True = per-request, False = global

    def run(self, session_id: str):
        if self._owns_bus:
            self._bus.clear()           # Per-request: just clear own instance
        else:
            AgentEventBus.reset_instance()  # Global: full reset (desktop/streamlit)
            self._bus = AgentEventBus.get_instance()
        self._bus.start_session(session_id)
```

**Desktop/Streamlit path**: No `bus` parameter → uses global singleton (backward compatible, zero refactoring).

**API path**: `bus=AgentEventBus()` → each request gets an isolated bus instance.

```python
# FastAPI dependency injection
def get_workflow() -> A3Workflow:
    return A3Workflow(
        llm_provider=provider,
        bus=AgentEventBus(),  # Independent per request
    )
```

This means 10 concurrent API requests each get their own EventBus — their agents publish and subscribe in complete isolation, with zero chance of cross-contamination.

---

## Agent Responsibility Boundaries

Clear boundaries prevent scope creep. Each agent has one job, defined by its output event type:

| Agent | Input Event | Output Event | LLM Required? |
|:------|:------------|:-------------|:-------------:|
| ProfileAgent | User input (text) | `profile.completed` | ✅ |
| PlannerAgent | `profile.completed` | `plan.completed` | ✅ |
| ResourceAgent | `plan.completed` | `resources.generated` | ❌ (rule-based) |
| TutorAgent | Chat message | SSE stream | ✅ |
| EvaluationAgent | Quiz submission | `evaluation.completed` | ✅ |
| ReflectionAgent | `evaluation.completed` | `reflection.completed` | ✅ |

### The "Frozen Core" Design Decision

After stabilizing the agent pipeline, three directories were permanently frozen:

```
src/agents/      — No modifications allowed
src/workflow/    — No modifications allowed
Veritas-Core     — External framework, version-pinned
```

This wasn't a limitation — it was a deliberate design choice. All subsequent development — user configuration, onboarding, packaging, documentation — happened in layers that interact with the frozen core through well-defined interfaces.

**Why freeze?** Because every modification to working agent code risks breaking the pipeline. In a system with 1154 tests, the fastest way to introduce regressions is to "just add one more field to the profile" or "tweak the planner prompt." Freezing the core forces developers to extend through composition rather than modification — a healthier pattern for long-lived projects.

---

## The Workflow Orchestrator

Above the individual agents sits `A3Workflow` — the orchestrator that sequences agent execution:

```python
class A3Workflow:
    def run(self, goal: str, session_id: str) -> WorkflowResult:
        # 1. Profile
        profile = self.profile_agent.analyze(goal)
        
        # 2. Plan (enhanced with RAG context)
        plan = self.planner_agent.create_plan(goal, profile)
        
        # 3. Resources
        resources = self.resource_agent.generate(plan)
        
        # 4. Evaluation
        evaluation = self.evaluation_agent.evaluate(plan, resources)
        
        # 5. Reflection
        reflection = self.reflection_agent.reflect(evaluation)
        
        return WorkflowResult(
            profile=profile,
            plan=plan,
            resources=resources,
            evaluation=evaluation,
            reflection=reflection,
            trace=self._bus.get_trace()
        )
```

The orchestrator is intentionally simple — it's a sequence, not a complex DAG. For a learning pipeline, sequential execution makes sense: you can't plan without a profile, you can't evaluate without resources. The simplicity makes the system debuggable: if output is wrong, you trace backward through the sequence to find which agent produced incorrect output.

---

## Key Takeaways

1. **EventBus decouples agents** — publish-subscribe beats direct calls for multi-agent systems
2. **Per-request isolation** prevents session cross-contamination in API deployments
3. **Frozen core** protects stable agent logic from feature-creep regressions
4. **Simple orchestrator** keeps the system debuggable — sequential beats complex DAGs for learning pipelines
5. **Clear boundaries** — one agent, one responsibility, one output event type

---

*Next: Part 3 — Memory & RAG: From Stateless Chatbots to Learning Systems*

*[A3-Agent on GitHub](https://github.com/Leisure-Auf1/A3-Multi-Agent-System) · 1154 tests · MIT License*
