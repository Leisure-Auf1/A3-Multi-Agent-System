# Phase 13 — Streaming / Event Demo Plan

> Competition-friendly generation progress visualization
> Date: 2026-07-13 | A3 v2.8 → v2.9

---

## 1. Goal

**Show the agents working in real-time** during the 5-minute demo. Not fake animation — actual pipeline progress from the EventBus.

---

## 2. Analysis: Real Streaming vs. Event-Driven Visualization

### 2.1 What "Real Streaming" Would Require

- SSE (Server-Sent Events) from Xunfei Spark API
- Token-level event emission during `generate()`
- Real-time token rendering in Streamlit
- WebSocket or polling loop for UI updates

**Assessment:** Heavy engineering. Not needed for competition. The 5-minute demo shows the pipeline flow — not token-by-token generation.

### 2.2 What "Event-Driven Visualization" Provides

- Pipeline step events from EventBus (already emitted)
- Progress bar: "ProfileAgent → PlannerAgent → ResourceGenAgent → Evaluator"
- Status indicators per step
- Latency metrics per step
- **Zero new infrastructure** — everything already in EventBus

**Assessment:** Lightweight, honest, impressive. Perfect for competition.

### 2.3 Recommendation

> **Prefer event-driven visualization over fake animation.**

The EventBus already captures every agent action. The TraceCollector persists them. All we need is a progress display that reads from these existing sources.

---

## 3. Pipeline Progress Visualization

### 3.1 Design

```
┌─────────────────────────────────────────────────┐
│ 🔄 Generation Progress                           │
│                                                  │
│  ✅ Student Input Received          (0ms)        │
│  ✅ ProfileAgent analyzing...       (120ms)      │
│  ✅ PlannerAgent generating path... (45ms)       │
│  ✅ ResourceAgent creating materials (85ms)     │
│  ✅ EvaluationAgent checking quality (60ms)     │
│  ✅ Completed                       (310ms total)│
│                                                  │
│  ████████████████████████████████ 100%           │
└─────────────────────────────────────────────────┘
```

### 3.2 Data Source

The EventBus timeline already contains all these events:

```python
# Running pipeline emits these events automatically:
EventBus.emit(agent="ProfileAgent", action="profile_extraction", ...)
EventBus.emit(agent="PlannerAgent", action="plan_generation", ...)
EventBus.emit(agent="ResourceGenerationAgent", action="generate_all", ...)
EventBus.emit(agent="AgentEvaluator", action="evaluate", ...)
```

To display progress:

```python
# In web/chat_demo.py or web/v1/components.py
def render_pipeline_progress(events: list, st) -> None:
    """Show pipeline progress from EventBus timeline."""
    st.header("🔄 Generation Progress")

    pipeline_steps = [
        "ProfileAgent",
        "PlannerAgent",
        "ResourceGenerationAgent",
        "AgentEvaluator",
    ]

    completed = 0
    for step in pipeline_steps:
        matching = [e for e in events if e.agent == step and e.status == "success"]
        if matching:
            st.markdown(f"✅ **{step}** — {matching[-1].output_summary[:80]}")
            completed += 1
        else:
            st.markdown(f"⏳ {step} — waiting...")

    # Progress bar
    pct = completed / len(pipeline_steps)
    st.progress(pct, text=f"{completed}/{len(pipeline_steps)} steps complete")

    # Total latency
    if completed == len(pipeline_steps):
        total_ms = sum(e.duration_ms for e in events if e.agent in pipeline_steps)
        st.success(f"✅ Completed in {total_ms:.0f}ms")
```

---

## 4. Existing StreamingSimulator

### 4.1 Current State

`utils/streaming.py` has a complete `StreamingSimulator` with:
- Token-by-token streaming with configurable delays
- EventBus integration for streaming events
- `stream_with_events()` — emits per-token events

### 4.2 Competition Use

The streaming simulator is **ready but not integrated** into any dashboard. For competition, we can:

**Option A:** Integrate into Chat Demo for content generation display
- Value: Shows "AI generating content in real-time"
- Cost: ~30 lines of UI integration
- Risk: Low — simulator already tested

**Option B:** Keep as architectural demonstration
- Value: "We have streaming capability, here's the architecture"
- Cost: 0 lines (already documented)
- Risk: None

**Recommendation:** Option A for competition value, Option B as fallback.

---

## 5. Implementation Plan

### 5.1 Files Affected

| File | Change | Lines |
|:-----|:-------|:------|
| `web/v1/components.py` | Add `render_pipeline_progress()` | ~40 |
| `web/dashboard/components.py` | Add progress panel to V2 | ~30 |
| `web/chat_demo.py` | Optional: integrate StreamingSimulator | ~30 |
| `web/v1/pipeline.py` | Emit progress events during pipeline | ~10 |

**Maximum: ~110 lines.** All using existing EventBus infrastructure.

### 5.2 Implementation Priority

| Feature | Priority | Reason |
|:--------|:---------|:-------|
| Pipeline progress (EventBus) | A | High value, low cost, honest |
| StreamingSimulator integration | B | Nice but not essential |
| Token-level streaming display | C | Over-engineering for competition |

---

## 6. Competition Demo Flow with Progress

```
Judge watches screen:

[Pipeline Progress Bar: 0%]

Student types input... click "Run Pipeline"

[Pipeline Progress Bar: 20%]
✅ Student Input Received

[Pipeline Progress Bar: 40%]
✅ ProfileAgent — "6-dim profile extracted (llm mode)"

[Pipeline Progress Bar: 60%]
✅ PlannerAgent — "6 nodes, 180min path generated"

[Pipeline Progress Bar: 80%]
✅ ResourceAgent — "5 resource types created"

[Pipeline Progress Bar: 100%]
✅ EvaluationAgent — "4-dim scores: 0.78 overall"

Total: 310ms — all agents completed.

Talking point: "Every agent action is captured by our EventBus.
You can see exactly what happened, in what order, and how long it took.
This is observability built into the architecture, not bolted on after."
```

---

## 7. What We're NOT Building

| Not Building | Why Not |
|:-------------|:--------|
| Real SSE streaming from Spark | Spark API doesn't support it reliably yet |
| WebSocket real-time updates | Over-engineering for a 5-min demo |
| Fake "loading" animations | Dishonest — judges see through it |
| Token-by-token typewriter effect | Cool but distracting from multi-agent story |

The multi-agent collaboration story is **more important** than the streaming story. Show agents working together, not characters appearing one at a time.
