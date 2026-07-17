# Runtime Engine

> **Phase 4.8** | Core state machine driving agent pipelines.

## Design Goal

Provide a deterministic state machine that executes agent pipelines
with hooks for observation, policy decisions, and recovery — all
without the agents knowing about the runtime.

## Core API

```python
from src.runtime import RuntimeEngine, RuntimeContext, AgentState, TransitionTable

# Minimal engine
engine = RuntimeEngine(session_id="demo")

# Register state handlers
engine.register_handler(AgentState.PROFILE, my_profile_handler)

# Custom transition table
table = TransitionTable(custom={
    AgentState.INIT: AgentState.PROFILE,
    AgentState.PROFILE: AgentState.DONE,
})
engine._table = table

# Execute
ctx = engine.run()
print(engine._checkpoint.timeline())
```

## Key Classes

| Class | File | Purpose |
|:------|:-----|:--------|
| `RuntimeEngine` | `runtime.py` | State machine executor |
| `RuntimeContext` | `runtime.py` | Mutable context passed to handlers |
| `AgentState` | `state.py` | Enum of pipeline states |
| `StateTransition` | `transition.py` | Record of a state change |
| `TransitionTable` | `transition.py` | Maps state → next state |
| `RuntimeCheckpoint` | `checkpoint.py` | Transition trace storage |
| `RuntimeHook` | `hooks.py` | Lifecycle callback base class |
| `CompositeHook` | `hooks.py` | Groups multiple hooks |
| `RuntimeEvent` | `events.py` | Emitted event |
| `RuntimeEventBus` | `events.py` | Pub/sub event bus |

## Handler Signature

```python
def my_handler(ctx: RuntimeContext) -> None:
    """Modify ctx in-place to produce pipeline outputs."""
    ctx.profile = {"knowledge_base": "beginner"}
    ctx.evaluation = {"score": 85}
```

## Advanced: Policy + Recovery

```python
from src.runtime import RuntimePolicyEngine
from src.runtime.recovery import RecoveryManager

engine = RuntimeEngine(
    session_id="demo",
    policy_engine=RuntimePolicyEngine(),
    recovery_manager=RecoveryManager(),
)
```

## Advanced: Hooks

```python
from src.runtime import RuntimeHook

class MyHook(RuntimeHook):
    def after_transition(self, engine, from_state, to_state, ctx, transition):
        print(f"{from_state.name} → {to_state.name}")

engine.add_hook(MyHook())
```

## Limitations

- State machine is linear by default; complex DAGs need custom transition tables
- `MAX_TRANSITIONS = 20` safety limit — long-running loops need adjustment
- Handlers are synchronous — no native async support (yet)
