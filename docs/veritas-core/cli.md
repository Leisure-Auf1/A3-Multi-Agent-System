# CLI

> **Phase 6.1** | Command-line interface for Veritas Runtime.

## Quick Start

```bash
pip install -e .
veritas --version    # veritas 6.1.0
```

## Commands

### `veritas run`

```bash
veritas run -a planner -t "create learning plan"
veritas run -a evaluator -t "analyze output" --timeout 120
veritas run -a tutor -t "teach Python" --context level=beginner
veritas run -a test -t "json output" --json
veritas run -a test -t "summary" --summary
```

Output:
```
╔══════════════════════════════════════════╗
║         Veritas Task Result              ║
║  Task ID:    abc123def456                ║
║  Status:     completed                   ║
║  Success:    True                        ║
║  Time:       0.2ms                       ║
║  Session:    abc123def456                ║
║  Trace:      abc123def456                ║
╚══════════════════════════════════════════╝
```

### `veritas status`

```bash
veritas status
veritas status --json
```

Output:
```
╔══════════════════════════════════════════╗
║         Veritas Runtime Status           ║
║  Version:          6.0                   ║
║  Recovery:         True                  ║
║  Sessions:         5                     ║
║  Plugins:          2                     ║
║  Distributed:      False                 ║
╚══════════════════════════════════════════╝
```

### `veritas trace`

```bash
veritas trace SESSION_ID
veritas trace SESSION_ID --json
```

Output:
```
╔══════════════════════════════════════════╗
║       Decision Explainability            ║
║  Decisions:       5                      ║
║  Explainability:  0.85                   ║
║  Diversity:        0.60                  ║
║  CONTINUE         3                      ║
║  RETRY            2                      ║
╚══════════════════════════════════════════╝
```

### `veritas plugins`

```bash
veritas plugins
veritas plugins --json
```

## Output Formats

| Flag | Format | Use Case |
|:-----|:-------|:---------|
| (default) | TABLE | Human-readable box-drawing |
| `--json` | JSON | Scripting, API integration |
| `--summary` | one-line | Logging, CI output |

## Architecture Enforcement

```
CLI → RuntimeClient → RuntimeAdapter → RuntimeEngine (hidden)
                                            ↑
                          NEVER imported directly by CLI
```

The CLI layer has zero `from src.runtime` imports. All calls go through `RuntimeClient`.
