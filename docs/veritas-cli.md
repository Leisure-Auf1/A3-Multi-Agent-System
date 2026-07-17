# Veritas CLI

> **Version:** 6.1.0 | **Tests:** 1042+

Command-line interface for the Veritas Agent Runtime. All commands
route through `RuntimeClient` — zero direct `RuntimeEngine` access.

## Installation

```bash
pip install -e .
# Now the `veritas` command is available
```

## Architecture

```
User
 │
 ▼
veritas CLI  (src/cli/)
 │
 ▼
RuntimeClient  (src/sdk/client.py)
 │
 ▼
RuntimeAdapter  (src/sdk/adapters/)
 │
 ▼
RuntimeEngine  (src/runtime/runtime.py)
         ↑
    (hidden from CLI — never imported directly)
```

## Commands

### `veritas run`

Execute a task through the Veritas Runtime.

```bash
veritas run --agent planner --task "create learning plan"
veritas run -a evaluator -t "analyze output" --timeout 120
veritas run -a tutor -t "teach Python" --context level=beginner style=visual
veritas run -a test -t "quick" --json
veritas run -a test -t "summary mode" --summary
```

| Flag | Short | Required | Description |
|:-----|:------|:---------|:------------|
| `--agent` | `-a` | Yes | Agent type (planner, evaluator, executor, tutor) |
| `--task` | `-t` | Yes | Task objective / description |
| `--timeout` | | No | Max execution time in seconds (default: 300) |
| `--context` | | No | Key=value pairs (e.g. `level=beginner`) |
| `--json` | | No | Output in JSON format |
| `--summary` | | No | Compact one-line output |

### `veritas status`

Display Runtime status and health.

```bash
veritas status
veritas status --json
```

Outputs: version, recovery status, session count, plugin count, distributed status.

### `veritas trace`

Query decision explainability for a session.

```bash
veritas trace SESSION_ID
veritas trace SESSION_ID --json
```

Outputs: total decisions, explainability score, decision diversity, per-action breakdown.

### `veritas plugins`

List installed RuntimePlugins.

```bash
veritas plugins
veritas plugins --json
```

## Design Rules

- **CLI never imports `RuntimeEngine` directly** — all calls go through `RuntimeClient`
- **CLI never imports `RuntimeEventBus` or `RuntimeHook`**
- **Config reuses `src/sdk/config/`** — no new config system
- **Formatter supports 3 modes:** TABLE (default), JSON, SUMMARY

## Internal Structure

```
src/cli/
├── __init__.py
├── main.py              # argparse entry point
├── formatter.py         # Output formatting (TABLE/JSON/SUMMARY)
└── commands/
    ├── run.py           # veritas run
    ├── status.py        # veritas status
    ├── trace.py         # veritas trace
    └── plugins.py       # veritas plugins
```
