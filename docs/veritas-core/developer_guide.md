# Developer Guide

> How to extend, debug, and contribute to Veritas-Core.

## Project Structure

```
A3-Multi-Agent-System/
├── src/
│   ├── runtime/          # Core runtime engine
│   │   ├── recovery/     # Recovery strategies
│   │   ├── lifecycle/    # Agent lifecycle
│   │   ├── explain/      # Decision explainability
│   │   ├── plugins/      # Plugin system
│   │   └── distributed/  # Multi-node runtime
│   ├── sdk/              # Public API (stable contracts)
│   ├── cli/              # Command-line interface
│   ├── security/         # Permission, audit, prompt guard
│   ├── benchmark/        # Failure injection, metrics
│   └── memory/           # Agent memory management
├── tests/                # 1042 tests
├── docs/                 # Documentation
│   └── veritas-core/     # Framework docs (you are here)
└── examples/             # Usage examples
```

## Running Tests

```bash
# All tests
make test

# Specific module
python -m pytest tests/test_runtime_recovery.py -v

# With coverage
make test-cov
```

## Adding a New Runtime Feature

1. **Never modify RuntimeEngine directly** — use hooks or plugins
2. Create your module in `src/runtime/your_feature/`
3. Implement as a `RuntimeHook` subclass for integration
4. Add tests in `tests/test_runtime_your_feature.py`
5. Run full suite: `make test`

## Creating a Custom Plugin

```python
from src.runtime.plugins import RuntimePlugin

class MyPlugin(RuntimePlugin):
    name = "my_plugin"
    version = "1.0.0"

    def on_initialize(self, runtime):
        self.runtime = runtime

    def on_start(self):
        print("MyPlugin active")

    def after_transition(self, engine, from_s, to_s, ctx, transition):
        # React to every state transition
        pass

    def on_error(self, engine, state, ctx, error):
        # React to errors
        pass
```

```python
# Integration
from src.runtime.plugins import PluginManager

mgr = PluginManager()
mgr.install(MyPlugin())
mgr.initialize_all(engine)
mgr.start_all()
engine.add_hook(mgr.bridge)
```

## Adding a CLI Command

1. Create `src/cli/commands/your_command.py`
2. Define `register_parser(subparsers)` + `handle_command(args)`
3. Register in `src/cli/main.py`'s `create_parser()`
4. `handle_command` must use only `RuntimeClient` — never import runtime internals

## Debugging

```python
# Enable all observability
from src.runtime import RuntimeObserver, RuntimeMetrics

observer = RuntimeObserver()
metrics = RuntimeMetrics()
engine.add_hook(observer)

engine.run()
print(observer.events_by_type("error"))
print(metrics.summary())
```

## Common Pitfalls

1. **Don't import RuntimeEngine in application code** — use `RuntimeClient`
2. **Hook errors are isolated** — one hook failure doesn't break others
3. **EventBus is not thread-safe** — use per-session buses
4. **`MAX_TRANSITIONS = 20`** — adjust if your pipeline is long
5. **Sessions are in-memory** — process restart loses history

## Architecture Rules

| Rule | Enforcement |
|:-----|:-----------|
| CLI never imports `src.runtime` | Test assertion |
| Plugins must extend `RuntimePlugin` | `issubclass` check in loader |
| SDK never exposes `RuntimeEngine` | Code review |
| Recovery never modifies agent logic | Architecture constraint |
| Distributed is add-on only | Works with `distributed_enabled=False` |
