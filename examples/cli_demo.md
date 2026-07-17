# CLI Demo

## Veritas CLI Quick Demo

```bash
# Install the CLI
pip install -e .

# Check version
$ veritas --version
veritas 6.1.0

# Run a task
$ veritas run -a planner -t "create Python learning plan"
╔══════════════════════════════════════════╗
║         Veritas Task Result              ║
║  Task ID:    3f7a2b1c8d4e               ║
║  Status:     completed                   ║
║  Success:    True                        ║
║  Time:       0.3ms                       ║
║  Session:    3f7a2b1c8d4e               ║
║  Trace:      3f7a2b1c8d4e               ║
╚══════════════════════════════════════════╝

# JSON output
$ veritas run -a evaluator -t "evaluate" --json
{
  "task_id": "a1b2c3d4e5f6",
  "status": "completed",
  "is_success": true,
  "execution_time_ms": 0.2,
  "session_id": "a1b2c3d4e5f6"
}

# Summary output (one line)
$ veritas run -a test -t "quick" --summary
✅ a1b2c3d4e5f6 | completed | 0ms

# Runtime status
$ veritas status
╔══════════════════════════════════════════╗
║         Veritas Runtime Status           ║
║  Version:          6.0                   ║
║  Recovery:         True                  ║
║  Sessions:         3                     ║
║  Plugins:          0                     ║
║  Distributed:      False                 ║
╚══════════════════════════════════════════╝

# Trace a session
$ veritas trace a1b2c3d4e5f6
╔══════════════════════════════════════════╗
║       Decision Explainability            ║
║  Decisions:       2                      ║
║  Explainability:  0.85                   ║
║  Diversity:        0.40                  ║
║  CONTINUE         2                      ║
╚══════════════════════════════════════════╝

# List plugins
$ veritas plugins
Plugins:
--------------------------------------------------
  ✅ security v1.0 | started | priority=10
  ⏸️ explain v2.0 | disabled | priority=5
```
