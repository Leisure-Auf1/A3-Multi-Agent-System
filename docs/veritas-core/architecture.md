# Veritas-Core Architecture

> **Phase 6.1** | In-depth architecture of the Agent Runtime Framework.

## System Architecture

```
                    ┌──────────────────────┐
                    │    Application       │
                    │  (A3, Agents, etc.)  │
                    └──────────┬───────────┘
                               │ uses
                    ┌──────────▼───────────┐
                    │    Public SDK (6.0)   │
                    │  RuntimeClient.run()  │
                    └──────────┬───────────┘
                               │ delegates
                    ┌──────────▼───────────┐
                    │   RuntimeAdapter     │
                    │  (translates contract │
                    │   ↔ runtime internals)│
                    └──────────┬───────────┘
                               │ creates
              ┌────────────────┼────────────────┐
              │                │                │
    ┌─────────▼──────┐ ┌──────▼──────┐ ┌───────▼──────┐
    │  RuntimeEngine │ │  Policy     │ │  Recovery    │
    │  • StateMach   │ │  Engine     │ │  Manager     │
    │  • Transitions │ │  • Analyze  │ │  • Retry     │
    │  • Handlers    │ │  • Detect   │ │  • Rollback  │
    │  • Hooks       │ │  • Decide   │ │  • Fallback  │
    └────────┬───────┘ └──────┬──────┘ └──────┬───────┘
             │                │               │
    ┌────────▼────────────────▼───────────────▼───────┐
    │              Observability Layer                 │
    │  Events → Metrics → Observer → Snapshot         │
    │  Lifecycle → Session → Trace → Explainability   │
    └──────────────────────┬──────────────────────────┘
                           │
    ┌──────────────────────▼──────────────────────────┐
    │              Extension Layer                     │
    │  Plugins → Bridge → Registry → Manager          │
    │  Security → Gateway → Audit                     │
    │  Distributed → Nodes → Remote → Collect         │
    └─────────────────────────────────────────────────┘
```

## State Machine

```
INIT → PROFILE → PLAN → EXECUTE → EVALUATE → REFLECT
                                                │
                                    ┌───────────┤
                                    ▼           ▼
                              META_REFLECT  MEMORY_UPDATE
                                    │           │
                                    ▼           ▼
                                    └───── DONE ─────┘
```

| State | Handler | Output |
|:------|:--------|:-------|
| INIT | no-op | — |
| PROFILE | ProfileAgent | user profile |
| PLAN | PlannerAgent | learning plan |
| EXECUTE | ResourceAgent | resources |
| EVALUATE | EvaluationManager | score, issues |
| REFLECT | ReflectionAgent | success, improvements |
| META_REFLECT | MetaReflector | system-level diagnosis |
| MEMORY_UPDATE | MemoryManager | persisted session |
| DONE | — | terminal |

## Hook Lifecycle

```
engine.run()
  │
  ├─ hooks: on_run_start(engine, ctx)
  │
  ├─ for each transition:
  │   ├─ hooks: before_transition(engine, from, to, ctx)
  │   ├─ handler(ctx)           ← executes state logic
  │   ├─ hooks: after_transition(engine, from, to, ctx, transition)
  │   └─ on error: hooks: on_error(engine, state, ctx, error)
  │
  └─ hooks: on_run_end(engine, ctx, total_duration_ms)
```

## Recovery Flow

```
FailureDetector → FailureEvent
       ↓
PolicyEngine → RuntimeDecision (RETRY/REFLECT/TERMINATE)
       ↓
RecoveryManager.select_strategy(failure) → RecoveryStrategy
       ↓
  ├─ RETRY: re-execute handler (up to max_retries)
  ├─ CHECKPOINT_ROLLBACK: restore context to snapshot
  ├─ FALLBACK_AGENT: try with fallback provider chain
  ├─ MEMORY_REPAIR: clear corrupted state
  └─ TERMINATE: stop execution
```

## Plugin Lifecycle

```
UNREGISTERED → INSTALLED → INITIALIZED → STARTED
                                            │
                                     ┌──────┤
                                     ▼      ▼
                                  STOPPED  DISABLED
                                     │
                                     ▼
                                  ERROR
```

## Data Flow

```
TaskRequest (public contract)
     │
     ▼
RuntimeContext (internal context)
     │
     ▼
RuntimeEngine.run() → state handlers → ctx.profile, ctx.evaluation, ...
     │
     ▼
TaskResult (public contract)
     │
     ├─ session_id → RuntimeSession → SessionInfo
     └─ trace_id   → DecisionTrace  → ExplanationRecorder.to_dict()
```
