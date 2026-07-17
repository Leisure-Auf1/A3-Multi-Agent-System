# Plugin System

> **Phase 5.8** | Pluggable extensions with managed lifecycle.

## Design Goal

Enable third-party extensions without modifying the RuntimeEngine.
Plugins follow a managed lifecycle and receive engine events through
the hook bridge — one `engine.add_hook(bridge)` integrates all plugins.

## Architecture

```
PluginManager → PluginRegistry → PluginLoader (importlib)
     │
     ├─ install / remove / enable / disable
     ├─ initialize_all(engine) / start_all / stop_all
     │
     └─ PluginHookBridge (RuntimeHook)
              │
              ├─ broadcasts to all OPERATIONAL plugins
              └─ error isolation per plugin
```

## Creating a Plugin

```python
from src.runtime.plugins import RuntimePlugin

class SecurityPlugin(RuntimePlugin):
    name = "security"
    version = "1.0.0"
    priority = 10
    description = "Audits every state transition"

    def on_initialize(self, runtime):
        print("Security plugin initialized")

    def on_start(self):
        print("Security plugin active")

    def after_transition(self, engine, from_s, to_s, ctx, transition):
        # Audit every transition
        print(f"AUDIT: {from_s.name} → {to_s.name}")
```

## Plugin Manager

```python
from src.runtime.plugins import PluginManager

mgr = PluginManager()

# Install
mgr.install(SecurityPlugin())
mgr.install(ExplainPlugin())

# Initialize with engine
mgr.initialize_all(engine)

# Start all
mgr.start_all()

# One-line integration
engine.add_hook(mgr.bridge)

# Query
print(mgr.list_plugins())
print(mgr.summary())  # {total, started, initialized, stopped, error}

# Manage
mgr.disable("security")
mgr.enable("security")
mgr.remove("security")
```

## Plugin Lifecycle

| State | Meaning |
|:------|:--------|
| `UNREGISTERED` | Not yet added to any registry |
| `INSTALLED` | Added to registry via `mgr.install()` |
| `INITIALIZED` | `on_initialize(runtime)` called |
| `STARTED` | `on_start()` called, receiving events |
| `STOPPED` | `on_stop()` called, paused |
| `DISABLED` | `on_shutdown()` called, removed |
| `ERROR` | Initialization or lifecycle failure |

## Plugin Hook Bridge

```python
# Plugins receive ALL RuntimeHook events:
# on_run_start, before_transition, after_transition, on_error, on_run_end
# Plus custom events via on_event(event)

from src.runtime.plugins import PluginHookBridge

bridge = PluginHookBridge()
bridge.add_plugin(my_plugin)
engine.add_hook(bridge)
```

## Dynamic Loading

```python
from src.runtime.plugins import PluginLoader

loader = PluginLoader()
plugin = loader.load("my_package.plugins", "SecurityPlugin")
plugins = loader.load_all("my_package.plugins")  # discover all
```

## Limitations

- Plugins must extend `RuntimePlugin(RuntimeHook)` — no alternative base classes
- Plugin discovery requires importable Python modules
- No hot-reload (unload + reload requires manager.remove() + manager.install())
