# Veritas-Core — Framework Overview

> **Version:** 6.1 | **Tests:** 1042 | **License:** MIT

Veritas-Core is a pluggable, observable, recoverable **Agent Runtime Framework**.
It provides the infrastructure for building autonomous agent applications
without reinventing execution, recovery, security, or observability.

## What Veritas Provides

| Capability | Phase | Description |
|:-----------|:-----:|:------------|
| Runtime Engine | 4.8 | State machine driving agent pipelines |
| Observability | 4.9–4.10 | Events, metrics, hooks, native observer |
| Dashboard | 5.0 | Snapshot, FastAPI endpoints, Streamlit UI |
| Memory & Store | 5.1 | Short-term runtime store + long-term agent memory |
| Intelligence | 5.2 | Analyzer, failure detector, policy engine |
| Security | 5.3 | Permission matrix, tool gateway, prompt guard, audit |
| Recovery | 5.4 | Retry, checkpoint rollback, provider fallback, memory repair |
| Lifecycle | 5.5 | Agent lifecycle states, session management |
| Benchmark | 5.6 | Failure injection, metrics, comparison reports |
| Explainability | 5.7 | Decision trace, structured reasons, causal chains |
| Plugin System | 5.8 | Pluggable extensions with managed lifecycle |
| Distributed | 5.9 | Multi-node runtime, event propagation, remote execution |
| Public SDK | 6.0 | Stable contract API (RuntimeClient, TaskRequest) |
| CLI | 6.1 | Command-line interface (veritas run/status/trace) |

## Quick Start

```python
from src.sdk import RuntimeClient, TaskRequest

client = RuntimeClient()

# Execute a task
result = client.run(TaskRequest(
    objective="analyze performance",
    agent="evaluator",
    timeout_seconds=60,
))

print(result.status)           # completed
print(result.execution_time_ms) # 42.0
print(result.session_id)        # trace correlation
```

## Architecture Layers

```
┌─────────────────────────────────────────────┐
│              Applications                    │
│  (A3 Learning, Coding Agent, Research Agent) │
├─────────────────────────────────────────────┤
│           Public SDK (stable API)            │
│       RuntimeClient, TaskRequest/Result      │
├─────────────────────────────────────────────┤
│          Runtime Infrastructure              │
│  ┌─────────┬──────────┬──────────┐          │
│  │ Engine  │ Recovery │ Security │          │
│  ├─────────┼──────────┼──────────┤          │
│  │Hooks    │Lifecycle │Plugins   │          │
│  ├─────────┼──────────┼──────────┤          │
│  │Explain  │Benchmark │Distributed│         │
│  └─────────┴──────────┴──────────┘          │
└─────────────────────────────────────────────┘
```

## Design Principles

1. **Non-invasive** — Add capabilities via hooks and plugins, never by modifying the engine
2. **Contract-first** — Public API is frozen; internals can evolve independently
3. **Layered** — Each layer depends only on the layer below it
4. **Isolated failure** — Hook errors, plugin crashes, and remote failures never break the engine
5. **Observable by default** — Every decision, transition, and recovery is traced

## Module Map

| Module | Path | Key Classes |
|:-------|:-----|:------------|
| Engine | `runtime/` | `RuntimeEngine`, `RuntimeContext`, `AgentState` |
| Hooks | `runtime/hooks.py` | `RuntimeHook`, `CompositeHook` |
| Events | `runtime/events.py` | `RuntimeEvent`, `RuntimeEventBus` |
| Recovery | `runtime/recovery/` | `RecoveryManager`, `RecoveryStrategy` |
| Lifecycle | `runtime/lifecycle/` | `LifecycleManager`, `RuntimeSession` |
| Explain | `runtime/explain/` | `DecisionTrace`, `ExplanationRecorder` |
| Plugins | `runtime/plugins/` | `RuntimePlugin`, `PluginManager` |
| Distributed | `runtime/distributed/` | `RuntimeNode`, `NodeRegistry` |
| SDK | `sdk/` | `RuntimeClient`, `TaskRequest`, `TaskResult` |
| CLI | `cli/` | `main()`, `veritas` command |
| Security | `security/` | `PermissionMatrix`, `ToolGateway`, `AuditLogger` |
| Benchmark | `benchmark/` | `BenchmarkRunner`, `FailureInjector` |
