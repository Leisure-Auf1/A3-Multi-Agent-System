# Agent Lifecycle & Session Management

> **Phase 5.5** | Agent OS-style lifecycle tracking + session records.

## Design Goal

Track individual agent states during execution — which agents are running,
which have failed, which are recovering. Provide a complete execution record
for dashboard display.

## Lifecycle States

```
CREATED → READY → RUNNING → (READY | FAILED → RECOVERING → READY | TERMINATED)
                           ↑_____________________________↓
```

| State | Meaning |
|:------|:--------|
| `CREATED` | Agent object instantiated |
| `READY` | Registered, waiting for execution |
| `RUNNING` | Executing its handler |
| `WAITING` | Paused (external dependency) |
| `FAILED` | Handler raised exception |
| `RECOVERING` | Recovery in progress |
| `TERMINATED` | Finished (success or final failure) |

## Usage

```python
from src.runtime.lifecycle import LifecycleManager, AgentLifecycle

lm = LifecycleManager()

# Hook into engine — zero engine modification
engine = RuntimeEngine(session_id="demo")
engine.add_hook(lm)
engine.run()

# Query
print(lm.agent_states)     # {"profile": "terminated", "plan": "terminated", ...}
print(lm.agent_summary())  # {total_agents, states, errors, recoveries}

# Session export
print(lm.session.timeline())   # ["PROFILE", "PLAN", "EXECUTE"]
print(lm.session.to_dict())     # full JSON export for dashboard
```

## Recovery Bridge

```python
# When recovery happens, update lifecycle
lm.mark_error("profile", "transient timeout")
lm.mark_recovery("profile")      # FAILED → RECOVERING
lm.mark_recovered("profile")     # RECOVERING → READY
```

## RuntimeSession

```python
session = lm.session
print(session.session_id)     # unique ID
print(session.final_status)   # "completed" | "error"
print(session.total_duration_ms)
print(session.timeline())     # ordered state list
print(session.error_count())
print(session.to_summary())   # lightweight dashboard export
```

## Limitations

- Lifecycle tracking is per-agent-name, not per-agent-instance
- Session data is in-memory only (no persistence yet)
- All 8 non-terminal states are auto-registered
