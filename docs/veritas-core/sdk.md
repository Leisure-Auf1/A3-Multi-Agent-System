# Public SDK

> **Phase 6.0** | Stable contract API — the ONLY way applications should talk to Veritas.

## Design Goal

Hide all RuntimeEngine internals behind a stable, contract-based API.
Applications never import `RuntimeEngine`, `RuntimeHook`, or `RuntimeEventBus`.
They only use `RuntimeClient` and data contracts.

## Quick Start

```python
from src.sdk import RuntimeClient, TaskRequest

client = RuntimeClient()

# Run a task
result = client.run(TaskRequest(
    objective="analyze code quality",
    agent="evaluator",
    context={"language": "Python"},
    timeout_seconds=120,
))

print(result.status.value)      # "completed"
print(result.is_success)        # True
print(result.execution_time_ms) # 42.0
```

## Contracts

### TaskRequest

| Field | Type | Required | Description |
|:------|:-----|:---------|:------------|
| `objective` | `str` | ✅ | What to accomplish |
| `agent` | `str` | ✅ | Agent type (planner, evaluator, etc.) |
| `context` | `dict` | | Task-specific data |
| `task_id` | `str` | | Auto-generated UUID |
| `timeout_seconds` | `float` | | Default: 300 |
| `metadata` | `dict` | | Caller tracing data |

### TaskResult

| Field | Type | Description |
|:------|:-----|:------------|
| `task_id` | `str` | Correlates to TaskRequest |
| `status` | `TaskStatus` | PENDING → COMPLETED / FAILED / TIMEOUT |
| `is_success` | `bool` | True if COMPLETED |
| `output` | `dict` | Task output data |
| `execution_time_ms` | `float` | Total execution time |
| `session_id` | `str` | For trace correlation |
| `trace_id` | `str` | For explainability |
| `errors` | `list` | Non-fatal errors |

### SessionInfo

| Field | Type | Description |
|:------|:-----|:------------|
| `session_id` | `str` | Unique session identifier |
| `state` | `str` | "completed" / "error" |
| `timeline` | `list` | Ordered state names visited |
| `total_duration_ms` | `float` | Session duration |
| `error_count` | `int` | Transition errors |
| `decision_count` | `int` | Policy decisions made |

## Configuration

```python
from src.sdk.config import RuntimeConfig, ConfigLoader

# Python
config = RuntimeConfig(
    recovery_enabled=True,
    max_retries=3,
    explainability_enabled=True,
)

# YAML
loader = ConfigLoader()
config = loader.load("veritas.yaml")

# Priority: constructor args > ENV vars > YAML > defaults
config = loader.load("veritas.yaml", overrides={"max_retries": 5})
```

## Error Handling

```python
from src.sdk.exceptions import (
    VeritasError,           # base — catch-all
    ContractValidationError, # invalid TaskRequest
    TaskExecutionError,      # execution failure
    SessionNotFoundError,    # session doesn't exist
    ConfigError,             # bad config
    PluginError,             # plugin lifecycle failure
)

try:
    result = client.run(task)
except ContractValidationError as e:
    print(f"Invalid input: {e.field}")
except TaskExecutionError as e:
    print(f"Task '{e.task_id}' failed: {e.cause}")
except VeritasError as e:
    print(f"SDK error: {e.detail}")
```

## Limitations

- No async/await support — all calls are synchronous
- Single client instance per process (no thread-safety guarantees)
- Sessions are in-memory only — process restart loses history
